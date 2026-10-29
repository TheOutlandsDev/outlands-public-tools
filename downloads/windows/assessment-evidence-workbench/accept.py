"""Fresh Windows CMD, original native boundaries and actual bundled-server browser acceptance."""
import argparse,json,os,queue,re,shutil,subprocess,sys,threading,zipfile
from pathlib import Path
from contextlib import contextmanager
from http.client import HTTPConnection
from urllib.parse import urlsplit
from build import FILENAME,PREFIX,sha,members
from workflow_demo import tree,encode,snapshot,verify_record,verify_export,ID,ID_KEY,CHECKS
PROFILE=json.loads(Path(__file__).with_name('profile.json').read_bytes())
KIND=PROFILE['module'];NATIVE=['test_native_hardlink_input_refused','test_native_database_hardlink_refused','test_native_symlink_input_refused','test_native_symlink_parent_refused','test_windows_stream_refused']
def accept(packages,workspace,browser=False):
    assert os.name=='nt' and workspace.is_absolute() and not workspace.exists() and workspace.parent.is_dir()
    assert not browser or os.environ.get('GITHUB_ACTIONS')=='true'
    receipt=json.loads((packages/'release-receipt.json').read_bytes());raw=(packages/FILENAME).read_bytes();assert sha(raw)==receipt['sha256'];contents=members(raw);manifest=json.loads(contents[PREFIX+'PACKAGE-MANIFEST.json'])
    assert len(contents)==receipt['files']==72 and set(contents)=={PREFIX+v['path'] for v in manifest['files']}|{PREFIX+'PACKAGE-MANIFEST.json'}
    for v in manifest['files']:assert v['bytes']==len(contents[PREFIX+v['path']]) and v['sha256']==sha(contents[PREFIX+v['path']])
    workspace.mkdir()
    with zipfile.ZipFile(packages/FILENAME) as z:z.extractall(workspace/'fresh extracted folder')
    root=workspace/'fresh extracted folder'/PREFIX.rstrip('/');app=root/'application';private=workspace/'private';private.mkdir();temporary=private/'temp';temporary.mkdir();local=private/'app data';local.mkdir();before=tree(root);pwsh=shutil.which('pwsh');assert pwsh
    env={**os.environ,'PATH':os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),str(Path(pwsh).parent)]),'LOCALAPPDATA':str(local),'TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary),'OUTLANDS_TEST_TEMP':str(temporary),'PYTHONDONTWRITEBYTECODE':'1','WORKBENCH_REQUIRE_LINKS':'1','PYTHONHOME':str(private/'invalid python home'),'PYTHONPATH':str(private/'invalid python path')}
    python=str(root/'runtime/python.exe');checks=[]
    def cmd(args,exercise=False):
        line=subprocess.list2cmdline([str(root/(PROFILE['short']+(' Exercise.cmd' if exercise else ' Demo.cmd'))),*map(str,args)])
        return '"'+os.environ['COMSPEC']+'" /d /s /c "'+line+'"'
    def cli(args,exercise=False,expected=0):
        p=subprocess.run(cmd(args,exercise),cwd=private,env=env,capture_output=True,timeout=180);(private/'last-cli.log').write_bytes(p.stdout+p.stderr);assert p.returncode==expected,'CMD failure; private log retained';return p.stdout
    health=json.loads(cli(['--check']));assert health['runtime']=='3.14.10' and health['isolated'] and health['bundled_runtime'];checks.append('cmd_bundled_isolated_runtime_without_system_python')
    source=subprocess.run([python,'-I','-B',str(app/'release_source.py'),'check'],cwd=app,env=env,capture_output=True,timeout=30);assert source.returncode==0;checks.append('27_original_source_files_byte_exact')
    p=subprocess.run([python,'-I','-B','-W','error',str(app/'run_checks.py')],cwd=app,env=env,capture_output=True,timeout=300);(private/'core-tests.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,'Core tests failed; private log retained';text=p.stderr.decode('utf-8');assert re.search(r'Ran '+str(PROFILE['core'])+r' tests?',text)
    skips=re.findall(r'^(test_\w+) [^\n]*\.\.\. skipped ',text,re.M);assert skips==['test_posix_fifo_refused_without_blocking']
    for n in NATIVE:assert re.search(n+r'[^\n]*\.\.\. ok',text)
    checks.append('all_original_core_methods_5_required_native_windows_only_posix_fifo_skip')
    exercise_path=private/'new fictional exercise';outcome=json.loads(cli(['--workspace',exercise_path],True).decode('utf-8').splitlines()[0]);assert outcome['status']=='PASS' and outcome['command_checks']==(32 if KIND=='assessment' else 24);checks.append('complete_original_cli_exercise_with_independent_history_exports_backup_and_reopen')
    preserved=tree(exercise_path);cli(['--workspace',exercise_path],True,2);assert tree(exercise_path)==preserved;checks.append('existing_exercise_refused_without_writes')
    original_browser_tests=0;captures={};browser_data={}
    @contextmanager
    def server():
        process=subprocess.Popen(cmd(['--no-browser']),cwd=private,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8');lines=queue.Queue();seen=[]
        def reader():
            for line in process.stdout:lines.put(line);seen.append(line)
        worker=threading.Thread(target=reader,daemon=True);worker.start();url=None;http=None
        try:
            import time
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                try:line=lines.get(timeout=1)
                except queue.Empty:
                    assert process.poll() is None,'Server exited before readiness';continue
                match=re.fullmatch(r'Open (http://127\.0\.0\.1:[0-9]+/)\s*',line)
                if match:url=match[1];break
            assert url,'No loopback readiness URL';parsed=urlsplit(url);http=HTTPConnection(parsed.hostname,parsed.port,timeout=20);http.request('GET','/');response=http.getresponse();html=response.read().decode();assert response.status==200;token=re.search(r"\btoken='([A-Za-z0-9_-]{32,})'",html)[1]
            def api(method,path,value=None,expected=200,headers=None):
                h={'X-Outlands-Token':token,'Content-Type':'application/json'} if headers is None else headers
                http.request(method,path,body=encode(value) if value is not None else None,headers=h);resp=http.getresponse();data=json.loads(resp.read());assert resp.status==expected,(path,resp.status);return data
            yield url,api
            api('POST','/api/shutdown',{})
            assert process.wait(timeout=20)==0
        finally:
            if http:http.close()
            if process.poll() is None:
                process.terminate();process.wait(timeout=15)
            worker.join(timeout=2);(private/'server.log').write_text(''.join(seen),encoding='utf-8')
    if browser:
        original_env={**os.environ,'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1','OUTLANDS_TEST_TEMP':str(temporary),'WORKBENCH_REQUIRE_LINKS':'1'}
        p=subprocess.run([sys.executable,'-B','-W','error',str(app/'run_browser_checks.py')],cwd=app,env=original_env,capture_output=True,timeout=300);(private/'original-browser-tests.log').write_bytes(p.stdout+p.stderr);text=(p.stdout+p.stderr).decode('utf-8');assert p.returncode==0 and re.search(r'Ran '+str(PROFILE['browser'])+r' tests?',text) and 'skipped=' not in text;original_browser_tests=PROFILE['browser'];checks.append('all_original_chromium_methods_on_separate_python312')
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=15000)
        journal=local/'Outlands'/PROFILE['parent']/'fictional-demo';fixture=json.loads((app/'examples'/('sample-assessment.json' if KIND=='assessment' else 'sample-recording.json')).read_bytes())
        with sync_playwright() as pw:
            browser_instance=pw.chromium.launch(headless=True);context=browser_instance.new_context(viewport={'width':1280,'height':960});page=context.new_page();requests=[];page.on('request',lambda request:requests.append(request.url))
            def capture(name,anchor):
                target=page.locator('section').filter(has=page.locator(anchor));assert target.count()==1;target.screenshot(path=str(packages/name),type='jpeg',quality=88);b=(packages/name).read_bytes();captures[name]=dict(bytes=len(b),sha256=sha(b),synthetic_only=True)
            with server() as (url,api):
                page.goto(url);expect(page.locator('#status')).to_contain_text('Private instance ready.');assert api('GET','/api/list')==({'assessments':[]} if KIND=='assessment' else {'cases':[]});checks.append('default_windows_appdata_gui_starts_empty_without_automatic_demo')
                assert api('GET','/api/list',expected=403,headers={})==dict(error='SESSION_REQUIRED')
                api('POST','/api/backup',{},403,{'X-Outlands-Token':'invalid','Content-Type':'application/json'});checks.append('unauthenticated_reads_and_writes_refused')
                def show():return verify_record(api('GET','/api/show?id='+ID))
                def submit(command):
                    page.locator('#operation').select_option(command['operation']);page.locator('#template').click();expect(page.locator('#status')).to_contain_text('Template loaded;');draft=json.loads(page.locator('#editor').input_value());draft['command']=command;page.locator('#editor').fill(json.dumps(draft));page.locator('#submit').click();expect(page.locator('#status')).to_contain_text('Saved immutable revision ')
                page.locator('#example').click()
                if KIND=='assessment':
                    expect(page.locator('#status')).to_contain_text('Fictional assessment created.');commands=fixture['commands']
                    for index in (0,2,3,1):submit(commands[index])
                    first=show();assert first['document']['findings'][0]['state']=='Triaged';capture('assessment-triaged.jpg','#findings')
                    submit(commands[4]);pending=show();assert pending['document']['findings'][0]['state']=='Retesting' and pending['document']['retests'][0]['review_state']=='pending';capture('assessment-retest.jpg','#findings')
                    submit(commands[5]);saved=show();assert saved['version']==7 and saved['document']['findings'][0]['state']=='Resolved' and saved['execution_performed'] is False;capture('assessment-resolved.jpg','#findings');browser_data=dict(versions=7,submissions=2,finding_state='Resolved',manual_retest_review='accept',private_export_files=6)
                    stale={ID_KEY:ID,'expected_sha256':first['sha256'],'command':commands[5]}
                else:
                    expect(page.locator('#status')).to_have_text('Fictional recording draft loaded. Submit to save it.');assert api('GET','/api/list')==dict(cases=[]);page.locator('#submit').click();expect(page.locator('#status')).to_contain_text('Saved immutable revision ')
                    from workflow_demo import baseline,ack,healthy
                    first=show();incident=baseline(first);capture('reliability-coverage.jpg','#coverage');page.locator('#incident-detail').select_option(incident['incident_id']);page.locator('#acknowledge').click();expect(page.locator('#status')).to_contain_text('Incident acknowledged');saved=show();current=baseline(saved);assert current['acknowledged'] and current['state']==incident['state'] and current['latest_evidence']==incident['latest_evidence'];capture('reliability-acknowledged.jpg','#incidents')
                    browser_data=dict(versions=4,snapshots=12,baseline_snapshots=10,baseline_seconds=dict(healthy=30,down=25,unknown=25,maintenance=20),acknowledgement_does_not_resolve=True,cached_recovery_refused=True,private_export_files=9)
                    stale={ID_KEY:ID,'expected_sha256':first['sha256'],'command':ack(incident)}
                checks.append('actual_gui_workflow_and_independent_saved_revision_oracles')
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('EXPORT_REVIEW_REQUIRED');checks.append('gui_export_refuses_missing_current_review')
                for key in CHECKS:page.locator('#'+key).check()
                page.locator('#export').click();expect(page.locator('#status')).to_contain_text('Reviewed private');exported=json.loads(page.locator('#handoff').inner_text());old_export=verify_export(journal,exported,saved,6 if KIND=='assessment' else 9);capture(KIND+'-export.jpg','#handoff');checks.append('actual_gui_export_independent_exact_members_receipt_bytes_and_hashes')
                if KIND=='reliability':
                    for value in (healthy(110),healthy(120,110)):submit(dict(operation='ingest',actor='sample_owner',reason='Fictional recorded extension',data=dict(snapshots=[value])))
                    latest=show();health=next(v for v in latest['report']['incidents'] if v['kind']=='health');assert health['state']!='resolved' and health['clean_count']==1;page.locator('#incident-detail').select_option(health['incident_id']);capture('reliability-cached.jpg','#incidents')
                else:latest=saved
                before_rows=snapshot(journal/'database/workbench.sqlite3');page.locator('#editor').fill(json.dumps(stale));draft=page.locator('#editor').input_value();page.locator('#submit').click();expect(page.locator('#status')).to_have_text('ASSESSMENT_REVISION_CONFLICT' if KIND=='assessment' else 'CASE_REVISION_CONFLICT');expect(page.locator('#editor')).to_have_value(draft);assert snapshot(journal/'database/workbench.sqlite3')==before_rows;checks.append('stale_gui_command_keeps_exact_draft_and_saved_journal')
                page.locator('#versions').select_option('1');expect(page.locator('#status')).to_contain_text('Historical revision')
                for key in CHECKS:page.locator('#'+key).check()
                page.locator('#export').click();expect(page.locator('#status')).to_have_text('ASSESSMENT_REVISION_CONFLICT' if KIND=='assessment' else 'CASE_REVISION_CONFLICT');checks.append('historical_export_refused_even_with_review_assertions')
                page.reload();expect(page.locator('#status')).to_contain_text('Private instance ready.')
                with page.expect_response(lambda response:response.url.endswith('/api/backup')) as pending_backup:page.locator('#backup').click()
                backup=pending_backup.value.json();assert sha((journal/backup['file']).read_bytes())==backup['sha256'] and snapshot(journal/backup['file'])==snapshot(journal/'database/workbench.sqlite3');checks.append('actual_gui_backup_integrity_and_all_logical_rows')
                for width in (390,320):page.set_viewport_size({'width':width,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                checks.append('actual_original_interface_fits_390_and_320_pixels')
                assert all(u.startswith(url) for u in requests);assert tree(journal/exported['directory'])==old_export;checks.append('loopback_only_and_earlier_private_export_preserved')
            assert not (journal/'.session-lock').exists();before_rows=snapshot(journal/'database/workbench.sqlite3');checks.append('normal_stop_releases_original_session')
            with server() as (url,api):
                page.goto(url);expect(page.locator('#status')).to_contain_text('Private instance ready.');assert verify_record(api('GET','/api/show?id='+ID))==latest and snapshot(journal/'database/workbench.sqlite3')==before_rows
                for key in CHECKS:expect(page.locator('#'+key)).not_to_be_checked()
            checks.append('actual_cmd_restart_preserves_history_without_reseed_and_starts_fresh_review');context.close();browser_instance.close()
        browser_data.update(independent_revision_and_receipt_hashes=True,independent_export_members_and_hashes=True,stale_change_refused_without_writes=True,review_refused_without_writes=True,original_inputs_unchanged=True,old_exports_unchanged=True,database_backup_integrity_and_rows=True,state_reopened_without_replay=True,operator_assertions_unverified=True,execution_performed=False,network_probed=False,publication_authorized=False,complete_restore_performed=False)
    assert tree(root)==before;checks.append('entire_extracted_package_unchanged')
    result=dict(status='PASS',browser=browser,app_source=receipt['app_source'],packaging_source=receipt['packaging_source'],runtime='3.14.10',package_sha256=receipt['sha256'],default_windows_workspace_qualified=bool(browser),core_tests=PROFILE['core'],core_skips=1,core_skip_methods=skips,required_windows_methods=5,original_browser_tests=original_browser_tests,original_browser_python=sys.version.split()[0],exercise=outcome,browser_data=browser_data,captures=captures,checks=checks,raw_logs_public=False,private_instances_public=False)
    (packages/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status='PASS',checks=len(checks),core_tests=PROFILE['core'],original_browser_tests=original_browser_tests)))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packages',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--browser',action='store_true');a=p.parse_args();accept(a.packages,a.workspace,a.browser)
