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
        line=subprocess.list2cmdline([str(root/('Visual Exercise.cmd' if exercise else 'Visual Demo.cmd')),*map(str,args)])
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
    assert re.search(r'Ran 72 tests?',p.stderr.decode('utf-8')) and 'skipped=1' in p.stderr.decode('utf-8')
    core=p.stderr.decode('utf-8')
    for name in ('test_native_hardlink_input_refused','test_native_database_hardlink_refused','test_native_symlink_input_refused','test_native_symlink_parent_refused','test_windows_stream_refused'):
        assert re.search(re.escape(name)+r'[^\n]*\.\.\. ok',core)
    checks.append('all_72_original_core_methods_on_bundled_python_five_required_native_boundaries_one_opposite_platform_skip')
    exercise_workspace=private/'new data exercise';outcome=json.loads(cli(['--workspace',exercise_workspace],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==25
    assert [outcome[k] for k in ('training_views','evaluation_views','unreviewed_training_views','training_versions','first_class_foreground_pixels','second_class_foreground_pixels')]==[1,1,0,3,2480,192]
    checks.append('cmd_exercise_25_original_cli_calls_independent_arithmetic_revision_report_and_backup_oracles')
    preserved=tree(exercise_workspace);cli(['--workspace',exercise_workspace],True,2);assert tree(exercise_workspace)==preserved;checks.append('existing_exercise_refused_without_writes')
    snapshot=json.loads(cli(['--workspace',exercise_workspace,'--cli','views','--dataset','sample-visual']));assert len(snapshot['views'])==2 and sorted(v['version'] for v in snapshot['views'])==[2,3]
    checks.append('original_cli_reopens_saved_training_and_held_out_corrections')
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
        assert p.returncode==0 and re.search(r'Ran 9 tests?',p.stderr.decode('utf-8')) and 'skipped=' not in p.stderr.decode('utf-8'),'Original browser methods failed; private log retained.'
        original_browser_tests=9;checks.append('all_nine_original_canvas_browser_methods_on_separate_test_python_without_skips')
        sys.path.insert(0,str(app))
        from playwright.sync_api import sync_playwright,expect
        from visual_demo import PROPOSAL,CORRECTION,LATER,practice_specimens,verify_report
        specimens=practice_specimens(json.loads((app/'examples/sample-dataset.json').read_bytes()));query=lambda part:'dataset=sample-visual&specimen='+specimens[part]+'&view=front'
        expect.set_options(timeout=20000)
        with sync_playwright() as pw,pw.chromium.launch(headless=True) as chromium:
            context=chromium.new_context(viewport={'width':1280,'height':1024});page=context.new_page();requests=[];errors=[];page.on('request',lambda request:requests.append(request.url));page.on('pageerror',lambda error:errors.append(str(error)))
            def capture(name):
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(packages/name),type='jpeg',quality=88,full_page=True)
                captures[name]=dict(bytes=(packages/name).stat().st_size,sha256=sha((packages/name).read_bytes()),scope='Actual hosted Windows Chromium and bundled Python; original generated pixels only; no address bar, machine path or token')
            def view(s,part='train'):return json.loads(s['http']('/api/view?'+query(part)))
            def selected_report(expected,polygons=None):
                summary=json.loads(page.locator('#report').inner_text());assert summary['selected_views']==expected
                value=dict(directory=summary['directory'],manifest=json.loads((gui_workspace/summary['directory']/'manifest.json').read_bytes()));verify_report(gui_workspace,value,expected,polygons);return value
            def save():page.locator('#save').click();expect(page.locator('#status')).to_have_text('Immutable correction saved. Review is pending for a new version.')
            def approve(training):
                page.locator('#review-status').select_option('approved')
                for key in ('quality','privacy','rights','context'):page.locator('#'+key).check()
                if training:page.locator('#training').check()
                page.locator('#review-form button').click();expect(page.locator('#status')).to_have_text('Review recorded for this saved version.')
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_have_text('Saved view loaded.');first=view(s);assert first['view']['partition']=='train' and first['annotation']['version']==1 and first['annotation']['polygons']==PROPOSAL
                assert len(json.loads(s['http']('/api/views?dataset=sample-visual'))['views'])==2
                images=tree(gui_workspace/'images');inputs=tree(gui_workspace/'inbox');capture('visual-proposal.jpg');checks.append('actual_bundled_browser_seeds_two_generated_views_with_specimen_level_train_test_partitions_and_pending_proposals')
                box=page.locator('#canvas').bounding_box()
                for x,y in ((60,20),(100,20),(100,50),(60,50)):page.mouse.click(box['x']+x,box['y']+y)
                page.keyboard.press('Enter');assert json.loads(page.locator('#polygons').input_value())==CORRECTION
                page.locator('#undo').click();assert json.loads(page.locator('#polygons').input_value())==PROPOSAL;page.locator('#redo').click();assert json.loads(page.locator('#polygons').input_value())==CORRECTION;save()
                second=view(s);assert second['annotation']['version']==2 and second['review']['status']=='pending';capture('visual-correction.jpg');checks.append('actual_bundled_pointer_drawing_enter_finish_undo_redo_and_immutable_correction')
                page.locator('#review-status').select_option('approved');page.locator('#review-form button').click();expect(page.locator('#status')).to_contain_text('OPERATION_REFUSED');assert view(s)==second
                approve(True);page.locator('#training-export').click();expect(page.locator('#status')).to_have_text('Private training export created.');original=selected_report(1,CORRECTION);old_bytes=tree(gui_workspace/original['directory'])
                page.locator('#polygons').fill(json.dumps(LATER));page.locator('#apply').click();save();third=view(s);assert third['annotation']['version']==3 and third['review']==dict(status='pending',training_selected=False,row_version=0)
                page.locator('#training-export').click();expect(page.locator('#status')).to_have_text('Private training export created.');selected_report(0)
                before_refusal=tree(gui_workspace);body=dict(dataset_id='sample-visual',specimen_id=specimens['train'],view_id='front',expected_sha256=second['annotation']['annotation_sha256'],polygons=CORRECTION)
                assert json.loads(s['http']('/api/correct',body,400))==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal
                approve(True);page.locator('#training-export').click();expect(page.locator('#status')).to_have_text('Private training export created.');training=selected_report(1,LATER)
                page.locator('#metrics').click();expect(page.locator('#status')).to_have_text('Saved proposal/correction agreement calculated.');metrics=json.loads(page.locator('#metric-output').inner_text());assert metrics['per_class']['1']['iou']==1280/2480 and metrics['comparison']=='operator_geometry_agreement_not_model_accuracy';capture('visual-reviewed.jpg')
                checks.append('actual_bundled_review_checks_new_version_pending_omission_stale_correction_refusal_and_independent_training_masks')
                saved_training=view(s);assert json.loads(s['http']('/api/view?'+query('train')+'&version=2'))['annotation']['polygons']==CORRECTION
                page.locator('#views').select_option(json.dumps([specimens['test'],'front'],separators=(',',':')));expect(page.locator('#identity')).to_contain_text('test');page.locator('#polygons').fill(json.dumps(CORRECTION));page.locator('#apply').click();save();held=view(s,'test');expect(page.locator('#training')).to_be_disabled()
                bad=dict(dataset_id='sample-visual',specimen_id=specimens['test'],view_id='front',annotation_sha256=held['annotation']['annotation_sha256'],expected_version=0,status='approved',training_selected=True,actor='sample_reviewer',note='Fictional held-out check',checks=dict(quality=True,privacy=True,rights=True,context=True));before_refusal=tree(gui_workspace)
                assert json.loads(s['http']('/api/review',bad,400))==dict(error='OPERATION_REFUSED') and tree(gui_workspace)==before_refusal
                approve(False);page.locator('#evaluation-export').click();expect(page.locator('#status')).to_have_text('Private evaluation export created.');evaluation=selected_report(1,CORRECTION)
                assert {i['specimen_id'] for i in training['manifest']['selected']}.isdisjoint(i['specimen_id'] for i in evaluation['manifest']['selected']);capture('visual-heldout.jpg');checks.append('actual_bundled_held_out_training_disabled_and_backend_refused_separate_evaluation_mask_export')
                assert tree(gui_workspace/'images')==images and tree(gui_workspace/'inbox')==inputs and tree(gui_workspace/original['directory'])==old_bytes
                page.locator('#backup').click();expect(page.locator('#status')).to_contain_text('Database-only backup created.');backup=json.loads(page.locator('#report').inner_text());raw=(gui_workspace/backup['file']).read_bytes();assert backup['sha256']==sha(raw) and not backup['image_files_included']
                import sqlite3
                with closing(sqlite3.connect((gui_workspace/backup['file']).as_uri()+'?mode=ro',uri=True)) as db:assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
                checks.append('actual_bundled_historical_annotations_original_images_old_export_and_database_backup_preserved')
                page.set_viewport_size(dict(width=390,height=844));page.locator('#point-x').focus();page.keyboard.press('Tab');expect(page.locator('#point-y')).to_be_focused();assert page.evaluate('document.documentElement.scrollWidth')<=390;checks.append('narrow_bundled_canvas_layout_and_keyboard_coordinate_navigation')
                page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping.')
            saved=tree(gui_workspace)
            with server() as s:
                page.goto(s['url']);expect(page.locator('#status')).to_have_text('Saved view loaded.');assert view(s)==saved_training and tree(gui_workspace)==saved and tree(gui_workspace/original['directory'])==old_bytes
                expect(page.locator('#identity')).to_contain_text('version 3');page.locator('#shutdown').click();s['shutdown_requested']=True;expect(page.locator('#status')).to_contain_text('Local server stopping.')
            checks.append('actual_bundled_saved_corrections_and_version_review_reopen_without_reseed_owned_shutdown_releases_lock')
            assert not errors and all(url.startswith(('http://127.0.0.1:','blob:http://127.0.0.1:')) for url in requests);context.close()
            browser_data=dict(practice_views=2,train_specimens=1,test_specimens=1,training_views=1,evaluation_views=1,unreviewed_training_views=0,training_versions=3,report_files_per_selected_view=5,first_class_foreground_pixels=2480,second_class_foreground_pixels=192,first_class_iou=1280/2480,independent_mask_pixels_checked=True,report_hashes_independently_verified=True,held_out_training_refused=True,missing_review_checks_refused=True,new_version_does_not_inherit_review=True,historical_correction_retained=True,old_report_unchanged=True,original_inputs_unchanged=True,specimen_splits_disjoint=True,backup_integrity_checked=True,saved_correction_reopened=True,journal_bytes_unchanged_on_reopen=True,backup_includes_images=False,trained_model_executed=False,real_images_or_model_weights_included=False)
    assert tree(root)==before;checks.append('no_package_writes_or_shipped_private_state')
    result=dict(schema=1,status='PASS',browser=browser,package_sha256=receipt['sha256'],packaging_source=receipt['packaging_source'],app_source=receipt['app_source'],runtime='3.14.10',core_tests=72,core_skips=1,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],checks=checks,exercise=outcome,browser_data=browser_data,captures=captures,scope='Fictional generated-image Windows CMD/canvas annotation, independent mask pixels, per-version review, specimen split separation, export and reopen; no real images, model training/inference, full restore or separate-PC handoff')
    if browser:(packages/'acceptance.json').write_bytes(encoded(result))
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
