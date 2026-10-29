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
from build import FILENAME,PREFIX,sha,encoded,members,download

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
        line=subprocess.list2cmdline([str(root/('Analytics Exercise.cmd' if exercise else 'Analytics Demo.cmd')),*map(str,args)])
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
    assert re.search(r'Ran 89 tests?',p.stderr.decode('utf-8')) and 'skipped=1' in p.stderr.decode('utf-8')
    core=p.stderr.decode('utf-8')
    for name in ('test_native_hardlink_input_refused','test_native_database_hardlink_refused','test_native_symlink_input_refused','test_native_symlink_parent_refused','test_native_junction_input_parent_refused','test_windows_stream_refused'):
        assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_89_original_core_methods_on_bundled_python_five_required_native_boundaries_one_opposite_platform_skip')
    exercise_workspace=private/'new data exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==20
    assert outcome['planning_totals']==[160,25,85,50] and outcome['initial_completions']==25 and outcome['final_completions']==33
    checks.append('cmd_exercise_20_original_cli_calls_independent_arithmetic_revision_report_and_backup_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    snapshot=json.loads(cli(['--workspace',exercise_workspace,'--cli','show','--project','sample-operations']));assert snapshot['sequence']==3
    checks.append('original_cli_reopens_saved_third_revision')
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


    # Companion source is supplied only to the original browser test copy.
    sources=private/'original-sources';sources.mkdir();original=sources/'operations-analytics-workbench';shutil.copytree(app,original)
    companion_source=members(download('https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/production-planning-workbench-v0.1.1/production-planning-workbench-source.zip','30ede891b1408effe56b607783a4b6fa083f61974786d44627ecbcdf86fc4263',2*1024*1024))
    for n,b in companion_source.items():
        f=sources/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
    # A separately pinned public Windows package makes a fresh report with no
    # source interpreter or Pydantic installation in the runtime environment.
    companion_raw=download('https://github.com/TheOutlandsDev/outlands-public-tools/releases/download/production-planning-workbench-windows-v0.1.1-1/production-planning-workbench-0.1.1-windows-x64.zip','dfda8bd89c94a82ede1d81e6b7fae63393d706c9f3c3c34c6aa18f7c6a665b9d',40*1024*1024)
    companion_files=members(companion_raw);companion_prefix='production-planning-workbench-0.1.1-windows-x64/';companion_root=private/companion_prefix.rstrip('/')
    for n,b in companion_files.items():
        f=private/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
    companion_manifest=json.loads(companion_files[companion_prefix+'PACKAGE-MANIFEST.json'])
    assert set(companion_files)=={companion_prefix+r['path'] for r in companion_manifest['files']}|{companion_prefix+'PACKAGE-MANIFEST.json'}
    for row in companion_manifest['files']:
        b=companion_files[companion_prefix+row['path']];assert row==dict(path=row['path'],bytes=len(b),sha256=sha(b))
    planner=private/'fresh stopped planning instance'
    def planning(*args):
        p=subprocess.run([str(companion_root/'runtime/python.exe'),'-I','-B',str(companion_root/'application/workbench.py'),'--workspace',str(planner),*args],env=env,cwd=private,capture_output=True,timeout=60);(private/'last-planning.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0;assert not (planner/'.session-lock').exists();return json.loads(p.stdout)
    planning('init');planning('import','--file','inbox/sample-project.json');fresh=planning('export','--project','sample-workshop');fresh_report=planner/fresh['directory']
    assert tree(fresh_report)==tree(root/'examples/planning-report');checks.append('fresh_separately_pinned_planning_windows_export_matches_all_five_curated_fixture_bytes_and_is_stopped')
    captures={};browser_data={};original_browser_tests=0
    if browser:
        test_env={**os.environ,'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_HANDOFF':'1'};test_env.pop('OUTLANDS_BROWSER_EVIDENCE',None)
        p=subprocess.run([sys.executable,'-B','-W','error',str(original/'run_browser_checks.py')],cwd=original,env=test_env,capture_output=True,timeout=360);(private/'original-browser-tests.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0 and re.search(r'Ran 25 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=25;checks.append('all_25_original_browser_methods_including_three_required_actual_source_handoffs_on_separate_test_python_without_skips')
        from playwright.sync_api import sync_playwright,expect
        from analytics_demo import oracle,reference,report
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual hosted Windows Chromium and bundled Analytics/Planning runtimes; invented data only; no address bar, machine path or token')
            def view(s):return json.loads(s['http']('/api/view?project=sample-operations'))
            def tab(name):page.locator('[data-tab='+name+']').click()
            with server() as s:
                page.goto(s['url']);expect(page.locator('#message')).to_have_text('Scenario loaded');first=view(s);oracle(first['plan']);assert first['plan']['snapshot']['completed_units']==25 and first['plan']['planning_reference'] is None;capture('analytics-baseline.jpg')
                assert tree(gui_workspace/'inbox/sample-planning-report')==tree(fresh_report)
                target=gui_workspace/'inbox/fresh-planning-report';target.mkdir()
                for f in fresh_report.iterdir():shutil.copyfile(f,target/f.name)
                input_bytes=tree(gui_workspace/'inbox');checks.append('actual_bundled_browser_new_demo_has_25_completions_and_independent_declared_capacity_process_inventory_dispatch_metrics')
                page.locator('#export').click();expect(page.locator('#message')).to_contain_text('outlands-analytics-report-v1');exported=json.loads(page.locator('#message').inner_text());assert report(gui_workspace,exported)==first['plan'];old_report=tree(gui_workspace/exported['directory'])
                tab('review');page.locator('#planning-directory').fill('inbox/fresh-planning-report');page.locator('#attach').click();expect(page.locator('#message')).to_contain_text('"sequence": 2');attached=view(s);ref=reference(attached['plan'])
                assert ref['manifest_sha256']==sha((fresh_report/'manifest.json').read_bytes()) and attached['plan']['snapshot']==first['plan']['snapshot'] and attached['plan']['dispatch']==first['plan']['dispatch'];capture('analytics-reference.jpg')
                checks.append('actual_bundled_browser_attaches_the_fresh_stopped_five_file_planning_export_without_completion_or_dispatch_mapping')
                page.locator('#ingest').click();expect(page.locator('#message')).to_contain_text('"inserted_events": 1');after=view(s);assert after['snapshot']['sequence']==3 and after['plan']['snapshot']['completed_units']==33 and after['plan']['snapshot']['completion_events']==3;before_replay=tree(gui_workspace)
                page.locator('#ingest').click();expect(page.locator('#message')).to_contain_text('"created": false');assert view(s)==after and tree(gui_workspace)==before_replay
                tab('board');expect(page.locator('#stats strong').first).to_have_text('33');capture('analytics-completions.jpg');checks.append('actual_bundled_completion_batch_25_to_33_replay_inserts_zero_events_and_no_revision_or_byte_change')
                before_refusal=tree(gui_workspace);stale=dict(project_id='sample-operations',directory='inbox/fresh-planning-report',expected=first['snapshot']['revision_sha256']);assert json.loads(s['http']('/api/attach-planning',stale,400))==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal
                changed=json.loads((gui_workspace/'inbox/sample-events.json').read_bytes());changed[0]['units']+=1;(gui_workspace/'inbox/conflict.json').write_text(json.dumps(changed),encoding='utf-8');before_refusal=tree(gui_workspace)
                assert json.loads(s['http']('/api/ingest',dict(project_id='sample-operations',file='inbox/conflict.json',expected=after['snapshot']['revision_sha256']),400))==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal
                bad=gui_workspace/'inbox/tampered-report';shutil.copytree(target,bad);(bad/'orders.csv').write_bytes((bad/'orders.csv').read_bytes()+b'fictional tamper');before_refusal=tree(gui_workspace)
                assert json.loads(s['http']('/api/attach-planning',dict(project_id='sample-operations',directory='inbox/tampered-report',expected=after['snapshot']['revision_sha256']),400))==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal and view(s)==after
                checks.append('actual_bundled_stale_revision_changed_event_identity_and_tampered_report_refused_without_writes')
                page.locator('#export').click();expect(page.locator('#message')).to_contain_text('outlands-analytics-report-v1');final_export=json.loads(page.locator('#message').inner_text());assert report(gui_workspace,final_export)==after['plan'] and tree(gui_workspace/exported['directory'])==old_report
                assert all(tree(gui_workspace/'inbox')[n]==v for n,v in input_bytes.items());assert json.loads(s['http']('/api/plan?project=sample-operations&revision=1'))==first['plan'];checks.append('actual_bundled_two_eight_file_reports_independent_hashes_no_mail_historical_result_and_original_inputs_preserved')
                tab('compare');page.locator('#right').fill('3');page.locator('#compare-run').click();expect(page.locator('#comparison')).to_contain_text('"completion_units_after": 33');expect(page.locator('#history-table tbody tr')).to_have_count(3);capture('analytics-history.jpg')
                history=after['history']['revisions'];assert history[1]['parent_sha256']==history[0]['revision_sha256'] and history[2]['parent_sha256']==history[1]['revision_sha256']
                page.locator('#backup').click();expect(page.locator('#message')).to_contain_text('.sqlite3');backup=json.loads(page.locator('#message').inner_text());raw=(gui_workspace/backup['file']).read_bytes();assert backup['sha256']==sha(raw) and backup['bytes']==len(raw)
                import sqlite3
                with closing(sqlite3.connect((gui_workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==3
                checks.append('actual_bundled_three_revision_parent_chain_comparison_and_database_backup_integrity')
                page.set_viewport_size(dict(width=390,height=844));tab('review');page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#status')).to_be_focused();assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_bundled_browser_layout_and_keyboard_navigation')
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            saved=tree(gui_workspace)
            with server() as s:
                page.goto(s['url']);expect(page.locator('#message')).to_have_text('Scenario loaded');assert view(s)==after and tree(gui_workspace)==saved and tree(gui_workspace/exported['directory'])==old_report
                expect(page.locator('#stats strong').first).to_have_text('33');page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            checks.append('actual_bundled_third_revision_reference_and_reports_reopen_without_reseed_or_replay_owned_shutdown_releases_lock')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close()
            browser_data=dict(planning_totals=[160,25,85,50],initial_completions=25,final_completions=33,completion_events=3,inserted_events=1,replay_inserted_events=0,replay_created_revision=False,revisions=3,private_report_files=8,capacity=201,oee=.5625,reorder_units=18,report_hashes_independently_verified=True,old_report_unchanged=True,original_inputs_unchanged=True,planning_does_not_map_eligibility_or_completions=True,stale_revision_refused=True,changed_event_identity_refused=True,tampered_report_refused=True,historical_result_unchanged=True,backup_integrity_checked=True,saved_revision_reopened=True,journal_bytes_unchanged_on_reopen=True,external_system_writes=False,production_execution_authorized=False,purchase_authorized=False,mail_sent=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=89,core_skips=1,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional Windows CMD/browser planning-reference handoff, independent scenario metrics, completion reconciliation and replay; no manufacturing, purchasing or mail authority, full restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
