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
        line=subprocess.list2cmdline([str(root/('ML Exercise.cmd' if exercise else 'ML Demo.cmd')),*map(str,args)])
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
    assert re.search(r'Ran 67 tests?',p.stderr.decode('utf-8')) and 'skipped=1' in p.stderr.decode('utf-8')
    core=p.stderr.decode('utf-8')
    for name in ('test_native_hardlink_input_refused','test_native_database_hardlink_refused','test_native_symlink_input_refused','test_native_symlink_parent_refused','test_windows_stream_refused'):
        assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_67_original_core_methods_on_bundled_python_five_required_native_boundaries_one_opposite_platform_skip')
    exercise_workspace=private/'new data exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==29
    assert [outcome[k] for k in ('rows','training_rows','validation_rows','test_rows','excluded_rows','private_report_files')]==[240,118,48,48,26,8]
    checks.append('cmd_exercise_29_original_cli_calls_independent_preprocessing_predictions_metrics_report_and_backup_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    snapshot=json.loads(cli(['--workspace',exercise_workspace,'--cli','list']));assert len(snapshot['experiments'])==2
    checks.append('original_cli_reopens_two_saved_experiments')
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
        assert p.returncode==0 and re.search(r'Ran 10 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=10;checks.append('all_ten_original_ml_browser_methods_on_separate_test_python_without_skips')
        sys.path.insert(0,str(app))
        from playwright.sync_api import sync_playwright,expect
        from ml_demo import numerical,verify_report
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual hosted Windows Chromium and bundled Python; invented tabular records only; no address bar, machine path or token')
            def record(s,name='sample-baseline'):return json.loads(s['http']('/api/experiment?experiment='+name))
            def approve():
                page.locator('#review-status').select_option('approved')
                for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                page.locator('#review-form button').click();expect(page.locator('#status')).to_have_text('Review recorded for this saved artifact.')
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_have_text('Ready. Import a fictional dataset to start.');assert len(json.loads(s['http']('/api/datasets'))['datasets'])==1 and json.loads(s['http']('/api/experiments'))==dict(experiments=[])
                data=json.loads(s['http']('/api/dataset?dataset=sample-ml'))['dataset'];inputs=tree(gui_workspace/'inbox');page.locator('#template').click();expect(page.locator('#status')).to_contain_text('Pinned template loaded.')
                page.locator('#train-end').fill('140');draft=page.locator('#configuration-json').input_value();page.locator('#prepare').click();expect(page.locator('#status')).to_have_text('CHRONOLOGY_INVALID; drafts retained.');assert page.locator('#configuration-json').input_value()==draft;page.locator('#train-end').fill('120')
                page.locator('#prepare').click();expect(page.locator('#status')).to_have_text('Experiment prepared. Holdout evaluation remains a separate step.');prepared=record(s);assert prepared['evaluation'] is None;numerical(prepared,data)
                assert page.locator('#weights tbody tr').count()==3 and page.locator('#threshold-chart circle').count()==5;capture('ml-prepared.jpg');checks.append('actual_bundled_training_only_preprocessing_validation_threshold_and_no_preparation_test_metrics')
                approve();page.locator('#export').click();expect(page.locator('#status')).to_have_text('EVALUATION_REQUIRED_FOR_EXPORT; drafts retained.')
                page.locator('#evaluate').click();expect(page.locator('#status')).to_have_text('Holdout evaluation recorded. Review is pending for this artifact.');evaluated=record(s);assert evaluated['review']==dict(status='pending',row_version=0) and page.locator('#review-status').input_value()=='pending';numerical(evaluated,data);capture('ml-evaluated.jpg')
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('APPROVAL_REQUIRED; drafts retained.');page.locator('#review-status').select_option('approved');page.locator('#review-form button').click();expect(page.locator('#status')).to_have_text('REVIEW_CHECKS_REQUIRED; drafts retained.')
                approve();saved_baseline=record(s);page.locator('#export').click();expect(page.locator('#status')).to_have_text('Approved artifact exported inside the private workspace.');summary=json.loads(page.locator('#report-output').inner_text());assert summary['files']==8
                report=dict(directory=summary['directory'],manifest=json.loads((gui_workspace/summary['directory']/'manifest.json').read_bytes()));verify_report(gui_workspace,report,saved_baseline,data);old_report=tree(gui_workspace/report['directory']);capture('ml-reviewed.jpg')
                before_refusal=tree(gui_workspace);stale=dict(experiment_id='sample-baseline',artifact_sha256=evaluated['artifact_sha256'],expected_version=0,status='approved',actor='sample_reviewer',note='Fictional stale check',checks=dict(quality=True,privacy=True,rights=True,context=True));assert json.loads(s['http']('/api/review',stale,400))==dict(error='REVIEW_VERSION_CONFLICT') and tree(gui_workspace)==before_refusal
                checks.append('actual_bundled_separate_evaluation_resets_review_missing_stale_approval_refused_and_eight_file_export_independently_checked')
                page.locator('#l2').fill('0.2');draft=page.locator('#configuration-json').input_value();page.locator('#prepare').click();expect(page.locator('#status')).to_have_text('EXPERIMENT_IMMUTABLE; drafts retained.');assert page.locator('#configuration-json').input_value()==draft
                page.locator('#experiment-id').fill('sample-comparison');page.locator('#prepare').click();expect(page.locator('#status')).to_have_text('Experiment prepared. Holdout evaluation remains a separate step.')
                page.locator('#left').select_option('sample-baseline');page.locator('#right').select_option('sample-comparison');page.locator('#compare').click();expect(page.locator('#status')).to_have_text('Comparison calculated with explicit cohort checks.');assert not json.loads(page.locator('#comparison').inner_text())['test_comparison_available']
                page.locator('#evaluate').click();expect(page.locator('#status')).to_have_text('Holdout evaluation recorded. Review is pending for this artifact.');page.locator('#compare').click();expect(page.locator('#status')).to_have_text('Comparison calculated with explicit cohort checks.');comparison=json.loads(page.locator('#comparison').inner_text());assert comparison['same_test_cohort'] and comparison['test_comparison_available'];capture('ml-comparison.jpg')
                checks.append('actual_bundled_immutable_configuration_conflict_retains_draft_and_comparison_waits_for_identical_evaluated_cohorts')
                assert tree(gui_workspace/'inbox')==inputs and tree(gui_workspace/report['directory'])==old_report
                page.locator('#backup').click();expect(page.locator('#status')).to_have_text('Private database backup created.');backup=json.loads(page.locator('#report-output').inner_text());assert sha((gui_workspace/backup['file']).read_bytes())==backup['sha256']
                import sqlite3
                with closing(sqlite3.connect((gui_workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
                checks.append('actual_bundled_original_inputs_old_report_and_database_backup_preserved')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#experiment-id').focus();page.keyboard.press('Tab');expect(page.locator('#train-end')).to_be_focused();assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_bundled_form_layout_and_keyboard_navigation')
                saved_comparison=record(s,'sample-comparison');page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping.')
            saved=tree(gui_workspace)
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_have_text('Saved experiment loaded.');assert record(s)==saved_baseline and record(s,'sample-comparison')==saved_comparison and tree(gui_workspace)==saved
                page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping.')
            checks.append('actual_bundled_experiments_evaluations_and_artifact_review_reopen_without_retraining_or_reseed_owned_shutdown_releases_lock')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close()
            m=saved_baseline['evaluation']['result']['metrics'];browser_data=dict(rows=240,training_rows=118,validation_rows=48,test_rows=48,excluded_rows=26,experiments=2,threshold=.4,test_auc=m['roc_auc'],test_brier=m['brier'],private_report_files=8,train_only_preprocessing_independently_checked=True,model_predictions_independently_replayed=True,metrics_independently_recomputed=True,validation_threshold_independently_checked=True,prepared_without_test_metrics=True,evaluation_resets_review=True,missing_review_checks_refused=True,stale_review_refused=True,invalid_chronology_refused=True,immutable_conflict_refused=True,same_test_cohort=True,comparison_waits_for_evaluations=True,report_hashes_independently_verified=True,old_report_unchanged=True,original_inputs_unchanged=True,backup_integrity_checked=True,saved_experiment_reopened=True,journal_bytes_unchanged_on_reopen=True,real_world_accuracy_established=False,scores_calibrated=False,pretrained_weights_included=False,complete_restore_performed=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=67,core_skips=1,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional tabular Windows CMD/browser baseline training, independent preprocessing/model/metrics replay, separate evaluation and artifact review, exports and reopen; no real-world accuracy, calibration, full restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
