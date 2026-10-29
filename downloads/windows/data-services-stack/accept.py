"""Fresh Windows CMD, preserved source and real bundled-runtime Chromium acceptance."""
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
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','STACK_REQUIRE_LINKS':'1','PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Data Services Exercise.cmd' if exercise else 'Data Services Demo.cmd')),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,exercise=False,expected=0):
        p=subprocess.run(command(args,exercise),cwd=private,env=env,capture_output=True,timeout=180);(private/'last-cli.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==expected,'CMD check failed; private log retained.'
        return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime'];assert tree(root)==before
    checks.append('cmd_uses_isolated_bundled_runtime_without_system_python_or_state')
    source=json.loads(cli(['--cli','source-check']));assert source['status']=='PASS';checks.append('original_source_inventory_preserved')
    p=subprocess.run([python,'-I','-B','-W','error',str(app/'run_checks.py')],cwd=app,env=env,capture_output=True,timeout=300);(private/'core-tests.log').write_bytes(p.stdout+p.stderr)
    assert p.returncode==0,'Bundled core checks failed; private log retained.'
    assert re.search(r'Ran 101 tests?',p.stderr.decode('utf-8')) and 'skipped=1' in p.stderr.decode('utf-8')
    checks.append('all_101_original_core_methods_on_bundled_python_five_required_native_boundaries_one_opposite_platform_skip')
    exercise_workspace=private/'new data exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==22
    assert [outcome[k] for k in ('input_records','holdout_predictions','mae','rmse','retry_attempts','accepted_attempts','unknown_attempts')]==[6,3,4,4,1,2,1] and outcome['predictions']==[10,10,10] and outcome['future_replay_calls']==0
    checks.append('cmd_exercise_22_original_cli_calls_independent_numeric_export_and_preservation_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    overview=json.loads(cli(['--workspace',exercise_workspace/'journal','--cli','status']));assert not overview['recovery_required'] and len(overview['runs'])==3
    assert [r['state'] for r in overview['queue']]==['DELIVERY_REPORTED','REVIEW_REQUIRED'] and [r['attempts'] for r in overview['queue']]==[2,1]
    checks.append('original_cli_reopens_saved_results_and_held_uncertain_queue_without_replay')
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
            html=http('/').decode('utf-8');value['token']=re.search(r"const token='([^']+)'",html).group(1);assert value['reports'].is_dir()
            yield value
        finally:
            try:
                if p.poll() is None and value.get('token') and not value.get('shutdown_requested'):http('/api/shutdown',dict(expected_head=None))
                if p.poll() is None:assert p.wait(timeout=10)==0
            finally:
                if p.poll() is None:subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True);p.wait(timeout=10)
                worker.join(timeout=5);p.stdout.close();log.close()
    captures={};browser_data={};original_browser_tests=0
    if browser:
        # These original browser methods run on the separate test interpreter.
        # The custom workflow below drives the actual bundled Python server.
        test_env={**os.environ,'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1'};test_env.pop('OUTLANDS_BROWSER_EVIDENCE',None)
        p=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=test_env,capture_output=True,timeout=300);(private/'original-browser-tests.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0 and re.search(r'Ran 25 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=25;checks.append('all_25_original_browser_methods_on_separate_test_python_without_skips')
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual Windows Chromium and bundled Python; invented data, baseline results and fake transport only; no address bar, absolute path or session token')
            def state(s):return json.loads(s['http']('/api/overview',{}))['result']
            def inspect(s,key):return json.loads(s['http']('/api/inspect',dict(key=key)))['result']
            def job_example(csv=False):
                page.locator('[data-tab=jobs]').click();page.locator('#example-config').click();expect(page.locator('#status')).to_contain_text('Invented configuration loaded.')
                if csv:
                    config=json.loads(page.locator('#configuration').input_value());config['jobs'][0]['input_format']='csv';page.locator('#configuration').fill(json.dumps(config))
                page.locator('#configure').click();expect(page.locator('#status')).to_contain_text('Configuration saved.')
            def preview(csv=False):
                page.locator('#sample-csv' if csv else '#sample-jsonl').click();page.locator('#preview').click();expect(page.locator('#status')).to_have_text('Preview clean and pinned. No run or notification created.')
            def run(key):
                page.locator('#run-key').fill(key);page.locator('#run').click();expect(page.locator('#status')).to_have_text('Run saved. One durable notification is queued; no transport was called.')
            def dispatch(outcome,tick):
                page.locator('#outcome').select_option(outcome);page.locator('#tick').fill(str(tick));page.locator('#dispatch').click();expect(page.locator('#status')).to_have_text('Fictional dispatch recorded. Adapter acceptance is not verified delivery.')
                return json.loads(page.locator('#dispatch-result').inner_text())
            with server() as s:
                first_reports=s['reports'];page.goto(s['url']);expect(page.locator('#status')).to_have_text('Private journal ready. Nothing configured or dispatched automatically.')
                initial=state(s);assert not initial['runs'] and not initial['jobs'] and not initial['queue'];checks.append('actual_bundled_browser_starts_empty_without_configuration_or_dispatch')
                job_example();head=state(s)['head_sha256'];preview();assert len(page.locator('#preview-records tr').all())==6 and state(s)['head_sha256']==head
                capture('data-preview.jpg');page.locator('#content').fill('null');page.locator('#preview').click();expect(page.locator('#status')).to_have_text('Preview blocked. Correct the input or configuration.');expect(page.locator('#run')).to_be_disabled();assert state(s)['head_sha256']==head
                preview();checks.append('actual_bundled_jsonl_preview_is_nonmutating_and_invalid_input_blocks_run')
                run('sample_run');original=inspect(s,'sample_run');result=original['run']['result'];assert result['accepted']==6 and result['duplicates']==0 and result['score']==dict(count=3,mae=4,rmse=4)
                assert result['forecast']==[dict(series='sample',period=i,value=10) for i in (6,7,8)];expect(page.locator('#metrics')).to_have_text('Accepted 6 · duplicates 0 · holdout predictions 3 · MAE 4 · RMSE 4')
                assert page.locator('#forecast-points tr').count()==3 and page.locator('#chart circle').count()==3;checks.append('actual_bundled_saved_forecast_and_holdout_metrics_match_independent_expectations')
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('REVIEW_REQUIRED');assert not list(first_reports.iterdir())
                page.locator('#note').fill('Invented independent review of baseline limits')
                for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                page.locator('#export').click();expect(page.locator('#status')).to_contain_text('Checked private report created: ');report=json.loads(page.locator('#report-result').inner_text());folder=first_reports/report['directory'];handed_off=tree(folder)
                assert set(handed_off)=={'run.json','review.json','manifest.json'}
                assert not report['manifest']['public_release_authorized'] and not report['manifest']['real_delivery_verified'] and not report['manifest']['source_input_included']
                for name,row in report['manifest']['files'].items():
                    b=(folder/name).read_bytes();assert row==dict(bytes=len(b),sha256=sha(b))
                assert json.loads((folder/'run.json').read_bytes())==original['run'];capture('data-result.jpg');checks.append('actual_bundled_private_report_requires_review_and_all_three_files_are_independently_verified')
                page.locator('[data-tab=queue]').click();retried=dispatch('retry',0);assert retried['fake_calls']==1 and retried['queue']==[dict(key='sample_run',state='PENDING',code='RETRY_SCHEDULED',attempts=1,next_attempt=1)]
                not_due=dispatch('accept',0);assert not_due['fake_calls']==0 and not_due['queue']==[] and state(s)['queue'][0]['attempts']==1;capture('data-retry.jpg')
                accepted=dispatch('accept',1);assert accepted['fake_calls']==1 and accepted['queue'][0]['state']=='ACCEPTED' and accepted['queue'][0]['attempts']==2;checks.append('actual_bundled_fake_retry_is_not_attempted_before_due_tick_and_acceptance_stays_unverified')
                page.locator('#delivery').click();expect(page.locator('#status')).to_have_text('DELIVERY_ASSERTION_REQUIRED');page.locator('#delivery-assertion').check();page.locator('#receipt').fill('wrong_receipt');page.locator('#delivery').click();expect(page.locator('#status')).to_have_text('DELIVERY_REPORT_REFUSED')
                page.locator('#receipt').fill('fake_receipt');page.locator('#delivery').click();expect(page.locator('#status')).to_have_text('Caller assertion recorded. Real delivery remains unverified.');assert state(s)['queue'][0]['state']=='DELIVERY_REPORTED';checks.append('caller_delivery_assertion_requires_matching_receipt_and_does_not_establish_delivery')
                job_example(csv=True);preview(csv=True);run('uncertain_run');assert inspect(s,'uncertain_run')['run']['job']['input_format']=='csv' and inspect(s,'sample_run')['run']==original['run'];checks.append('actual_bundled_csv_run_keeps_the_original_jsonl_job_snapshot_and_result_unchanged')
                page.locator('[data-tab=queue]').click();held=dispatch('accepted_then_unknown',2);assert held['fake_calls']==1 and held['queue'][0]['state']=='REVIEW_REQUIRED' and held['queue'][0]['attempts']==1
                later=dispatch('accept',100);assert later['fake_calls']==0 and later['queue']==[];page.locator('#delivery-key').select_option('uncertain_run');page.locator('#delivery-assertion').check();page.locator('#delivery').click();expect(page.locator('#status')).to_have_text('DELIVERY_REPORT_REFUSED');capture('data-held.jpg');saved=state(s)
                assert saved['queue'][1]['state']=='REVIEW_REQUIRED' and saved['queue'][1]['attempts']==1;checks.append('actual_bundled_unknown_outcome_is_held_and_cannot_be_replayed_or_promoted_by_assertion')
                page.set_viewport_size(dict(width=390,height=844));page.locator('[data-tab=runs]').click();page.locator('[data-run=sample_run]').click();page.locator('#actor').focus();page.keyboard.press('Tab');expect(page.locator('#note')).to_be_focused();assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_bundled_browser_layout_and_keyboard_navigation')
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local UI stopped.')
            journal_before=tree(gui_workspace)
            with server() as s:
                assert s['reports']!=first_reports and not list(s['reports'].iterdir())
                reopened=state(s);assert reopened==saved and tree(gui_workspace)==journal_before and tree(folder)==handed_off
                assert inspect(s,'sample_run')['run']==original['run']
                page.goto(s['url']);page.locator('[data-tab=runs]').click();page.locator('[data-run=sample_run]').click();expect(page.locator('#metrics')).to_contain_text('MAE 4');page.locator('[data-tab=queue]').click();expect(page.locator('#queue-rows')).to_contain_text('REVIEW_REQUIRED')
                assert dispatch('accept',100)['fake_calls']==0 and tree(gui_workspace)==journal_before and tree(folder)==handed_off
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local UI stopped.')
            checks.append('actual_bundled_journal_reopens_exact_results_and_held_attempts_without_replay_prior_reports_retained_fresh_report_root_and_owned_shutdown')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close()
            browser_data=dict(input_records=6,predictions=[10,10,10],holdout_predictions=3,mae=4,rmse=4,private_report_files=3,report_hashes_independently_verified=True,missing_review_refused=True,jsonl_and_csv_runs=True,historical_result_unchanged=True,retry_attempts=1,retry_due_tick=1,not_due_fake_calls=0,accepted_attempts=2,unknown_attempts=1,unknown_state='REVIEW_REQUIRED',future_replay_calls=0,uncertain_delivery_assertion_refused=True,journal_bytes_unchanged_on_reopen=True,previous_reports_retained=True,fresh_report_roots=True,saved_results_reopened=True,real_delivery_verified=False,real_forecast_usefulness_measured=False,automatic_dispatch=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=101,core_skips=1,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional Windows CMD/browser data jobs, baseline metrics, private reports and fake notification transitions; real forecast usefulness, provider delivery, full restore and separate-PC acceptance remain unverified')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
