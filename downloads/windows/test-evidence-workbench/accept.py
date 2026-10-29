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
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir();local_data=private/'app data';local_data.mkdir();before=tree(root);pwsh=shutil.which('pwsh');assert pwsh
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_LINKS':'1','LOCALAPPDATA':str(local_data),'PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Test Evidence Exercise.cmd' if exercise else 'Test Evidence Demo.cmd')),*map(str,args)])
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
    core=p.stderr.decode('utf-8');assert re.search(r'Ran 56 tests?',core)
    required=['test_native_hardlink_input_refused','test_native_database_hardlink_refused','test_native_symlink_input_refused','test_native_symlink_parent_refused','test_windows_stream_refused']
    skipped=re.findall(r'^(test_\w+) [^\n]*\.\.\. skipped ',core,re.M);assert skipped==['test_posix_fifo_refused_without_blocking']
    for name in required:assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_56_original_methods_on_bundled_python_5_required_native_windows_only_posix_fifo_skip')
    exercise_workspace=private/'new evidence exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==33
    checks.append('cmd_exercise_33_original_cli_calls_independent_pins_captures_verdicts_exports_and_reopen')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    saved=json.loads(cli(['--workspace',exercise_workspace,'--cli','artifacts']));assert len(saved['artifacts'])==2;checks.append('original_cli_reopens_saved_mixed_and_matching_artifacts')
    gui_workspace=local_data/'Outlands/TestEvidenceWorkbench/fictional-demo'
    @contextmanager
    def server():
        p=subprocess.Popen(command(['--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
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
            html=http('/').decode('utf-8');value['token']=re.search(r"\btoken='([A-Za-z0-9_-]{32,})'",html).group(1)
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
        tested=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=test_env,capture_output=True,timeout=600);(private/'original-browser-tests.log').write_bytes(tested.stdout+tested.stderr)
        assert tested.returncode==0 and re.search(r'Ran 16 tests?',tested.stderr.decode('utf-8')) and 'skipped=' not in tested.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=16;checks.append('all_16_original_chromium_methods_on_separate_python312_without_skips')
        sys.path.insert(0,str(root));from evidence_demo import fixtures,verify_artifact,verify_export,snapshot,encode
        fixture=fixtures(app)
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=20000)
        with sync_playwright() as pw:
            chromium=pw.chromium.launch(headless=True);context=chromium.new_context(viewport=dict(width=1360,height=1000));page=context.new_page();errors=[];requests=[]
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:requests.append(req.url))
            def capture(name,section):
                page.locator('main > section').nth(section).screenshot(path=str(packages/name),type='jpeg',quality=88);raw=(packages/name).read_bytes();captures[name]=dict(bytes=len(raw),sha256=sha(raw))
            def case(identifier):
                page.locator('#cases').select_option(identifier);expect(page.locator('#status')).to_have_text('Saved case loaded.');expect(page.locator('#case-id')).to_have_value(identifier);expect(page.locator('#cases')).to_be_enabled()
            def trust():
                for key in ('code_reviewed','authority','input_reviewed','effects_reviewed'):page.locator('#'+key).check()
                page.locator('#trust').click();expect(page.locator('#status')).to_have_text('Execution trust saved. No code ran.');expect(page.locator('#trust')).to_be_enabled()
            def plan(ids):
                page.locator('#suite-cases').select_option(ids);page.locator('#build-plan').click();expect(page.locator('#status')).to_have_text('Pinned plan prepared. Run is a separate action.');expect(page.locator('#run')).to_be_enabled();return json.loads(page.locator('#plan').input_value())
            def run():
                page.locator('#run').click();expect(page.locator('#status')).to_have_text('Evidence saved: completed. Review is pending.');expect(page.locator('#run')).to_be_enabled();return page.locator('#artifacts').input_value()
            def review(status='approved',checked=True):
                page.locator('#review-status').select_option(status);page.locator('#actor').fill('sample_reviewer');page.locator('#note').fill('Fictional failure evidence; verdicts unchanged')
                for key in ('quality','privacy','rights','context'):page.locator('#'+key).set_checked(checked)
                page.locator('#review').click();expect(page.locator('#status')).to_have_text('Evidence review saved. Check verdicts are unchanged.');expect(page.locator('#review')).to_be_enabled()
            def export():
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('Evidence exported inside the private workspace. Review before sharing.');return json.loads(page.locator('#receipt').inner_text())
            with server() as session:
                get=lambda path:json.loads(session['http'](path))
                page.goto(session['url']);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.');assert get('/api/cases')==dict(cases=[]) and not list((gui_workspace/'runs').iterdir())
                page.locator('#example').click();expect(page.locator('#status')).to_have_text('Fictional cases loaded into import draft. No code executed.');page.locator('#import').click();expect(page.locator('#status')).to_have_text('Cases imported. Execution trust is separate; no code ran.')
                assert len(get('/api/cases')['cases'])==4 and not list((gui_workspace/'runs').iterdir())
                page.locator('#suite-cases').select_option(['sample-total']);page.locator('#build-plan').click();expect(page.locator('#status')).to_have_text('EXECUTION_TRUST_REQUIRED');page.locator('#trust').click();expect(page.locator('#status')).to_have_text('TRUST_CHECKS_REQUIRED');assert not list((gui_workspace/'runs').iterdir())
                checks.append('actual_bundled_default_windows_workspace_empty_start_import_untrusted_plan_and_missing_trust_assertions_execute_nothing')
                for identifier in fixture['definitions']:case(identifier);trust()
                prepared=plan(list(fixture['definitions']));assert prepared==dict(cases=[dict(case_id=n,expected_sha256=fixture['pins'][n],trust_version=1) for n in sorted(fixture['definitions'])]);assert not list((gui_workspace/'runs').iterdir())
                capture('evidence-trust.jpg',2);checks.append('actual_bundled_four_explicit_revision_trusts_and_complete_pinned_plan_without_execution')
                first_id=run();first=get('/api/artifact?id='+first_id);verify_artifact(first,fixture,fixture['definitions']);assert [first['payload']['result'][k] for k in ('planned','attempted','matched','unmatched')]==[4,4,2,2]
                page.locator('#result-cases').select_option('sample-mismatch');expect(page.locator('#case-result')).to_contain_text('"total": 8');capture('evidence-results.jpg',4);checks.append('actual_bundled_four_owned_checks_two_matches_mismatch_timeout_independent_stream_verdicts_and_hashes')
                page.locator('#review-status').select_option('approved');page.locator('#review').click();expect(page.locator('#status')).to_have_text('REVIEW_CHECKS_REQUIRED');review();first=get('/api/artifact?id='+first_id);assert first['review']['status']=='approved' and first['payload']['result']['unmatched']==2
                exported=export();old_export=verify_export(gui_workspace,exported,first,fixture);old_artifact=encode(first['payload']);inputs=tree(gui_workspace/'inbox');capture('evidence-export.jpg',6);checks.append('actual_bundled_failure_evidence_review_preserves_verdicts_and_independently_verified_13_file_private_export')
                plan(['sample-total','sample-nonzero']);second_id=run();second=get('/api/artifact?id='+second_id);verify_artifact(second,fixture,('sample-total','sample-nonzero'));assert second_id!=first_id and second['review']==dict(status='pending',row_version=0)
                expect(page.locator('#review-status')).to_have_value('pending')
                for key in ('quality','privacy','rights','context'):expect(page.locator('#'+key)).not_to_be_checked()
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('APPROVAL_REQUIRED');capture('evidence-pending.jpg',5)
                page.locator('#left').select_option(first_id);page.locator('#right').select_option(second_id);page.locator('#compare').click();expect(page.locator('#status')).to_have_text('Pinned evidence compared; source differences remain explicit.');comparison=json.loads(page.locator('#comparison').inner_text());assert not comparison['same_case_set'] and comparison['both_complete']
                checks.append('actual_bundled_new_matching_run_has_pending_review_export_refused_and_pinned_comparison_keeps_case_sets_explicit')
                case('sample-total');prepared=plan(['sample-total']);page.locator('#title').fill('Fictional revised total check');page.locator('#run').click();expect(page.locator('#status')).to_have_text('CASE_DRAFT_UNSAVED');page.locator('#trust').click();expect(page.locator('#status')).to_have_text('CASE_DRAFT_UNSAVED');page.locator('#save-case').click();expect(page.locator('#status')).to_have_text('Immutable case saved. New revisions require execution trust.');before_dirs=tree(gui_workspace/'runs');page.locator('#run').click();expect(page.locator('#status')).to_have_text('CASE_REVISION_CONFLICT');assert tree(gui_workspace/'runs')==before_dirs
                current=get('/api/case?id=sample-total');assert current['version']==2 and current['trust']==dict(status='pending',row_version=0);checks.append('actual_bundled_dirty_draft_blocks_trust_run_new_revision_needs_trust_and_stale_plan_refuses_before_children')
                page.locator('#artifacts').select_option(first_id);expect(page.locator('#status')).to_have_text('Evidence and its review loaded.');review('pending',False);page.locator('#export').click();expect(page.locator('#status')).to_have_text('APPROVAL_REQUIRED');review();again=export();assert again['directory']!=exported['directory'];verify_export(gui_workspace,again,get('/api/artifact?id='+first_id),fixture)
                assert tree(gui_workspace/exported['directory'])==old_export and get('/api/artifact?id='+first_id)['payload']==first['payload'] and tree(gui_workspace/'inbox')==inputs
                checks.append('actual_bundled_review_revocation_blocks_future_export_and_preserves_old_payload_reports_and_original_input')
                page.locator('#backup').click();expect(page.locator('#status')).to_have_text('Private database backup created and schema verified.');backup=json.loads(page.locator('#receipt').inner_text());assert sha((gui_workspace/backup['file']).read_bytes())==backup['sha256'] and snapshot(gui_workspace/backup['file'])==snapshot(gui_workspace/'database/workbench.sqlite3')
                page.set_viewport_size(dict(width=390,height=844));assert page.evaluate('document.documentElement.scrollWidth')<=390;page.locator('#cases').focus();assert page.evaluate('document.activeElement.id')=='cases';checks.append('actual_bundled_database_backup_integrity_logical_rows_and_390px_keyboard_layout')
                page.locator('#shutdown').click();session['shutdown_requested']=True;expect(page.locator('#status')).to_have_text('Local server stopping.')
            saved_tree=tree(gui_workspace)
            with server() as session:
                page.set_viewport_size(dict(width=1360,height=1000));page.goto(session['url']);expect(page.locator('#status')).to_have_text('Ready. Private workspace loaded.');assert len(json.loads(session['http']('/api/cases'))['cases'])==4 and len(json.loads(session['http']('/api/artifacts'))['artifacts'])==2 and tree(gui_workspace)==saved_tree
                assert encode(json.loads(session['http']('/api/artifact?id='+first_id))['payload'])==old_artifact;page.locator('#shutdown').click();session['shutdown_requested']=True;expect(page.locator('#status')).to_have_text('Local server stopping.')
            checks.append('actual_bundled_saved_revisions_trust_artifacts_review_reopen_without_execution_or_reseed')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close();chromium.close()
            browser_data=dict(cases=4,case_revisions=5,planned=4,attempted=4,matched=2,unmatched=2,timeouts=1,expected_nonzero_matched=True,artifacts=2,owned_children_started=6,export_files=13,export_data_files=12,independent_case_artifact_script_input_hashes=True,independent_raw_capture_verdicts=True,independent_export_members_and_hashes=True,untrusted_plan_refused_without_children=True,missing_trust_checks_refused=True,missing_review_checks_refused=True,fresh_run_review_pending=True,pending_export_refused=True,review_revocation_blocks_future_export=True,new_case_revision_requires_trust=True,stale_plan_refused_without_children=True,old_artifact_payload_unchanged=True,old_exports_unchanged=True,original_inputs_unchanged=True,backup_integrity_and_logical_rows=True,saved_records_reopened=True,journal_unchanged_on_reopen=True,dirty_draft_blocks_execution=True,execution_sandbox=False,descendant_containment=False,original_operational_checks_executed=False,external_services_used=False,publication_authorized=False,complete_restore_performed=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',default_windows_workspace_qualified=True,core_tests=56,core_skips=len(skipped),core_skip_methods=skipped,required_windows_methods=5,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Explicit trusted fictional Python execution, pinned plans, independent captured verdicts, private reviewed exports and state backup/reopen; no execution sandbox, descendant containment, operational check, external service, publication approval, complete restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
