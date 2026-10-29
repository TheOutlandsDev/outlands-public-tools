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
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','OUTLANDS_DATASET_REQUIRE_LINKS':'1','PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def command(args,exercise=False):
        line=subprocess.list2cmdline([str(root/('Dataset Review Exercise.cmd' if exercise else 'Dataset Review Demo.cmd')),*map(str,args)])
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
    core=p.stderr.decode('utf-8');assert re.search(r'Ran 115 tests?',core)
    import ast
    allowed=set();required=[]
    for filename in ('test_io_safety.py','test_store_schema.py'):
        tree_ast=ast.parse((app/'tests'/filename).read_text(encoding='utf-8'))
        for cls in tree_ast.body:
            if isinstance(cls,ast.ClassDef):
                names=[n.name for n in cls.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
                if cls.name.startswith('Posix'):allowed.update(names)
                if cls.name.startswith('Windows'):
                    for name in names:
                        if name.startswith('test_short_name_'):allowed.add(name)
                        else:required.append(name)
    skipped=re.findall(r'^(test_\w+) [^\n]*\.\.\. skipped ',core,re.M);assert len(required)==22 and 10<=len(skipped)<=12 and set(skipped)<=allowed
    assert re.search(r'skipped='+str(len(skipped))+r'\)',core)
    for name in required:assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_115_original_methods_on_bundled_python_22_required_windows_methods_only_posix_and_optional_short_name_skips')
    exercise_workspace=private/'new dataset exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==24
    assert [outcome[k] for k in ('input_rows','records','test_records','approved_records','provenance_rows','exported_records','export_files')]==[5,4,2,1,5,1,2]
    checks.append('cmd_exercise_24_original_cli_calls_independent_ids_group_splits_provenance_state_pins_exports_and_backup')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    snapshot=json.loads(cli(['--workspace',exercise_workspace,'--cli','status']));assert snapshot['total']==4 and snapshot['counts']==dict(pending=3,approved=1,rejected=0)
    checks.append('original_cli_reopens_four_records_and_two_reviews')
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
        p=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=test_env,capture_output=True,timeout=600);(private/'original-browser-tests.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0 and re.search(r'Ran 25 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=25;checks.append('all_25_original_dataset_browser_methods_on_separate_test_python_without_skips')
        from playwright.sync_api import sync_playwright,expect
        from review_demo import fixture_ids,verify_store,verify_export,logical,encode
        fixture=fixture_ids(app);expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual hosted Windows Chromium and bundled Python; original fictional text only; no address bar, machine path, token or review timestamps shown')
            def state(s):return json.loads(s['http']('/api/state'))
            def detail(s,identifier):return json.loads(s['http']('/api/detail?id='+identifier))
            def fields(tab,decision='approved',note='Fictional evidence checked',checked=True):
                tab.locator('#actor').fill('sample_reviewer');tab.locator('#note').fill(note);tab.locator('#decision').select_option(decision)
                if checked:
                    for key in ('quality','privacy','rights','context'):tab.locator('#'+key).check()
            with server() as s:
                page.goto(s['url']);expect(page.locator('#message')).to_have_text('Private store ready. Nothing imported or approved automatically.');assert state(s)['total']==0
                inputs=tree(gui_workspace/'inbox');page.locator('[data-tab=transfer]').click();page.locator('#export').click();expect(page.locator('#message')).to_have_text('Checked private export created. Sharing needs a separate audit.');empty=json.loads(page.locator('#output').inner_text());verify_export(gui_workspace,empty,fixture,False)
                page.locator('#import').click();expect(page.locator('#message')).to_have_text('Import saved. New records are pending; holdouts remain conservative.');imported=state(s);assert imported['total']==4 and imported['counts']==dict(pending=4,approved=0,rejected=0)
                _,head=verify_store(gui_workspace,fixture);assert head==imported['head'];page.locator('[data-tab=records]').click();page.locator('#query').fill('DUPLICATE');page.locator('#search').click();expect(page.locator('#page-info')).to_contain_text('1 of 1');page.locator('#rows button').click();expect(page.locator('#message')).to_have_text('Saved record loaded. Review assertions start unchecked.');linked=detail(s,fixture['duplicate']);assert linked['split']=='test' and linked['linked_records']==2 and linked['aliases']==['sample-gamma'] and len(linked['provenance'])==2;capture('dataset-imported.jpg')
                checks.append('actual_bundled_empty_start_zero_record_export_and_five_to_four_import_with_independent_groups_and_provenance')
                page.locator('#query').fill('');page.locator('#search').click();expect(page.locator('#message')).to_have_text('Saved state refreshed. No action replayed.');page.locator('[data-record="'+fixture['train']+'"]').click();expect(page.locator('#message')).to_have_text('Saved record loaded. Review assertions start unchecked.')
                fields(page,checked=False);page.locator('#review').click();expect(page.locator('#message')).to_have_text('FOUR_CHECKS_REQUIRED');expect(page.locator('#note')).to_have_value('Fictional evidence checked');assert state(s)['counts']['approved']==0
                for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                other=context.new_page();other.goto(s['url']);expect(other.locator('#message')).to_have_text('Private store ready. Nothing imported or approved automatically.');other.locator('[data-record="'+fixture['validation']+'"]').click();expect(other.locator('#message')).to_have_text('Saved record loaded. Review assertions start unchecked.');fields(other,'pending','Fictional second-tab review',False);other.locator('#review').click();expect(other.locator('#message')).to_have_text('Local review saved. Public release remains unapproved.');other.close()
                before_refusal=tree(gui_workspace);page.locator('#review').click();expect(page.locator('#message')).to_have_text('STALE_STATE_REFRESH_REQUIRED');expect(page.locator('#note')).to_have_value('Fictional evidence checked');assert tree(gui_workspace)==before_refusal and detail(s,fixture['train'])['status']=='pending';capture('dataset-stale.jpg')
                checks.append('actual_bundled_two_tab_stale_review_and_missing_assertions_refused_with_draft_and_store_preserved')
                page.locator('#refresh').click();expect(page.locator('#message')).to_contain_text('UNSAVED_REVIEW_DRAFT');page.locator('#discard').check();page.locator('#refresh').click();expect(page.locator('#message')).to_have_text('Saved state refreshed. No action replayed.');expect(page.locator('#note')).to_have_value('')
                for key in ('quality','privacy','rights','context'):expect(page.locator('#'+key)).not_to_be_checked()
                fields(page);page.locator('#review').click();expect(page.locator('#message')).to_have_text('Local review saved. Public release remains unapproved.')
                for key in ('quality','privacy','rights','context'):expect(page.locator('#'+key)).not_to_be_checked()
                approved=state(s);saved_detail=detail(s,fixture['train']);assert approved['counts']==dict(pending=3,approved=1,rejected=0) and saved_detail['status']=='approved' and len(saved_detail['reviews'])==1
                checks.append('actual_bundled_explicit_discard_refresh_new_assertions_current_state_approval_and_fresh_unchecked_forms')
                page.locator('[data-tab=transfer]').click();page.locator('#export').click();expect(page.locator('#message')).to_have_text('Checked private export created. Sharing needs a separate audit.');exported=json.loads(page.locator('#output').inner_text());old_export=verify_export(gui_workspace,exported,fixture,True);assert exported['manifest']['store_head']==approved['head'];capture('dataset-export.jpg')
                page.locator('#import').click();expect(page.locator('#message')).to_have_text('Import saved. New records are pending; holdouts remain conservative.');assert state(s)==approved and detail(s,fixture['train'])==saved_detail
                before_refusal=tree(gui_workspace)
                for operation in ('export','backup'):assert json.loads(s['http']('/api/'+operation,dict(expected=imported['head']),400))==dict(error='STALE_STATE_REFRESH_REQUIRED') and tree(gui_workspace)==before_refusal
                checks.append('actual_bundled_export_bytes_and_hashes_reimported_approval_and_stale_export_backup_refusals_independently_checked')
                (gui_workspace/'inbox/invalid.jsonl').write_bytes(encode(dict(text='Fictional extra row',group='sample-extra'))+b'\nnull\n');page.locator('#import-file').fill('inbox/invalid.jsonl');before_invalid=tree(gui_workspace);page.locator('#import').click();expect(page.locator('#message')).to_have_text('OPERATION_UNCERTAIN_REFRESH_REQUIRED');assert tree(gui_workspace)==before_invalid and state(s)['head']==approved['head'] and state(s)['refresh_required']
                page.locator('#export').click();expect(page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');assert tree(gui_workspace)==before_invalid;page.locator('#refresh').click();expect(page.locator('#message')).to_have_text('Saved state refreshed. No action replayed.');assert state(s)==approved;page.locator('#import-file').fill('inbox/sample-records.jsonl')
                checks.append('actual_bundled_invalid_batch_atomicity_and_uncertain_write_gate_until_explicit_refresh_without_replay')
                for name,digest in inputs.items():assert sha((gui_workspace/'inbox'/name).read_bytes())==digest
                assert tree(gui_workspace/exported['directory'])==old_export;page.locator('#backup').click();expect(page.locator('#message')).to_have_text('Checked database-only backup created. No automatic restore.');backup=json.loads(page.locator('#output').inner_text());assert backup['database_only'] and sha((gui_workspace/backup['file']).read_bytes())==backup['sha256'] and logical(gui_workspace/backup['file'])==logical(gui_workspace/'database/review.sqlite3')
                checked,head=verify_store(gui_workspace,fixture,True);assert head==approved['head'] and len(checked['reviews'])==2;checks.append('actual_bundled_original_input_old_export_database_backup_integrity_and_logical_rows_preserved')
                page.set_viewport_size(dict(width=390,height=844));page.locator('[data-tab=records]').click();page.locator('#rows').focus();assert page.evaluate('document.activeElement.id')=='rows' and page.locator('#rows').evaluate('(node)=>node.scrollWidth-node.clientWidth')>0 and page.evaluate('document.documentElement.scrollWidth')<=390;page.locator('[data-tab=transfer]').focus();page.keyboard.press('Enter');expect(page.locator('#import')).to_be_visible();checks.append('narrow_bundled_keyboard_navigation_and_readable_contained_scroll_table')
                page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            saved=tree(gui_workspace)
            with server() as s:
                page.set_viewport_size(dict(width=1280,height=1024));page.goto(s['url']);expect(page.locator('#message')).to_have_text('Private store ready. Nothing imported or approved automatically.');assert state(s)==approved and detail(s,fixture['train'])==saved_detail and tree(gui_workspace)==saved
                expect(page.locator('#actor')).to_have_value('');expect(page.locator('#note')).to_have_value('');capture('dataset-reopened.jpg');page.locator('#stop').click();s['shutdown_requested']=True;expect(page.locator('#message')).to_contain_text('Local UI stopped.')
            checks.append('actual_bundled_records_reviews_and_provenance_reopen_without_import_or_review_owned_shutdown_releases_lock')
            assert not errors and all(url.startswith('http://127.0.0.1:') for url in requests);context.close()
            browser_data=dict(input_rows=5,records=4,train_records=1,validation_records=1,test_records=2,approved_records=1,pending_records=3,provenance_rows=5,reviews=2,exported_records=1,export_files=2,empty_export_records=0,duplicate_linked_records_in_test=2,independent_record_ids_and_group_splits_checked=True,provenance_source_rows_independently_checked=True,logical_state_pin_independently_checked=True,stale_review_refused=True,missing_review_checks_refused=True,stale_export_and_backup_refused=True,invalid_batch_atomicity_checked=True,reimport_preserves_reviews_and_pin=True,export_bytes_and_hashes_independently_verified=True,old_export_unchanged=True,original_inputs_unchanged=True,backup_integrity_and_logical_rows_checked=True,saved_records_reopened=True,journal_bytes_unchanged_on_reopen=True,two_real_browser_tabs=True,stale_draft_retained=True,explicit_discard_required=True,fresh_review_assertions_unchecked=True,uncertain_reply_gate_without_replay=True,public_release_authorized=False,export_automatically_training_only=False,model_executed=False,complete_restore_performed=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=115,core_skips=len(skipped),core_skip_methods=skipped,required_windows_methods=22,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional text Windows CMD/browser review, independent hashes/groups/provenance, two-tab stale decisions, explicit discard/refresh, uncertainty gates, private exports/backups and reopen; no training-only export filter, anonymity, rights proof, model execution, full restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
