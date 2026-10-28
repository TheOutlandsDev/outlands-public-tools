"""Fresh portable application acceptance; private metrics/tokens/logs never uploaded."""
import argparse
from contextlib import contextmanager
import csv
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit,parse_qs
import zipfile
from build import FILENAME,PREFIX,sha


def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def accept(packages,workspace,browser=False):
    if sys.version_info[:2]!=(3,12):raise ValueError('Acceptance controller requires Python 3.12 for legacy source-launcher qualification.')
    if os.name!='nt' or not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_EXTERNAL_WINDOWS_WORKSPACE_REQUIRED')
    r=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes();assert sha(raw)==r['sha256']
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:
        m=json.loads(z.read(PREFIX+'PACKAGE-MANIFEST.json'));names=z.namelist()
        assert len(names)==len(set(names))==r['files'] and set(names)=={PREFIX+x['path'] for x in m['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
        for row in m['files']:
            n=row['path'];assert not n.startswith('/') and not any(x in ('','.','..') for x in n.split('/')) and ':' not in n and '\\' not in n
            b=z.read(PREFIX+n);assert len(b)==row['bytes'] and sha(b)==row['sha256']
        z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir()
    before=tree(root);node=shutil.which('node');assert node
    env={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32'),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','RESOURCE_MONITOR_REQUIRE_LIVE':'1','PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def cmd(args,live=False):
        line=subprocess.list2cmdline([str(root/('Resource Monitor Live.cmd' if live else 'Resource Monitor.cmd')),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,live=False,expected=0):
        p=subprocess.run(cmd(args,live),cwd=private,env=env,capture_output=True,timeout=40)
        (private/'last-cli.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==expected,'CMD check failed; private log retained.'
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and not health['psutil_loaded']
    assert tree(root)==before and {p.name for p in private.iterdir()}=={'temp','last-cli.log'};checks.append('default_cmd_uses_isolated_bundled_python_without_live_import_or_state')
    h=json.loads(cli(['--check'],True));assert h['mode']=='live' and h['live_dependency']=='7.2.1' and h['psutil_loaded'];checks.append('separate_live_cmd_loads_only_bundled_pinned_native_dependency')
    checked=subprocess.run([python,'-I','-B',str(app/'source_check.py')],cwd=app,env=env,capture_output=True,timeout=40);assert checked.returncode==0;checks.append('original_application_source_manifest_unchanged')
    def unittest_result(result,name,count):
        (private/(name+'.log')).write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,'Original tests failed; private log retained.'
        log=result.stderr.decode('utf-8');assert re.search(r'Ran '+str(count)+r' tests?',log)
        match=re.search(r'skipped=(\d+)',log);skips=int(match.group(1)) if match else 0
        assert skips in (0,1)
        if skips:assert log.count("skipped 'This account cannot create symlinks'")==1
        return skips
    core=subprocess.run([python,'-I','-B','-W','error','-m','unittest','discover','-s',str(app/'tests'),'-p','test_monitor.py','-v'],cwd=app,env=env,capture_output=True,timeout=180)
    core_skips=unittest_result(core,'core-tests',46);checks.append('all_46_original_core_cases_run_on_bundled_python_with_required_live_sampling')
    # Source launcher intentionally retains its Python 3.12/3.13 version guard.
    source_env={**os.environ,'PYTHONPATH':str(root/'dependencies'),'PYTHONDONTWRITEBYTECODE':'1','RESOURCE_MONITOR_REQUIRE_LIVE':'1','TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary)}
    source=subprocess.run([sys.executable,'-B','-W','error','-m','unittest','discover','-s','tests','-v'],cwd=app,env=source_env,capture_output=True,timeout=180)
    source_skips=unittest_result(source,'source-tests',49);checks.append('all_49_unmodified_source_and_legacy_launcher_cases_run_separately_on_python_312')
    front=subprocess.run([node,'--test','--test-reporter=tap','tests/frontend.test.mjs'],cwd=app,capture_output=True,timeout=40)
    (private/'frontend-tests.log').write_bytes(front.stdout+front.stderr);assert front.returncode==0 and b'# tests 13' in front.stdout;checks.append('all_13_original_presentation_cases_pass')
    def http(origin,token,route,extra=None):
        parts=urlsplit(origin);conn=HTTPConnection(parts.hostname,parts.port,timeout=5)
        try:
            headers={'X-Outlands-Token':token};headers.update(extra or {});conn.request('GET',route,headers=headers);res=conn.getresponse();return res.status,res.read()
        finally:conn.close()
    def api(s,route='/api/history'):
        status,b=http(s['origin'],s['token'],route);assert status==200;return json.loads(b)
    def wait_samples(s,count):
        end=time.monotonic()+10
        while time.monotonic()<end:
            j=api(s)
            if len(j['samples'])>=count:return j
            time.sleep(.05)
        raise AssertionError('Sample collection timed out.')
    @contextmanager
    def server(live=False):
        p=subprocess.Popen(cmd(['--no-browser','--stop-stdin','--interval','.2','--history','12'],live),cwd=private,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        lines=queue.Queue();log=(private/'last-server.log').open('w',encoding='utf-8')
        def read():
            for line in p.stdout:log.write(line);log.flush();lines.put(line)
            lines.put(None)
        worker=threading.Thread(target=read,daemon=True);worker.start();s={'process':p}
        def stop():
            if p.poll() is None:p.stdin.write('stop\n');p.stdin.flush();assert p.wait(timeout=10)==0
        s['stop']=stop
        try:
            until=time.monotonic()+15;state=None
            while time.monotonic()<until:
                line=lines.get(timeout=15)
                if line is None:raise AssertionError('Server stopped before ready; private log retained.')
                if line.startswith('{'):state=json.loads(line)
                if line.startswith('http://127.0.0.1:'):
                    url=line.strip();parts=urlsplit(url);s.update(url=url,origin=parts.scheme+'://'+parts.netloc,token=parse_qs(parts.fragment)['token'][0]);break
            assert s.get('url') and state==dict(mode='live' if live else 'demo',psutil_loaded=live)
            yield s
        finally:
            try:stop()
            finally:
                if p.poll() is None:
                    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=10)
                worker.join(timeout=3);p.stdin.close();p.stdout.close();log.close()
    exports=private/'explicit exports';exports.mkdir()
    with server() as s:
        assert http(s['origin'],s['token'],'/')[0]==200;checks.append('fictional_mode_starts_loopback_only_without_loading_psutil')
        report=wait_samples(s,4);assert report['mode']=='demo' and report['samples'][0]['cpu_percent'] is None and report['samples'][1]['cpu_percent'] is not None
        latest=wait_samples(s,12);time.sleep(.5);latest=api(s);assert len(latest['samples'])==12 and latest['samples'][0]['sequence']>1;checks.append('warmup_gaps_and_bounded_demo_history_observed')
        assert http(s['origin'],'','/api/history')[0]==403 and http(s['origin'],s['token'],'/api/history',{'Origin':'https://example.invalid'})[0]==403;checks.append('missing_token_and_foreign_origin_refused')
        status,json_bytes=http(s['origin'],s['token'],'/api/export.json');assert status==200
        status,csv_bytes=http(s['origin'],s['token'],'/api/export.csv');assert status==200
        jp=exports/'fictional-history.json';cp=exports/'fictional-history.csv';jp.write_bytes(json_bytes);cp.write_bytes(csv_bytes)
        assert json.loads(jp.read_bytes())['mode']=='demo';rows=list(csv.DictReader(io.StringIO(cp.read_text(encoding='utf-8'))));assert rows and len(rows)<=12 and all(x['mode']=='demo' for x in rows);checks.append('explicit_http_json_csv_exports_reopened_and_validated')
        sys.path.insert(0,str(app));from resource_monitor.core import save_fresh,MonitorError
        previous=jp.read_bytes()
        try:save_fresh(str(jp),b'replacement');raise AssertionError('Existing export overwritten.')
        except MonitorError:pass
        assert jp.read_bytes()==previous;checks.append('original_explicit_cli_export_refuses_existing_file_without_changes')
        old=s['token']
    with server() as second:
        j=api(second);assert j['samples'] and j['samples'][0]['sequence']==1 and len(j['samples'])<12
        assert old!=second['token'] and http(second['origin'],old,'/api/history')[0]==403
        assert jp.read_bytes()==json_bytes and cp.read_bytes()==csv_bytes;checks.append('actual_restart_resets_history_and_token_preserves_deliberate_exports')
    with server(True) as live:
        values=wait_samples(live,3);assert values['mode']=='live' and not values['sampling_error']
        row=values['samples'][-1];assert isinstance(row['cpu_percent'],(int,float)) and 0<=row['cpu_percent']<=100
        assert row['memory']['total_bytes']>0 and row['network']['received_bytes']>=0
    checks.append('explicit_live_launcher_collects_real_aggregate_metrics_values_kept_private')
    if browser:
        from playwright.sync_api import sync_playwright,expect
        with sync_playwright() as pw:
            chrome=pw.chromium.launch();context=chrome.new_context(accept_downloads=True,viewport={'width':1440,'height':1000});page=context.new_page()
            try:
                with server() as s:
                    page.goto(s['url']);expect(page.locator('#mode-badge')).to_have_text('FICTIONAL DEMO');expect(page.locator('#connection-state')).to_have_text('Connected locally')
                    assert '#token=' not in page.url
                    expect(page.locator('#cpu-path')).to_have_attribute('d',re.compile(r'.+'))
                    page.locator('#pause').click();expect(page.locator('#connection-state')).to_have_text('View paused');display=page.locator('#readings').inner_text();seq=api(s)['samples'][-1]['sequence'];time.sleep(1.3)
                    assert page.locator('#readings').inner_text()==display and api(s)['samples'][-1]['sequence']>seq
                    page.locator('#pause').click();expect(page.locator('#connection-state')).to_have_text('Connected locally');expect(page.locator('#readings')).not_to_have_text(display)
                    for extension,button in [('json','#export-json'),('csv','#export-csv')]:
                        with page.expect_response(lambda response:response.url.endswith('/api/export.'+extension)) as response_info:
                            with page.expect_download() as download_info:page.locator(button).click()
                        dest=exports/('browser-history.'+extension);download_info.value.save_as(str(dest));assert dest.read_bytes()==response_info.value.body()
                        if extension=='json':assert json.loads(dest.read_bytes())['mode']=='demo'
                        else:assert all(x['mode']=='demo' for x in csv.DictReader(io.StringIO(dest.read_text(encoding='utf-8'))))
                    old=s['token'];s['stop']();expect(page.locator('#connection-state')).to_have_text('Connection unavailable',timeout=12000);last_display=page.locator('#readings').inner_text();time.sleep(1.1);assert page.locator('#readings').inner_text()==last_display
                with server() as current:
                    page.goto(current['origin']+'/#token='+old);expect(page.locator('#connection-state')).to_have_text('Reconnect required');expect(page.locator('#auth-panel')).to_be_visible();expect(page.locator('#export-json')).to_be_disabled()
                    page.locator('#token').fill(current['token']);page.locator('#connect-form button').click();expect(page.locator('#connection-state')).to_have_text('Connected locally');expect(page.locator('#mode-badge')).to_have_text('FICTIONAL DEMO')
                with server(True) as live:
                    page.goto(live['url']);expect(page.locator('#mode-badge')).to_have_text('LIVE METRICS');expect(page.locator('#connection-state')).to_have_text('Connected locally')
                checks.append('chromium_real_pause_resume_downloads_stale_display_reconnect_and_live_badge')
            finally:context.close();chrome.close()
    assert tree(root)==before;checks.append('all_distribution_files_unchanged_no_automatic_private_state_or_logs')
    assert len(checks)==(15 if browser else 14)
    accepted=dict(schema=1,status='PASS',browser=browser,package_sha256=r['sha256'],packaging_source=r['packaging_source'],bundled_runtime='3.14.10',core_tests=46,core_skips=core_skips,source_test_runtime=sys.version.split()[0],source_tests=49,source_skips=source_skips,frontend_tests=13,live_smoke=True,synthetic_exports_only=True,private_live_values_published=False,manual_python_free_pc='not_performed',checks=checks)
    (packages/'acceptance.json').write_text(json.dumps(accepted,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(accepted))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
