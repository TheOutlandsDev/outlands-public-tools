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
        line=subprocess.list2cmdline([str(root/('Setup Exercise.cmd' if exercise else 'Setup Demo.cmd')),*map(str,args)])
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
    log=p.stderr.decode('utf-8');assert re.search(r'Ran 57 tests?',log) and 'skipped=1' in log
    checks.append('all_57_original_core_checks_on_bundled_python_seven_native_fixtures_one_opposite_platform_skip')
    exercise_workspace=private/'new setup exercise'
    outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0])
    assert outcome['status']=='PASS' and outcome['command_checks']==19
    assert [outcome[k] for k in ('checks','blocked_steps_before','blocked_steps_after','private_handoff_files')]==[9,3,0,6]
    assert outcome['ordered_steps']==['prepare','review','handoff'] and outcome['review_refused'] and outcome['input_bytes_unchanged']
    assert outcome['manual_verifications']=='NOT_PERFORMED' and all(outcome[k] is False for k in ('runtime_verified','programs_executed','network_probed'))
    checks.append('cmd_exercise_runs_19_original_cli_commands_with_independent_artifact_and_handoff_hash_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2)
    assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    overview=json.loads(cli(['--workspace',exercise_workspace,'--cli','overview']))
    assert [len(overview[k]) for k in ('profiles','evaluations','plans')]==[1,2,1] and overview['unfinished_jobs']==0 and overview['plan_only']
    checks.append('original_cli_reopens_registered_profiles_evaluations_and_plan')
    gui_workspace=private/'browser setup practice'
    @contextmanager
    def server():
        p=subprocess.Popen(command(['--workspace',gui_workspace,'--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        lines=queue.Queue();log=(private/'last-server.log').open('w',encoding='utf-8')
        def read():
            for line in p.stdout:log.write(line);log.flush();lines.put(line)
            lines.put(None)
        worker=threading.Thread(target=read,daemon=True);worker.start();value={}
        def http(path,body=None):
            parts=urlsplit(value['url']);conn=HTTPConnection(parts.hostname,parts.port,timeout=10)
            try:
                conn.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers={'X-Outlands-Token':value.get('token',''),'Content-Type':'application/json'});res=conn.getresponse();raw=res.read();assert res.status==200;return raw
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
    captures={};browser_setup={}
    if browser:
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=15000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[]
            page.on('request',lambda request:requests.append(request.url))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium and bundled Python; invented supplied declarations only; no address bar, absolute paths or session token')
            def state(s):return json.loads(s['http']('/api/overview'))
            def approve():
                for name in ('quality','privacy','rights','context'):page.locator('#'+name).check()
            def read_evaluation(s,identifier):return json.loads(s['http']('/api/inspect?kind=evaluation&id='+identifier))['content']
            def evaluation_oracle(value,blocked):
                assert value['summary']['checks']==9 and value['summary']['blocked_steps']==blocked
                assert [row['id'] for row in value['steps']]==['prepare','review','handoff']
                assert all(row['verification_status']=='NOT_PERFORMED' for row in value['steps'])
                assert all(value[k] is False for k in ('runtime_verified','network_probed','programs_executed','host_inventory_collected','configuration_modified'))
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_contain_text('Private instance ready')
                inputs={n:sha((gui_workspace/'inbox'/n).read_bytes()) for n in ('profile.json','observations.json')}
                page.locator('#save-profile').click();expect(page.locator('#status')).to_contain_text('New profile revision saved')
                observations=json.loads(page.locator('#observations').input_value());observations['prerequisites']['sample_runtime']='MISSING'
                page.locator('#observations').fill(json.dumps(observations));page.locator('#evaluate').click();expect(page.locator('#status')).to_contain_text('Pinned evaluation saved')
                first=state(s)['evaluations'][0];bad=read_evaluation(s,first['evaluation_id']);evaluation_oracle(bad,3)
                assert bad['status']=='REVIEW_REQUIRED' and bad['summary']['blocking_checks']==1
                expect(page.locator('#summary')).to_contain_text('3 blocked steps');capture('setup-blocked.jpg')
                checks.append('actual_browser_missing_runtime_declaration_blocks_all_three_manual_steps')
                observations['prerequisites']['sample_runtime']='PRESENT';page.locator('#observations').fill(json.dumps(observations));page.locator('#evaluate').click();expect(page.locator('#status')).to_contain_text('Pinned evaluation saved')
                second=state(s)['evaluations'][-1];good=read_evaluation(s,second['evaluation_id']);evaluation_oracle(good,0)
                assert good['status']=='DECLARATIONS_SATISFIED' and good['summary']['blocking_checks']==0
                page.locator('#compare-evaluation').select_option(first['evaluation_id']);page.locator('#compare-evaluations').click();expect(page.locator('#status')).to_contain_text('Saved evaluation statuses compared')
                assert json.loads(page.locator('#evaluation-diff').inner_text())['changes']['checks']['changed']==['prerequisite:sample_runtime']
                checks.append('actual_browser_nine_satisfied_declarations_and_exact_single_check_comparison')
                page.locator('#make-plan').click();expect(page.locator('#status')).to_have_text('REVIEW_REQUIRED');assert state(s)['plans']==[]
                capture('setup-review-refused.jpg');checks.append('actual_browser_missing_review_refused_without_plan_creation')
                approve();page.locator('#make-plan').click();expect(page.locator('#status')).to_contain_text('Reviewed plan saved')
                planned=state(s)['plans'][0];page.locator('#inspect-plan').click();expect(page.locator('#status')).to_contain_text('Registered plan and all upstream pins verified')
                inspected=json.loads(page.locator('#plan-data').inner_text());assert inspected['result']==planned
                assert inspected['content']['plan_only'] and not inspected['content']['execution_authorized'] and not inspected['content']['runtime_verified']
                checks.append('actual_browser_reviewed_plan_pins_original_evaluation_without_execution_authority')
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('REVIEW_REQUIRED');assert not list((gui_workspace/'reports').iterdir())
                approve();page.locator('#export').click();expect(page.locator('#status')).to_contain_text('Reviewed private handoff created')
                report=json.loads(page.locator('#handoff').inner_text());folder=gui_workspace/report['directory'];manifest=report['manifest']
                assert len(manifest['files'])==5 and manifest['plan_only'] and not manifest['execution_authorized'] and not manifest['public_release_authorized']
                assert set(p.name for p in folder.iterdir())==set(manifest['files'])|{'manifest.json'}
                assert json.loads((folder/'manifest.json').read_bytes())==manifest
                for name,row in manifest['files'].items():
                    raw=(folder/name).read_bytes();assert row==dict(bytes=len(raw),sha256=sha(raw))
                capture('setup-plan.jpg');checks.append('actual_browser_private_export_requires_fresh_review_and_all_six_handoff_files_verify')
                page.locator('#backup').click();expect(page.locator('#status')).to_contain_text('Private index backup verified')
                backup=json.loads(page.locator('#handoff').inner_text());assert backup['contains_private_inputs'] and not backup['includes_artifact_files']
                assert sha((gui_workspace/backup['file']).read_bytes())==backup['sha256']
                assert all(sha((gui_workspace/'inbox'/n).read_bytes())==pin for n,pin in inputs.items())
                checks.append('actual_browser_index_backup_scope_and_unchanged_fictional_inputs_verified')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#reason')).to_be_focused()
                assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_layout_and_keyboard_navigation')
                browser_setup=dict(checks=9,blocked_steps_before=3,blocked_steps_after=0,changed_checks=['prerequisite:sample_runtime'],ordered_steps=['prepare','review','handoff'],missing_review_refused=True,export_without_review_refused=True,private_handoff_files=6,handoff_hashes_independently_verified=True,input_bytes_unchanged=True,manual_verifications='NOT_PERFORMED',runtime_verified=False,programs_executed=False,network_probed=False)
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping')
            with server() as s:
                reopened=state(s);assert [len(reopened[k]) for k in ('profiles','evaluations','plans')]==[1,2,1]
                page.goto(s['url']);expect(page.locator('#plan-count')).to_have_text('1')
                page.locator('#plans').select_option(planned['plan_id']);page.locator('#inspect-plan').click();expect(page.locator('#status')).to_contain_text('Registered plan and all upstream pins verified')
                assert json.loads(page.locator('#plan-data').inner_text())==inspected
                assert all(sha((gui_workspace/'inbox'/n).read_bytes())==pin for n,pin in inputs.items())
                page.locator('#stop').click();s['shutdown_requested']=True
            context.close();assert all(url.startswith('http://127.0.0.1:') for url in requests)
        checks.append('saved_instance_reopened_without_reseed_and_owned_servers_stopped')
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=57,core_skips=1,checks=checks,exercise=outcome,browser_setup=browser_setup,captures=captures,scope='Fictional Windows CMD/browser declaration and manual-plan qualification; no real setup, target execution, runtime readiness or separate-PC acceptance')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
