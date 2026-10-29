"""Fresh Windows CMD, preserved source and real bundled-runtime Chromium acceptance."""
import argparse
from contextlib import contextmanager,closing
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit
import zipfile
from build import FILENAME,PREFIX,sha,encoded,members

def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}

def accept(packages,workspace,browser=False):
    if os.name!='nt' or not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_WINDOWS_WORKSPACE_REQUIRED')
    if browser and os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('HOSTED_BROWSER_QUALIFICATION_ONLY')
    receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes();assert sha(raw)==receipt['sha256'];contents=members(raw)
    manifest=json.loads(contents[PREFIX+'PACKAGE-MANIFEST.json'])
    assert len(contents)==receipt['files'] and set(contents)=={PREFIX+r['path'] for r in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
    for row in manifest['files']:
        b=contents[PREFIX+row['path']];assert row==dict(path=row['path'],bytes=len(b),sha256=sha(b))
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir();before=tree(root);pwsh=shutil.which('pwsh');assert pwsh
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_LINKS':'1','PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Planning Exercise.cmd' if exercise else 'Planning Demo.cmd')),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,exercise=False,expected=0):
        p=subprocess.run(command(args,exercise),cwd=private,env=env,capture_output=True,timeout=180);(private/'last-cli.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==expected,'CMD check failed; private log retained.'
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime'];assert tree(root)==before
    checks.append('cmd_uses_isolated_bundled_runtime_without_system_python_or_state')
    source=subprocess.run([python,'-I','-B',str(app/'release_source.py'),'check'],cwd=app,env=env,capture_output=True,timeout=30);assert source.returncode==0;checks.append('original_source_inventory_preserved')
    p=subprocess.run([python,'-I','-B','-W','error',str(app/'run_checks.py')],cwd=app,env=env,capture_output=True,timeout=300);(private/'core-tests.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Bundled core checks failed; private log retained.'
    assert re.search(r'Ran 86 tests?',p.stderr.decode('utf-8')) and 'skipped=1' in p.stderr.decode('utf-8')
    core=p.stderr.decode('utf-8')
    for name in ('test_native_hardlink_file_refused','test_native_database_hardlink_refused','test_native_symlink_file_refused','test_native_symlink_parent_refused','test_native_junction_input_parent_refused','test_windows_stream_refused'):
        assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_86_original_core_methods_on_bundled_python_five_required_native_boundaries_one_opposite_platform_skip')
    exercise_workspace=private/'new data exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==14
    assert outcome['initial_totals']==[160,25,85,50,3] and outcome['final_totals']==[170,25,85,60,4]
    checks.append('cmd_exercise_14_original_cli_calls_independent_arithmetic_revision_report_and_backup_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    snapshot=json.loads(cli(['--workspace',exercise_workspace,'--cli','show','--project','sample-workshop']));assert snapshot['sequence']==2
    checks.append('original_cli_reopens_saved_second_revision')
    gui_workspace=private/'browser data practice'
    @contextmanager
    def server():
        p=subprocess.Popen(command(['--workspace',gui_workspace,'--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        lines=queue.Queue();log=(private/'last-server.log').open('w',encoding='utf-8');value={}
        def read():
            for line in p.stdout:log.write(line);log.flush();lines.put(line)
            lines.put(None)
        worker=threading.Thread(target=read,daemon=True);worker.start()
        def http(path,body=None,expected=200):
            parts=urlsplit(value['url']);conn=HTTPConnection(parts.hostname,parts.port,timeout=10)
            try:
                headers={'X-Outlands-Token':value.get('token',''),'Content-Type':'application/json','Origin':value['url'].rstrip('/')}
                conn.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers=headers);res=conn.getresponse();raw=res.read();assert res.status==expected;return raw
            finally:conn.close()
        value['http']=http
        try:
            while True:
                line=lines.get(timeout=30)
                if line is None:raise AssertionError('Server stopped before ready; private log retained.')
                if line.startswith('Fresh private report directory: '):value['reports']=Path(line.strip().removeprefix('Fresh private report directory: '))
                if line.startswith('Open http://127.0.0.1:'):value['url']=line.strip().removeprefix('Open ');break
            html=http('/').decode('utf-8');value['token']=re.search(r"const token='([^']+)'",html).group(1)
            yield value
        finally:
            try:
                if p.poll() is None and value.get('token') and not value.get('shutdown_requested'):http('/api/shutdown',{})
                if p.poll() is None:assert p.wait(timeout=10)==0
            finally:
                if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=10)
                worker.join(timeout=5);p.stdout.close();log.close()

    captures={};browser_data={};original_browser_tests=0
    if browser:
        test_env={**os.environ,'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1'};test_env.pop('OUTLANDS_BROWSER_EVIDENCE',None)
        p=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=test_env,capture_output=True,timeout=300);(private/'original-browser-tests.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0 and re.search(r'Ran 19 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=19;checks.append('all_19_original_browser_methods_on_separate_test_python_without_skips')
        from playwright.sync_api import sync_playwright,expect
        from planning_demo import totals,report
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual hosted Windows Chromium and bundled Python; invented planning data only; no address bar, absolute path or session token')
            def view(s):return json.loads(s['http']('/api/view?project=sample-workshop'))
            with server() as s:
                page.goto(s['url']);expect(page.locator('#message')).to_have_text('Project loaded');first=view(s);assert totals(first['plan'])==[160,25,85,50,3]
                expect(page.locator('#stats strong')).to_have_text(['160','25','85','50','3']);capture('planning-baseline.jpg');checks.append('actual_bundled_browser_independent_160_equals_25_plus_85_plus_50')
                page.locator('#export').click();expect(page.locator('#message')).to_contain_text('outlands-planning-report-v1');first_export=json.loads(page.locator('#message').inner_text());assert report(gui_workspace,first_export)==first['plan'];old_report=tree(gui_workspace/first_export['directory'])
                checks.append('actual_bundled_baseline_five_file_report_hashes_independently_checked')
                page.locator('#actor').fill('sample_reviewer');page.get_by_role('button',name='ACKNOWLEDGE',exact=True).first.click();expect(page.locator('#message')).to_have_text('Local review saved');reviewed=view(s);assert reviewed['plan']['actions'][0]['workflow']['status']=='ACKNOWLEDGED';capture('planning-review.jpg')
                checks.append('actual_bundled_local_review_persists_without_execution_authority')
                page.locator('[data-tab=editor]').click();project=json.loads(page.locator('#json').input_value());appended=dict(project['order_history'][0],row_version=2,ordered_quantity=80);project['order_history'].append(appended);project['handoffs'][0]['order_version']=2
                page.locator('#json').fill(json.dumps(project));page.locator('#save').click();expect(page.locator('#message')).to_have_text('Validated revision 2 saved');second=view(s);assert totals(second['plan'])==[170,25,85,60,4] and all(a['workflow']['status']=='OPEN' for a in second['plan']['actions']);expect(page.locator('#stats strong')).to_have_text(['170','25','85','60','4'])
                before_refusal=tree(gui_workspace);refused=json.loads(s['http']('/api/save',dict(project=project,expected=first['snapshot']['revision_sha256']),400));assert refused==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal
                page.locator('#export').click();expect(page.locator('#message')).to_contain_text('outlands-planning-report-v1');second_export=json.loads(page.locator('#message').inner_text());assert report(gui_workspace,second_export)==second['plan'] and first_export['directory']!=second_export['directory'];assert tree(gui_workspace/first_export['directory'])==old_report;capture('planning-revised.jpg')
                checks.append('actual_bundled_revision_170_equals_25_plus_85_plus_60_no_inherited_review_stale_write_refused_old_report_retained')
                page.locator('[data-tab=history]').click();expect(page.locator('#history-table tbody tr')).to_have_count(2);assert second['history']['revisions'][1]['parent_sha256']==first['snapshot']['revision_sha256'];capture('planning-history.jpg')
                page.locator('#backup').click();expect(page.locator('#message')).to_contain_text('.sqlite3');backup=json.loads(page.locator('#message').inner_text());raw=(gui_workspace/backup['file']).read_bytes();assert backup['sha256']==sha(raw) and backup['bytes']==len(raw)
                import sqlite3
                with closing(sqlite3.connect((gui_workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==2
                checks.append('actual_bundled_two_revision_parent_chain_and_database_backup_integrity')
                page.set_viewport_size(dict(width=390,height=844));page.locator('[data-tab=overview]').click();page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#note')).to_be_focused();assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_bundled_browser_layout_and_keyboard_navigation')
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            journal_before=tree(gui_workspace)
            with server() as s:
                page.goto(s['url']);expect(page.locator('#message')).to_have_text('Project loaded');assert view(s)==second and tree(gui_workspace)==journal_before and tree(gui_workspace/first_export['directory'])==old_report
                expect(page.locator('#stats strong')).to_have_text(['170','25','85','60','4']);page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            checks.append('actual_bundled_saved_second_revision_and_reports_reopen_without_reseed_owned_shutdown_releases_lock')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close()
            browser_data=dict(initial_totals=[160,25,85,50,3],final_totals=[170,25,85,60,4],revisions=2,private_report_files=5,report_hashes_independently_verified=True,old_report_unchanged=True,stale_revision_refused=True,new_revision_does_not_inherit_review=True,backup_integrity_checked=True,saved_revision_reopened=True,journal_bytes_unchanged_on_reopen=True,external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=86,core_skips=1,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional Windows CMD/browser planning, local review, reports, database integrity and restart; no manufacturing or shipment authority, full restore or separate-PC acceptance')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
