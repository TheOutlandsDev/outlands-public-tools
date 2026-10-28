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
    default=local/'Outlands/DeveloperWorkspace/fictional-demo';blank=local/'Outlands/DeveloperWorkspace/workspace'
    checks=[]
    def command(args,demo=True):
        line=subprocess.list2cmdline([str(root/('Developer Demo.cmd' if demo else 'Developer Workspace.cmd')),*map(str,args)])
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
    assert core==55;checks.append('all_original_core_tests_run_under_bundled_runtime')

    def http(url,path,payload=None):
        from urllib.parse import urlsplit
        parsed=urlsplit(url);con=HTTPConnection(parsed.hostname,parsed.port,timeout=10)
        try:
            headers={}
            if path!='/':
                page=http(url,'/')[1].decode('utf-8');token=re.search(r"token='([^']+)'",page).group(1)
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
    def validate(url):
        saved=api(url,'/api/project?id=sample-project')
        value=api(url,'/api/validate',dict(project_id='sample-project',expected_sha256=saved['sha256']))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            value=api(url,'/api/job?id='+value['job_id'])
            if value['state']=='finished':
                assert value['result']['status']=='completed'
                return api(url,'/api/artifact?id='+value['result']['artifact_id'])
            time.sleep(.05)
        raise AssertionError('Owned validation worker did not finish.')
    def check_export(folder,receipt,original):
        directory=folder/receipt['directory'];raw=(directory/'project-source.zip').read_bytes()
        assert len(raw)==receipt['bytes'] and sha(raw)==receipt['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            m=json.loads(archive.read('manifest.json'))
            assert m['project_version']==1 and m['code_executed'] is False and m['public_release_authorized'] is False
            assert len(archive.namelist())==9 and set(archive.namelist())==set(m['files'])|{'manifest.json'}
            for name,row in m['files'].items():b=archive.read(name);assert len(b)==row['bytes'] and sha(b)==row['sha256']
            for file in original['definition']['files']:assert archive.read('source/'+file['path'])==file['content'].encode()
        return raw
    sentinel=private/'supplied-code-must-not-run.txt'
    with server() as url:
        assert api(url,'/api/projects')['projects']==[dict(project_id='sample-project',version=1)]
        assert api(url,'/api/artifacts')['artifacts']==[]
        first_project=api(url,'/api/project?id=sample-project');assert len(first_project['definition']['files'])==5
        cli(['--no-browser'],expected=2)
        first=validate(url);result=first['payload']['result']
        assert result['counts']==dict(fail=0,**{'pass':4},unchecked=1) and result['code_executed'] is False and result['all_files_checked'] is False
        canary='from pathlib import Path\nPath('+repr(str(sentinel))+').write_text("unexpected execution")\nvalue = 7\n'
        api(url,'/api/edit',dict(project_id='sample-project',expected_sha256=first_project['sha256'],path='src/sample.py',content=canary,operation='save'))
        second_project=api(url,'/api/project?id=sample-project');assert second_project['version']==2
        comparison=api(url,'/api/compare?id=sample-project&left=1&right=2')
        assert comparison['source_hash_comparison_complete'] and len(comparison['changes'])==1 and comparison['changes'][0]['path']=='src/sample.py'
        assert api(url,'/api/project?id=sample-project&version=1')==first_project
        second=validate(url);assert second['artifact_id']!=first['artifact_id'] and second['review']['status']=='pending'
        assert second['payload']['result']['counts']==dict(fail=0,**{'pass':4},unchecked=1) and not sentinel.exists()
        api(url,'/api/review',dict(artifact_id=first['artifact_id'],artifact_sha256=first['artifact_sha256'],expected_version=0,status='approved',actor='fictional_reviewer',note='Static checks only; inspect unchecked text separately',checks=dict(quality=True,privacy=True,rights=True,context=True)))
        exported=api(url,'/api/export',dict(artifact_id=first['artifact_id']))
        historical=api(url,'/api/artifact?id='+first['artifact_id'])
        assert historical['review']['status']=='approved' and api(url,'/api/artifact?id='+second['artifact_id'])['review']['status']=='pending'
    checks+=['default_demo_seeds_five_files_in_revision_one_without_running_checks','existing_running_instance_refused',
             'validation_reports_four_pass_one_unchecked_without_executing_supplied_code',
             'one_file_edit_creates_revision_two_and_preserves_revision_one',
             'distinct_validation_and_review_states_remain_independent']
    export_bytes=check_export(default,exported,first_project)
    checks.append('historical_nine_member_export_preserves_every_revision_one_file')
    before=snapshot(default)
    with server() as url:
        assert api(url,'/api/project?id=sample-project')==second_project and api(url,'/api/artifact?id='+first['artifact_id'])==historical
        assert len(api(url,'/api/artifacts')['artifacts'])==2 and not sentinel.exists()
    assert snapshot(default)==before;checks.append('real_new_process_reopens_saved_revisions_reviews_and_export_without_reseed')
    copied=private/'stopped complete workspace copy';shutil.copytree(default,copied);assert snapshot(copied)==before
    with server(copied,demo=False) as url:
        assert api(url,'/api/project?id=sample-project&version=1')==first_project and api(url,'/api/project?id=sample-project')==second_project
        assert api(url,'/api/artifact?id='+first['artifact_id'])==historical
    assert snapshot(default)==before and snapshot(copied)==before and check_export(copied,exported,first_project)==export_bytes
    checks.append('stopped_full_copy_reopens_history_and_exact_export_with_original_unchanged')
    (copied/'.session-lock').mkdir()
    cli(['--workspace',copied,'--no-browser'],demo=False,expected=2)
    assert (copied/'.session-lock').is_dir() and snapshot(copied)==before
    recovered=json.loads(cli(['--workspace',copied,'--cli','recover','--confirm-stopped'],demo=False))
    assert recovered['status']=='SESSION_RECOVERED' and not (copied/'.session-lock').exists() and snapshot(copied)==before
    checks.append('stale_session_requires_explicit_stopped_recovery_without_record_changes')
    with server(demo=False) as url:assert api(url,'/api/projects')['projects']==[] and api(url,'/api/artifacts')['artifacts']==[]
    assert blank.exists() and snapshot(default)==before;checks.append('blank_workspace_is_separate_and_does_not_modify_demo')
    complete=private/'original full CLI demo';full=json.loads(cli(['--workspace',complete,'--cli','demo'],demo=False))
    assert full==dict(mode='FICTIONAL_DEVELOPER_WORKSPACE_DEMO',projects=1,files=5,versions=2,checked=4,unchecked=1,changed_files=1,validation_artifacts=2,new_review_pending=True,private_export_members=9,export_version=1,backup_validated=True,project_code_executed=False,external_services_used=False)
    checks.append('original_full_cli_demo_comparison_historical_export_and_partial_backup_pass')
    if browser:
        from playwright.sync_api import sync_playwright,expect
        ui=private/'browser tutorial'
        with sync_playwright() as pw:
            chromium=pw.chromium.launch();page=chromium.new_page();errors=[];external=[];origin={'url':''}
            page.on('pageerror',lambda error:errors.append(str(error)))
            def route(request):
                if request.request.url.startswith(origin['url']):request.continue_()
                else:external.append(request.request.url.split(':',1)[0]);request.abort()
            page.route('**/*',route)
            try:
                with server(ui) as url:
                    origin['url']=url;page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
                    assert page.locator('#files option').count()==5;expect(page.locator('#versions')).to_have_value('1')
                    page.locator('#validate').click();expect(page.locator('#status')).to_have_text('Validation finished: completed. New artifact is pending review.')
                    expect(page.locator('#validation')).to_contain_text('"pass": 4');expect(page.locator('#validation')).to_contain_text('"unchecked": 1')
                    selected=page.locator('#artifacts').input_value()
                    page.locator('#review-status').select_option('approved')
                    for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                    page.locator('#review').click();expect(page.locator('#status')).to_have_text('Review saved for this exact validation and source revision.')
                    page.locator('#files').select_option('src/sample.py');expect(page.locator('#path')).to_have_value('src/sample.py')
                    page.locator('#editor').fill('def total(values):\n    return sum(values) + 1\n');page.locator('#save').click()
                    expect(page.locator('#status')).to_have_text('File saved in immutable project history. No code executed.');expect(page.locator('#versions')).to_have_value('2')
                    page.locator('#left').select_option('1');page.locator('#right').select_option('2');page.locator('#compare').click()
                    expect(page.locator('#status')).to_have_text('Saved source hashes compared. Diff preview limits are explicit.');expect(page.locator('#diff')).to_contain_text('src/sample.py')
                    page.locator('#validate').click();expect(page.locator('#status')).to_have_text('Validation finished: completed. New artifact is pending review.');expect(page.locator('#review-status')).to_have_value('pending')
                    page.locator('#artifacts').select_option(selected);expect(page.locator('#review-status')).to_have_value('approved')
                    page.locator('#export').click();expect(page.locator('#status')).to_have_text('Approved source exported inside the private workspace. Review before sharing.')
                    ui_receipt=json.loads(page.locator('#receipt').inner_text());check_export(ui,ui_receipt,first_project)
                ui_before=snapshot(ui)
                with server(ui) as url:
                    origin['url']=url;page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.');expect(page.locator('#versions')).to_have_value('2')
                    page.locator('#artifacts').select_option(selected);expect(page.locator('#review-status')).to_have_value('approved')
                    expect(page.locator('#review-context')).to_contain_text('"version": 1')
                assert snapshot(ui)==ui_before
                restored=private/'browser complete copy';shutil.copytree(ui,restored)
                with server(restored,demo=False) as url:
                    origin['url']=url;page.goto(url);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
                    page.locator('#versions').select_option('1');expect(page.locator('#status')).to_have_text('Saved revision loaded.')
                    page.locator('#files').select_option('src/sample.py');expect(page.locator('#editor')).to_have_value('def total(values):\n    return sum(values)\n')
                    page.locator('#artifacts').select_option(selected);expect(page.locator('#review-status')).to_have_value('approved')
                assert snapshot(ui)==ui_before and check_export(restored,ui_receipt,first_project)==check_export(ui,ui_receipt,first_project)
                assert not errors and not external
                checks.append('chromium_bundled_process_edit_validate_compare_historical_export_restart_and_full_copy_recovery')
            finally:chromium.close()
    for row in manifest['files']:assert sha((root/row['path']).read_bytes())==row['sha256']
    assert not sentinel.exists();checks.append('all_distribution_members_unchanged_and_execution_canary_absent')
    result=dict(schema=1,status='PASS',package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],
                bundled_runtime=health['runtime'],core_tests=core,core_skips=int(skipped.group(1)) if skipped else 0,
                browser=browser,synthetic_only=True,checks=checks,
                scope='Restricted-PATH Windows runtime/process isolation; not a manual Python-free PC or Explorer/default-browser test. Syntax is not runtime correctness; state-only backup omits inbox and exports.')
    (packages/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
