"""Fresh portable ZIP acceptance; generated state/tokens/raw logs stay private."""
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
import zipfile

from build import FILENAME,PREFIX,sha


def snapshot(folder):return {p.relative_to(folder).as_posix():sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}


def accept(packages,workspace,browser=False):
    if os.name!='nt':raise RuntimeError('Windows acceptance is required.')
    if not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_PRIVATE_WORKSPACE_REQUIRED')
    receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes()
    assert sha(raw)==receipt['sha256'] and len(raw)==receipt['bytes']
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as archive:
        manifest=json.loads(archive.read(PREFIX+'PACKAGE-MANIFEST.json'));names=archive.namelist()
        assert len(names)==len(set(names))==receipt['files']
        assert set(names)=={PREFIX+r['path'] for r in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
        for row in manifest['files']:
            assert not row['path'].startswith('/') and '\\' not in row['path'] and ':' not in row['path'] and '..' not in Path(row['path']).parts
            b=archive.read(PREFIX+row['path']);assert len(b)==row['bytes'] and sha(b)==row['sha256']
        archive.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application'
    private=workspace/'private state';private.mkdir();local=private/'local app data';local.mkdir();temp=private/'temporary';temp.mkdir()
    env={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32'),'LOCALAPPDATA':str(local),
         'TEMP':str(temp),'TMP':str(temp),'OUTLANDS_TEST_TEMP':str(temp),
         'PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    default=local/'Outlands/SQLReportWorkbench/fictional-demo';blank=local/'Outlands/SQLReportWorkbench/workspace'
    checks=[]
    def command(args,demo=True):
        line=subprocess.list2cmdline([str(root/('SQL Report Demo.cmd' if demo else 'SQL Report Workbench.cmd')),*map(str,args)])
        return '"'+str(Path(os.environ['COMSPEC']))+'" /d /s /c "'+line+'"'
    def cli(args,demo=True,expected=0):
        p=subprocess.run(command(args,demo),env=env,cwd=workspace,capture_output=True,timeout=100)
        if p.returncode!=expected:
            (private/'last-cli.log').write_bytes(p.stdout+p.stderr);raise AssertionError('Portable CLI failed; private diagnostic retained.')
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime']
    assert not (local/'Outlands').exists();checks.append('isolated_bundled_runtime_check_creates_no_workspace')
    p=subprocess.run([str(root/'runtime/python.exe'),'-I','-B','-W','error',str(app/'release_source.py'),'check'],env=env,cwd=app,capture_output=True,timeout=40)
    assert p.returncode==0;checks.append('original_source_manifest_matches')
    p=subprocess.run([str(root/'runtime/python.exe'),'-I','-B','-W','error',str(app/'run_checks.py')],env=env,cwd=app,capture_output=True,timeout=240)
    (private/'core-tests.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Bundled original core tests failed; private log retained.'
    log=p.stderr.decode('utf-8');core=int(re.search(r'Ran (\d+) tests?',log).group(1));skipped=re.search(r'skipped=(\d+)',log)
    assert core==60;checks.append('all_original_core_tests_run_under_bundled_runtime')

    def http(url,path,payload=None):
        from urllib.parse import urlsplit
        parsed=urlsplit(url);con=HTTPConnection(parsed.hostname,parsed.port,timeout=10)
        try:
            headers={}
            if path!='/':
                page=http(url,'/')[1].decode('utf-8');token=re.search(r"const token='([^']+)'",page).group(1)
                headers={'X-Outlands-Token':token,'Content-Type':'application/json','Origin':url.rstrip('/')}
            con.request('POST' if payload is not None else 'GET',path,json.dumps(payload) if payload is not None else None,headers)
            res=con.getresponse();return res.status,res.read()
        finally:con.close()
    def api(url,path,payload=None):
        status,b=http(url,path,payload);assert status==200;return json.loads(b)
    @contextmanager
    def server(data=None,demo=True):
        args=['--no-browser']+(['--workspace',str(data)] if data else [])
        p=subprocess.Popen(command(args,demo),env=env,cwd=workspace,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        q=queue.Queue()
        def reader():
            for line in p.stdout:q.put(line)
        thread=threading.Thread(target=reader,daemon=True);thread.start();url=None
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:line=q.get(timeout=.2)
                except queue.Empty:
                    assert p.poll() is None,'Bundled server exited before startup.';continue
                m=re.fullmatch(r'Open (http://127\.0\.0\.1:[0-9]+/)\s*',line)
                if m:url=m[1];break
            assert url,'Bundled server did not print a loopback URL.'
            yield url
        finally:
            try:
                if p.poll() is None and url:api(url,'/api/shutdown',{})
            finally:
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    subprocess.run([str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe'),'/PID',str(p.pid),'/T','/F'],capture_output=True)
                    p.wait();raise AssertionError('Graceful owned-worker shutdown failed.')
            thread.join(timeout=2);p.stdout.close();assert p.returncode==0,'Bundled server did not stop cleanly.'
    def query(url,minimum,query=None):
        data=api(url,'/api/dataset?id=sample-data');saved=query or api(url,'/api/query?id=sample-summary')
        value=api(url,'/api/run',dict(query_id='sample-summary',expected_query_sha256=saved['sha256'],dataset_id='sample-data',expected_dataset_sha256=data['dataset_sha256'],bindings=dict(minimum=minimum)))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            value=api(url,'/api/job?id='+value['job_id'])
            if value['state']=='finished':
                assert value['result']['status']=='completed';return api(url,'/api/artifact?id='+value['result']['artifact_id'])
            time.sleep(.05)
        raise AssertionError('Owned query worker did not finish.')
    def rows(record):return record['payload']['result']['rows']
    with server() as url:
        assert len(api(url,'/api/datasets')['datasets'])==1 and api(url,'/api/artifacts')['artifacts']==[]
        cli(['--no-browser'],expected=2)
        first=query(url,0);assert rows(first)==[['alpha',8],['beta',11]]
        filtered=query(url,4);assert rows(filtered)==[['alpha',5],['beta',11]]
        saved=api(url,'/api/query?id=sample-summary');definition=saved['definition'];definition['sql']=definition['sql'].replace('SUM(i.quantity)','SUM(i.quantity) + 1')
        api(url,'/api/save-query',dict(definition=definition,expected_sha256=saved['sha256']))
        revised=query(url,0);assert rows(revised)==[['alpha',9],['beta',12]]
        api(url,'/api/review',dict(artifact_id=first['artifact_id'],artifact_sha256=first['artifact_sha256'],expected_version=0,status='approved',actor='fictional_reviewer',note='Original invented portable exercise',checks=dict(quality=True,privacy=True,rights=True,context=True)))
        exported=api(url,'/api/export',dict(artifact_id=first['artifact_id']))
        record=api(url,'/api/artifact?id='+first['artifact_id'])
    checks+=['default_demo_seed_is_separate_from_blank_workspace','existing_running_instance_refused','parameterized_worker_results_match_8_11_and_5_11','new_query_revision_returns_9_12_without_changing_historical_result']
    export=default/exported['directory'];assert exported['manifest']['public_release_authorized'] is False
    for name,row in exported['manifest']['files'].items():b=(export/name).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    actual=list(csv.reader(io.StringIO((export/'preview.csv').read_text(encoding='utf-8'))))
    assert actual[1:]==[['alpha','8'],['beta','11']]
    checks.append('review_and_checked_private_csv_json_export_agree')
    before=snapshot(default)
    with server() as url:assert api(url,'/api/artifact?id='+first['artifact_id'])==record and len(api(url,'/api/artifacts')['artifacts'])==3
    assert snapshot(default)==before;checks.append('real_new_process_reopens_saved_results_reviews_and_export_without_reseed')
    copied=private/'stopped full workspace copy';shutil.copytree(default,copied);assert snapshot(copied)==before
    with server(copied,demo=False) as url:assert api(url,'/api/artifact?id='+first['artifact_id'])==record and query(url,0)['payload']['result']['rows']==[['alpha',9],['beta',12]]
    assert snapshot(default)==before;checks.append('stopped_full_workspace_copy_reopens_snapshots_records_and_exports_with_original_unchanged')
    # A hard kill can leave the original empty session marker; recovery is explicit.
    (copied/'.session-lock').mkdir();stale=snapshot(copied)
    cli(['--workspace',copied,'--no-browser'],demo=False,expected=2);assert snapshot(copied)==stale and (copied/'.session-lock').is_dir()
    result=json.loads(cli(['--workspace',copied,'--cli','recover','--confirm-stopped'],demo=False));assert result['status']=='SESSION_RECOVERED' and not (copied/'.session-lock').exists()
    with server(copied,demo=False) as url:assert api(url,'/api/artifact?id='+first['artifact_id'])==record
    checks.append('stale_session_refused_until_explicit_stopped_recovery_without_record_changes')
    with server(demo=False) as url:assert api(url,'/api/datasets')['datasets']==[] and api(url,'/api/artifacts')['artifacts']==[]
    assert blank.exists() and snapshot(default)==before;checks.append('blank_workspace_is_separate_and_does_not_modify_demo')
    complete=private/'original full CLI demo'
    full=json.loads(cli(['--workspace',complete,'--cli','demo'],demo=False))
    assert full['groups']==[['alpha',8],['beta',11]] and full['filtered_groups']==[['alpha',5],['beta',11]] and full['revision_groups']==[['alpha',9],['beta',12]]
    assert full['report_valid'] and full['private_export_files']==7 and full['artifacts']==4 and full['backup_validated']
    checks.append('original_full_cli_demo_report_validation_export_and_partial_backup_pass')
    if browser:
        from playwright.sync_api import sync_playwright,expect
        ui=private/'browser tutorial'
        with sync_playwright() as pw:
            chromium=pw.chromium.launch();page=chromium.new_page();errors=[];external=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def route(request):
                if request.request.url.startswith('http://127.0.0.1:'):request.continue_()
                else:external.append(request.request.url.split(':',1)[0]);request.abort()
            page.route('**/*',route)
            try:
                with server(ui) as url:
                    page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
                    page.locator('#run').click();expect(page.locator('#status')).to_have_text('Job finished: completed. Saved artifact is pending review.')
                    assert page.locator('#results tbody tr').all_inner_texts()==['alpha\t8','beta\t11'];selected=page.locator('#artifacts').input_value()
                    page.locator('#review-status').select_option('approved')
                    for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                    page.locator('#review-form button').click();expect(page.locator('#status')).to_have_text('Review recorded for this immutable artifact.')
                    page.locator('#export').click();expect(page.locator('#status')).to_have_text('Approved artifact exported inside the private workspace.')
                    ui_export=json.loads(page.locator('#export-output').inner_text());assert ui_export['manifest']['public_release_authorized'] is False
                    page.locator('#bindings').fill('{"minimum":4}');page.locator('#run').click();expect(page.locator('#status')).to_have_text('Job finished: completed. Saved artifact is pending review.')
                    assert page.locator('#results tbody tr').all_inner_texts()==['alpha\t5','beta\t11']
                    page.locator('summary').filter(has_text='Import or revise report XML').click();page.locator('#save-report').click();expect(page.locator('#status')).to_have_text('Inspected report revision saved; no datasets were run.')
                    page.locator('#validate-report').click();expect(page.locator('#status')).to_have_text('Job finished: completed. Saved artifact is pending review.');expect(page.locator('#result-state')).to_contain_text('fields valid: true')
                ui_before=snapshot(ui)
                with server(ui) as url:
                    page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
                    page.locator('#artifacts').select_option(selected);page.locator('#load-artifact').click();expect(page.locator('#status')).to_have_text('Saved artifact and review loaded; editor drafts retained.')
                    assert page.locator('#results tbody tr').all_inner_texts()==['alpha\t8','beta\t11'];expect(page.locator('#review-status')).to_have_value('approved')
                assert snapshot(ui)==ui_before
                restored=private/'browser full copy';shutil.copytree(ui,restored)
                with server(restored,demo=False) as url:
                    page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
                    page.locator('#artifacts').select_option(selected);page.locator('#load-artifact').click();expect(page.locator('#status')).to_have_text('Saved artifact and review loaded; editor drafts retained.')
                    assert page.locator('#results tbody tr').all_inner_texts()==['alpha\t8','beta\t11']
                assert snapshot(ui)==ui_before and (restored/ui_export['directory']/'manifest.json').read_bytes()==(ui/ui_export['directory']/'manifest.json').read_bytes()
                assert not errors and not external
                checks.append('chromium_bundled_process_queries_report_validation_review_export_restart_and_full_copy_recovery')
            finally:chromium.close()
    for row in manifest['files']:assert sha((root/row['path']).read_bytes())==row['sha256']
    checks.append('all_distribution_members_unchanged')
    result=dict(schema=1,status='PASS',package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],
                bundled_runtime=health['runtime'],core_tests=core,core_skips=int(skipped.group(1)) if skipped else 0,
                browser=browser,synthetic_only=True,checks=checks,
                scope='Restricted-PATH Windows runtime/process isolation; not a manual Python-free PC or Explorer/default-browser test. State-only backup is not full workspace recovery.')
    (packages/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
