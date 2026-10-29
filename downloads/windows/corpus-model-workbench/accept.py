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
        line=subprocess.list2cmdline([str(root/('Corpus Model Exercise.cmd' if exercise else 'Corpus Model Demo.cmd')),*map(str,args)])
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
    core=p.stderr.decode('utf-8');assert re.search(r'Ran 82 tests?',core)
    required=['test_native_junction_or_directory_link_export_parent_refused','test_native_workspace_metadata_hardlink_refused','test_native_hardlink_input_refused','test_native_symlink_input_refused','test_native_directory_link_refused','test_native_database_hardlink_refused','test_windows_stream_name_refused']
    skipped=re.findall(r'^(test_\w+) [^\n]*\.\.\. skipped ',core,re.M);assert skipped==['test_posix_fifo_refused_without_blocking']
    for name in required:assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    assert health['sqlite_fts5'];checks.append('all_82_original_methods_bundled_7_required_native_windows_only_posix_fifo_skip_fts5_available')
    exercise_workspace=private/'new corpus exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==21
    checks.append('cmd_exercise_21_original_cli_calls_independent_records_exports_provenance_backup_and_reopen')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    reopened=json.loads(cli(['--workspace',exercise_workspace,'--cli','status']));assert reopened['records']==5 and reopened['status']==dict(approved=4,pending=1);checks.append('original_cli_reopens_saved_records_and_pending_candidate')
    gui_workspace=private/'browser corpus practice'
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
        tested=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=test_env,capture_output=True,timeout=600);(private/'original-browser-tests.log').write_bytes(tested.stdout+tested.stderr)
        assert tested.returncode==0 and re.search(r'Ran 22 tests?',tested.stderr.decode('utf-8')) and 'skipped=' not in tested.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=22;checks.append('all_22_original_chromium_methods_on_separate_python312_without_skips')
        sys.path.insert(0,str(root));from corpus_demo import fixture,verify_exports,snapshot
        f=fixture(app)
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=20000)
        with sync_playwright() as pw:
            chromium=pw.chromium.launch(headless=True);context=chromium.new_context(viewport=dict(width=1280,height=1024));page=context.new_page();errors=[];requests=[]
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:requests.append(req.url))
            def capture(name):
                page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=False);raw=(packages/name).read_bytes();captures[name]=dict(bytes=len(raw),sha256=sha(raw))
            def select(title):
                page.locator('#records .record').filter(has_text=title).click();expect(page.locator('#message')).to_have_text('Ready');expect(page.locator('#detail h2')).to_have_text(title)
            def review(decision='approved',checked=True):
                page.locator('#actor').fill('sample_reviewer');page.locator('#review-note').fill('Fictional review assertion only')
                for key in ('quality','privacy','rights','context'):page.locator('#check-'+key).set_checked(checked)
                page.locator('[data-decision='+decision+']').click();expect(page.locator('#message')).to_have_text('Review saved')
            def exported(kind):
                previous=page.locator('#message').inner_text();page.locator('[data-export='+kind+']').click();expect(page.locator('#message')).not_to_have_text(previous);expect(page.locator('#message')).to_contain_text('Export saved: ')
                return gui_workspace/page.locator('#message').inner_text().splitlines()[0].removeprefix('Export saved: ')
            with server() as session:
                page.goto(session['url']);expect(page.locator('#count')).to_contain_text('0 matching records');expect(page.get_by_text('FICTIONAL MODEL DEMONSTRATION',exact=False)).to_be_visible()
                assert not list((gui_workspace/'exports').iterdir());initial=json.loads(session['http']('/api/status'));assert initial['records']==0
                checks.append('actual_bundled_fictional_mode_starts_empty_without_import_approval_or_model_request')
                page.locator('#load-benchmarks').click();expect(page.locator('#message')).to_have_text('Benchmarks loaded; matching examples held out.');page.locator('#import-jsonl').click();expect(page.locator('#message')).to_have_text('Import complete; records require review.')
                state=json.loads(session['http']('/api/status'));assert state['records']==4 and state['provenance_links']==5 and state['split']==dict(train=2,test=2) and state['status']==dict(pending=4)
                capture('corpus-imported.jpg');checks.append('actual_bundled_explicit_five_to_four_import_five_source_receipts_and_benchmark_holdouts')
                select('Fictional training example');page.locator('#actor').fill('sample_reviewer');page.locator('#review-note').fill('Keep fictional draft');page.locator('[data-decision=approved]').click();expect(page.locator('#message')).to_have_text('OPERATION_FAILED');expect(page.locator('#review-note')).to_have_value('Keep fictional draft');assert json.loads(session['http']('/api/status'))['status']==dict(pending=4)
                page.locator('#context').click();expect(page.locator('#context-data')).to_contain_text('complete_supplied_messages')
                page.locator('#status').select_option('');page.locator('#search').click();expect(page.locator('#message')).to_have_text('Ready');expect(page.locator('#count')).to_contain_text('4 matching records')
                for title in ('Fictional training example','Fictional heldout match','Fictional Python reference','Fictional heldout document'):
                    select(title);review()
                    for key in ('quality','privacy','rights','context'):expect(page.locator('#check-'+key)).not_to_be_checked()
                checks.append('actual_bundled_missing_review_checks_refused_draft_retained_and_four_explicit_current_reviews')
                sft=exported('sft');rag=exported('rag');verify_exports(gui_workspace,f);old_exports=tree(gui_workspace/'exports');inputs=tree(gui_workspace/'inbox')
                page.reload();expect(page.locator('#count')).to_contain_text('0 matching records');page.locator('#status').select_option('');page.locator('#search').click();expect(page.locator('#message')).to_have_text('Ready');expect(page.locator('#count')).to_contain_text('4 matching records');capture('corpus-exports.jpg')
                checks.append('actual_bundled_exact_five_file_sft_and_two_file_train_document_rag_exports_independent_bytes_hashes')
                page.locator('[data-tab=models]').click();expect(page.locator('#message')).to_have_text('Ready');page.locator('#discover').click();expect(page.locator('#message')).to_have_text('Completed');expect(page.locator('#model-choices')).to_contain_text('fictional-model-a')
                for choice in page.locator('input[name=model]').all():choice.check()
                page.locator('#benchmark-limit').fill('3');page.locator('#benchmark').click();expect(page.locator('#message')).to_have_text('Responses saved. Review outputs and score against the rubrics.')
                assert page.locator('#runs details').count()==6
                for number in range(3):
                    details=page.locator('#runs details').filter(has_text='fictional-model-a').nth(number);details.locator('summary').click();details.locator('input[placeholder="0-5"]').fill('3');details.locator('input[placeholder=Reviewer]').fill('sample_reviewer');details.locator('input[placeholder="Evidence note"]').fill('Invented rubric score, not measured model quality');details.locator('[data-score]').click();expect(page.locator('#message')).to_have_text('Score saved')
                capture('corpus-models.jpg')
                page.locator('#embed').click();expect(page.locator('#message')).to_have_text('Vectors saved: 1');page.locator('#semantic-search').click();expect(page.locator('#semantic-results')).to_contain_text('Fictional Python reference')
                checks.append('actual_bundled_six_simulated_responses_three_invented_scores_and_one_fake_vector_search')
                page.locator('[data-tab=council]').click();page.locator('#task').fill('Explain a fictional Python function.');page.locator('#rounds').select_option('1');page.locator('#discuss').click();expect(page.locator('#conversation')).to_contain_text('Final answer');page.locator('[data-queue]').click();expect(page.locator('#message')).to_have_text('Answer added as a pending training candidate');page.locator('[data-queue]').click();expect(page.locator('#message')).to_have_text('Answer added as a pending training candidate')
                state=json.loads(session['http']('/api/status'));assert state['records']==5 and state['status']==dict(approved=4,pending=1)
                with closing(__import__('sqlite3').connect(gui_workspace/'database/corpus.sqlite3')) as con:assert con.execute('SELECT COUNT(*) FROM discussion_turns').fetchone()[0]==4 and con.execute('SELECT COUNT(*) FROM benchmark_runs WHERE score=3').fetchone()[0]==3
                checks.append('actual_bundled_four_turn_fictional_discussion_idempotently_queues_one_pending_answer_without_execution')
                page.locator('[data-tab=corpus]').click();page.locator('#status').select_option('');page.locator('#search').click();expect(page.locator('#message')).to_have_text('Ready');expect(page.locator('#count')).to_contain_text('5 matching records');select('Fictional training example');review('pending',False);revoked=exported('sft');assert (revoked/'train.jsonl').read_bytes()==b'';review();exported('sft')
                assert all(tree(gui_workspace/'exports')[n]==h for n,h in old_exports.items())
                with closing(__import__('sqlite3').connect(gui_workspace/'database/corpus.sqlite3')) as con:discussion_id=con.execute('SELECT id FROM discussions').fetchone()[0]
                current_inputs=tree(gui_workspace/'inbox');generated_name='discussion_'+discussion_id+'.jsonl'
                assert set(current_inputs)==set(inputs)|{generated_name} and all(current_inputs[n]==h for n,h in inputs.items())
                generated=json.loads((gui_workspace/'inbox'/generated_name).read_bytes());assert generated['group_id']=='discussion:'+discussion_id and generated['flags']==['model_generated','model_review_only'] and generated['messages']==[dict(role='user',content='Explain a fictional Python function.'),dict(role='assistant',content='Fictional model response. No code or real inference was executed.')]
                checks.append('actual_bundled_revocation_blocks_new_training_export_and_preserves_earlier_outputs_and_inputs')
                page.locator('#backup').click();expect(page.locator('#message')).to_contain_text('Backup saved: ');backup=gui_workspace/page.locator('#message').inner_text().removeprefix('Backup saved: ');assert snapshot(backup)==snapshot(gui_workspace/'database/corpus.sqlite3')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#query').fill('docstring');page.locator('#query').press('Enter');expect(page.locator('#count')).to_contain_text('1 matching records');assert page.locator('#message').evaluate('(node)=>getComputedStyle(node).overflowWrap')=='anywhere';assert page.evaluate('document.documentElement.scrollWidth')<=390;page.locator('#query').focus();assert page.evaluate('document.activeElement.id')=='query'
                checks.append('actual_bundled_database_backup_integrity_logical_rows_and_narrow_keyboard_search')
                page.locator('#stop-ui').click();session['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            saved=tree(gui_workspace)
            with server() as session:
                page.set_viewport_size(dict(width=1280,height=1024));page.goto(session['url']);expect(page.locator('#count')).to_contain_text('1 matching records');assert json.loads(session['http']('/api/status'))['status']==dict(approved=4,pending=1) and tree(gui_workspace)==saved
                capture('corpus-reopened.jpg');page.locator('#stop-ui').click();session['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            checks.append('actual_bundled_saved_records_reviews_runs_discussions_reopen_without_reseed_or_model_replay')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close();chromium.close()
            browser_data=dict(records=5,approved_records=4,pending_records=1,input_rows=5,imported_records=4,source_row_receipts=5,sft_train=1,sft_test=1,sft_validation=0,sft_files=5,rag_train_chunks=1,rag_files=2,simulated_responses=6,invented_scores=3,discussion_turns=4,pending_generated_candidates=1,embeddings=1,exact_sft_rag_bytes_and_hashes=True,missing_checks_refused=True,queue_idempotent=True,revocation_blocks_future_export=True,old_exports_unchanged=True,original_inputs_unchanged=True,backup_integrity_and_logical_rows=True,saved_records_reopened=True,journal_unchanged_on_reopen=True,real_inference_verified=False,model_trained=False,generated_code_executed=False,publication_authorized=False,complete_restore_performed=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',sqlite_fts5=True,portable_message_wrapping=True,core_tests=82,core_skips=len(skipped),core_skip_methods=skipped,required_windows_methods=7,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional corpus/current-content review, SFT/RAG exports, simulated comparisons/vectors/discussion, independent hashes/backup and reopen; no real inference, training, quality, rights proof, complete restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
