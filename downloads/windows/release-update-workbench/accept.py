"""Fresh Windows download qualification; only synthetic summaries/captures are public."""
import argparse
from contextlib import contextmanager
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
import time
from urllib.parse import urlsplit
import zipfile
from build import FILENAME,PREFIX,sha,encoded,members


def tree(root):return {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def accept(packages,workspace,browser=False):
    if os.name!='nt' or not workspace.is_absolute() or workspace.exists() or not workspace.parent.is_dir():raise ValueError('NEW_WINDOWS_WORKSPACE_REQUIRED')
    if browser and os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('HOSTED_BROWSER_QUALIFICATION_ONLY')
    receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes()
    assert sha(raw)==receipt['sha256'];contents=members(raw)
    manifest=json.loads(contents[PREFIX+'PACKAGE-MANIFEST.json'])
    assert len(contents)==receipt['files'] and set(contents)=={PREFIX+r['path'] for r in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
    for row in manifest['files']:
        b=contents[PREFIX+row['path']];assert row==dict(path=row['path'],bytes=len(b),sha256=sha(b))
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir()
    before=tree(root);pwsh=shutil.which('pwsh');assert pwsh
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),
         'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),
         'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_LINKS':'1',
         'PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Update Exercise.cmd' if exercise else 'Update Demo.cmd')),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,exercise=False,expected=0):
        p=subprocess.run(command(args,exercise),cwd=private,env=env,capture_output=True,timeout=90)
        (private/'last-cli.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==expected,'CMD check failed; private log retained.'
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime']
    assert tree(root)==before;checks.append('cmd_uses_isolated_bundled_runtime_without_system_python_or_state')
    p=subprocess.run([python,'-I','-B',str(app/'release_source.py'),'check'],cwd=app,env=env,capture_output=True,timeout=30)
    assert p.returncode==0 and json.loads(p.stdout)['status']=='SOURCE_MATCH';checks.append('original_source_inventory_preserved')
    p=subprocess.run([python,'-I','-B','-W','error',str(app/'run_checks.py')],cwd=app,env=env,capture_output=True,timeout=240)
    (private/'core-tests.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Bundled core checks failed; private log retained.'
    log=p.stderr.decode('utf-8');assert re.search(r'Ran 55 tests?',log) and 'skipped=1' in log
    checks.append('all_55_original_core_checks_on_bundled_python_eight_native_fixtures_one_opposite_platform_skip')
    exercise_workspace=private/'new update exercise'
    outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0])
    assert outcome['status']=='PASS' and outcome['command_checks']==34
    assert [outcome[k] for k in ('snapshots','files_per_snapshot','blockers_before','blockers_after','private_handoff_files')]==[2,4,5,0,8]
    assert outcome['file_counts']==dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1)
    assert all(outcome[k] is True for k in ('blocked_approval_refused','unapproved_export_refused','revoked_export_refused','input_bytes_unchanged','copied_snapshots_unchanged','fictional_target_unchanged'))
    assert all(outcome[k] is False for k in ('new_plan_inherits_approval','target_updates_performed','programs_executed','network_probed','rollback_restore_performed'))
    assert outcome['manual_checkpoints']=='NOT_PERFORMED'
    checks.append('cmd_exercise_runs_34_original_cli_commands_with_independent_snapshot_handoff_and_target_preservation_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2)
    assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    overview=json.loads(cli(['--workspace',exercise_workspace,'--cli','overview']))
    assert [len(overview[k]) for k in ('candidates','comparisons','plans')]==[2,2,3] and overview['unfinished_jobs']==0 and overview['target_updates_plan_only']
    assert sorted(row['status'] for row in overview['reviews'].values())==['REVOKED']
    checks.append('original_cli_reopens_registered_snapshots_plans_and_revocation')
    gui_workspace=private/'browser update practice'
    @contextmanager
    def server():
        p=subprocess.Popen(command(['--workspace',gui_workspace,'--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        lines=queue.Queue();log=(private/'last-server.log').open('w',encoding='utf-8')
        def read():
            for line in p.stdout:log.write(line);log.flush();lines.put(line)
            lines.put(None)
        worker=threading.Thread(target=read,daemon=True);worker.start();value={}
        def http(path,body=None,expected=200):
            parts=urlsplit(value['url']);conn=HTTPConnection(parts.hostname,parts.port,timeout=10)
            try:
                conn.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers={'X-Outlands-Token':value.get('token',''),'Content-Type':'application/json'});res=conn.getresponse();raw=res.read();assert res.status==expected;return raw
            finally:conn.close()
        value['http']=http
        try:
            while True:
                line=lines.get(timeout=30)
                if line is None:raise AssertionError('Server stopped before ready; private log retained.')
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
    captures={};browser_update={}
    if browser:
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[]
            page.on('request',lambda request:requests.append(request.url))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium and bundled Python; invented package snapshots and supplied policy assertions; no address bar, absolute paths or session token')
            def state(s):return json.loads(s['http']('/api/overview'))
            def review_checks():
                for name in ('quality','privacy','rights','context'):page.locator('#'+name).check()
            def refusal(s,path,body,code):
                request=dict(expected_head=state(s)['head'],actor='sample_operator',reason='Fictional package acceptance refusal',**body)
                assert json.loads(s['http'](path,request,400))==dict(error=code)
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_contain_text('Private instance ready')
                sentinel=gui_workspace/'inbox/fictional-target.txt';sentinel.write_bytes(b'Invented target sentinel; never apply an update.');inputs=tree(gui_workspace/'inbox')
                page.locator('#capture-button').click();expect(page.locator('#status')).to_contain_text('Fresh private snapshot captured and verified')
                page.locator('#fixture').select_option('v2');page.locator('#load-fixture').click();expect(page.locator('#status')).to_contain_text('Invented request loaded')
                page.locator('#capture-button').click();expect(page.locator('#status')).to_contain_text('Fresh private snapshot captured and verified')
                candidates=state(s)['candidates'];assert len(candidates)==2;snapshots={}
                for row in candidates:
                    folder=gui_workspace/row['target'];descriptor=json.loads((folder/'candidate.json').read_bytes())
                    assert sha((folder/'candidate.json').read_bytes())==row['candidate_sha256']
                    actual={p.relative_to(folder/'payload').as_posix():dict(size=p.stat().st_size,sha256=sha(p.read_bytes())) for p in (folder/'payload').rglob('*') if p.is_file()}
                    assert actual=={v['path']:dict(size=v['size'],sha256=v['sha256']) for v in descriptor['inventory']} and len(actual)==4
                    snapshots[row['candidate_id']]=(folder,tree(folder))
                checks.append('actual_browser_two_four_file_snapshots_independently_match_copied_payload_hashes')
                page.locator('#compare').click();expect(page.locator('#status')).to_contain_text('Pinned comparison saved')
                blocked=state(s)['comparisons'][-1];assert blocked['blocker_count']==5
                page.locator('#make-plan').click();expect(page.locator('#status')).to_contain_text('Manual plan saved pending review')
                blocked_plan=state(s)['plans'][-1];expect(page.locator('#approve')).to_be_disabled()
                refusal(s,'/api/review',dict(plan_id=blocked_plan['plan_id'],plan_sha256=blocked_plan['plan_sha256'],approve=True,checks={k:True for k in ('quality','privacy','rights','context')}),'BLOCKED_PLAN_CANNOT_BE_APPROVED')
                capture('update-blocked.jpg');checks.append('actual_browser_five_blockers_disable_approval_and_backend_refuses_blocked_plan')
                for name in ('backup_confirmed','target_stopped_confirmed','readiness_confirmed','allow_removals','dependency_reviewed'):page.locator('#'+name).check()
                page.locator('#compare').click();expect(page.locator('#status')).to_contain_text('Pinned comparison saved')
                ready=state(s)['comparisons'][-1];assert ready['blocker_count']==0 and ready['counts']==dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1)
                assert json.loads(page.locator('#lock-data').inner_text())['counts']['version_text_changed']==1
                page.locator('#make-plan').click();expect(page.locator('#status')).to_contain_text('Manual plan saved pending review')
                planned=state(s)['plans'][-1];inspected=json.loads(page.locator('#plan-data').inner_text());plan=inspected['content']
                assert plan['plan_only'] and not plan['execution_authorized'] and not plan['runtime_verified']
                assert all(row['status']=='NOT_PERFORMED' for row in plan['steps']) and not plan['rollback']['backup_independently_verified'] and not plan['rollback']['restore_performed']
                expect(page.locator('#export')).to_be_disabled();checks.append('actual_browser_exact_file_and_lock_changes_create_only_unperformed_manual_checkpoints')
                review_checks();page.locator('#approve').click();expect(page.locator('#status')).to_contain_text('Plan approved for private handoff only')
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('REVIEW_REQUIRED');assert not list((gui_workspace/'reports').iterdir())
                review_checks();page.locator('#export').click();expect(page.locator('#status')).to_contain_text('Approved private evidence handoff created')
                report=json.loads(page.locator('#handoff').inner_text());folder=gui_workspace/report['directory'];manifest=report['manifest']
                assert len(manifest['files'])==7 and manifest['target_updates_plan_only'] and not manifest['payload_files_included'] and not manifest['execution_authorized'] and not manifest['public_release_authorized']
                assert set(p.name for p in folder.iterdir())==set(manifest['files'])|{'manifest.json'} and json.loads((folder/'manifest.json').read_bytes())==manifest
                for name,row in manifest['files'].items():
                    body=(folder/name).read_bytes();assert row==dict(bytes=len(body),sha256=sha(body))
                handed_off=tree(folder);capture('update-approved.jpg');checks.append('actual_browser_scoped_approval_fresh_export_review_and_all_eight_private_handoff_hashes_verify')
                page.locator('#comparisons').select_option(ready['comparison_id']);page.locator('#inspect-comparison').click();expect(page.locator('#status')).to_contain_text('Saved comparison and both snapshot payloads verified')
                page.locator('#make-plan').click();expect(page.locator('#status')).to_contain_text('Manual plan saved pending review')
                another=state(s)['plans'][-1];assert another['plan_id']!=planned['plan_id'] and another['plan_id'] not in state(s)['reviews']
                expect(page.locator('#export')).to_be_disabled();expect(page.locator('#decision')).to_contain_text('PENDING_REVIEW')
                refusal(s,'/api/export',dict(plan_id=another['plan_id'],checks={k:True for k in ('quality','privacy','rights','context')}),'CURRENT_PLAN_APPROVAL_REQUIRED')
                capture('update-new-plan.jpg');checks.append('actual_browser_new_plan_inherits_no_approval_and_backend_refuses_unapproved_export')
                page.locator('#plans').select_option(planned['plan_id']);page.locator('#inspect-plan').click();expect(page.locator('#status')).to_contain_text('Plan, comparison and snapshot bytes verified')
                review_checks();page.locator('#revoke').click();expect(page.locator('#status')).to_contain_text('Plan approval revoked')
                expect(page.locator('#export')).to_be_disabled();expect(page.locator('#decision')).to_contain_text('REVOKED')
                refusal(s,'/api/export',dict(plan_id=planned['plan_id'],checks={k:True for k in ('quality','privacy','rights','context')}),'CURRENT_PLAN_APPROVAL_REQUIRED')
                assert tree(folder)==handed_off;revoked=json.loads(page.locator('#plan-data').inner_text())
                capture('update-revoked.jpg');checks.append('actual_browser_revocation_blocks_backend_and_future_exports_while_previous_handoff_is_retained')
                page.locator('#backup').click();expect(page.locator('#status')).to_contain_text('Private index backup verified')
                backup=json.loads(page.locator('#handoff').inner_text());assert backup['contains_private_inputs'] and not backup['includes_payload_or_artifact_files']
                assert sha((gui_workspace/backup['file']).read_bytes())==backup['sha256'] and tree(gui_workspace/'inbox')==inputs
                assert all(tree(path)==original for path,original in snapshots.values())
                checks.append('actual_browser_index_scope_input_snapshot_and_fictional_target_preservation_verified')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#reason')).to_be_focused()
                assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_layout_and_keyboard_navigation')
                browser_update=dict(snapshots=2,files_per_snapshot=4,file_counts=ready['counts'],blockers_before=5,blockers_after=0,lock_version_text_changes=1,blocked_approval_refused=True,unapproved_export_refused=True,new_plan_inherits_approval=False,revoked_export_refused=True,private_handoff_files=8,handoff_hashes_independently_verified=True,previous_handoff_retained=True,input_bytes_unchanged=True,copied_snapshots_unchanged=True,fictional_target_unchanged=True,manual_checkpoints='NOT_PERFORMED',rollback_restore_performed=False,target_updates_performed=False,programs_executed=False,network_probed=False)
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping')
            with server() as s:
                reopened=state(s);assert [len(reopened[k]) for k in ('candidates','comparisons','plans')]==[2,2,3] and reopened['reviews'][planned['plan_id']]['status']=='REVOKED'
                page.goto(s['url']);expect(page.locator('#plan-count')).to_have_text('3')
                page.locator('#plans').select_option(planned['plan_id']);page.locator('#inspect-plan').click();expect(page.locator('#decision')).to_contain_text('REVOKED')
                assert json.loads(page.locator('#plan-data').inner_text())==revoked and tree(gui_workspace/'inbox')==inputs and tree(folder)==handed_off
                assert all(tree(path)==original for path,original in snapshots.values())
                page.locator('#stop').click();s['shutdown_requested']=True
            context.close();assert all(url.startswith('http://127.0.0.1:') for url in requests)
        checks.append('saved_decisions_and_original_snapshot_pins_reopened_and_owned_servers_stopped')
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=55,core_skips=1,checks=checks,exercise=outcome,browser_update=browser_update,captures=captures,scope='Fictional Windows CMD/browser snapshot, approval and revocation qualification; no real update, payload execution, compatibility, recovery or separate-PC acceptance')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
