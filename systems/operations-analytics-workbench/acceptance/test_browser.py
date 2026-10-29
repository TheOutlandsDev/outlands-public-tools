"""Real Chromium acceptance using only fresh fictional private instances."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright,expect
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from operations_analytics import application as app,runtime,web
expect.set_options(timeout=15000)

class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(runtime.close);self.parent=Path(self.temp.name);self.root=self.parent/'instance';runtime.configure(self.root,create=True);runtime.initialize();app.import_file('inbox/sample-scenario.json');self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport=dict(width=1360,height=1000));self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.errors=[];self.page.on('request',lambda req:self.requests.append((req.method,req.url)));self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.url='http://127.0.0.1:'+str(self.server.server_port);self.page.goto(self.url);expect(self.page.locator('#message')).to_have_text('Scenario loaded')
    def tearDown(self):self.assertEqual(self.errors,[])
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def tab(self,name):self.page.locator('[data-tab='+name+']').click()
    def edit(self,text):self.tab('editor');self.page.locator('#json').fill(text)
    def save(self):self.page.locator('#save').click()
    def reload(self,discard=False):
        if discard:self.page.locator('#discard').check()
        self.page.locator('#load').click()
    def image(self,name):
        if os.environ.get('OUTLANDS_BROWSER_EVIDENCE'):
            root=Path(os.environ['OUTLANDS_BROWSER_EVIDENCE']);root.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(root/name),full_page=True)
    def test_fictional_board_and_no_external_requests(self):
        self.assertTrue(all(url.startswith(self.url) for _,url in self.requests));self.assertFalse(app.plan('sample-operations')['external_system_writes']);self.assertGreater(self.page.locator('#stats .stat').count(),3);self.image('operations_analytics-board-wide.png')
    def test_json_save_creates_revision_and_preserves_old_snapshot(self):
        old=app.show('sample-operations');value=old['scenario'];value['title']='Fictional revised scenario';self.edit(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');self.assertEqual(app.history('sample-operations')['revisions'][1]['parent_sha256'],old['revision_sha256']);self.assertEqual(app.show('sample-operations')['scenario']['title'],'Fictional revised scenario')
    def test_invalid_json_keeps_draft_and_revision(self):
        before=app.show('sample-operations');draft='{"fictional":"unfinished"';self.edit(draft);self.save();expect(self.page.locator('#message')).to_have_class('error');expect(self.page.locator('#json')).to_have_value(draft);self.assertEqual(app.show('sample-operations'),before)
    def test_schema_error_keeps_draft_without_disclosing_input(self):
        value=app.show('sample-operations')['scenario'];value['fictional_unknown']='invented rejected text';draft=json.dumps(value);self.edit(draft);self.save();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');expect(self.page.locator('#json')).to_have_value(draft);self.assertEqual(app.show('sample-operations')['sequence'],1)
    def test_reload_and_example_require_explicit_discard_of_json_draft(self):
        draft=self.page.locator('#json').input_value()+' ';self.edit(draft);self.reload();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');expect(self.page.locator('#json')).to_have_value(draft);self.page.locator('#example').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.reload(True);expect(self.page.locator('#message')).to_have_text('Scenario loaded');self.assertNotEqual(self.page.locator('#json').input_value(),draft)
    def test_stale_second_browser_save_refused_and_draft_retained(self):
        other=self.context.new_page();other.goto(self.url);expect(other.locator('#message')).to_have_text('Scenario loaded');value=app.show('sample-operations')['scenario'];value['title']='Fictional first change';self.edit(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');value['title']='Fictional stale edit';other.locator('[data-tab=editor]').click();other.locator('#json').fill(json.dumps(value));other.locator('#save').click();expect(other.locator('#message')).to_have_text('OPERATION_REFUSED');expect(other.locator('#json')).to_have_value(json.dumps(value));self.assertEqual(app.show('sample-operations')['scenario']['title'],'Fictional first change');other.close()
    def test_private_report_inventory_hashes_and_database_backup(self):
        self.page.locator('#export').click();expect(self.page.locator('#message')).to_contain_text('manifest');value=json.loads(self.page.locator('#message').inner_text());folder=self.root/value['directory'];self.assertEqual({p.name for p in folder.iterdir()},set(value['manifest']['files'])|{'manifest.json'})
        for name,item in value['manifest']['files'].items():self.assertEqual(item,dict(bytes=len((folder/name).read_bytes()),sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest()))
        self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('sha256');value=json.loads(self.page.locator('#message').inner_text());self.assertEqual(value['sha256'],hashlib.sha256((self.root/value['file']).read_bytes()).hexdigest())
    def test_stale_report_pin_refuses_before_creating_directory(self):
        old=app.show('sample-operations');value=old['scenario'];value['title']='Fictional outside revision';app.save(runtime.encode(value),old['revision_sha256']);self.page.locator('#export').click();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_unsaved_json_blocks_reports_and_backup(self):
        self.edit(self.page.locator('#json').input_value()+' ');self.page.locator('#export').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.assertEqual(list((self.root/'reports').iterdir()),[]);self.assertEqual(list((self.root/'backups').iterdir()),[])
    def test_lost_save_reply_is_held_until_explicit_server_reload(self):
        value=app.show('sample-operations')['scenario'];value['title']='Fictional uncertain reply';self.edit(json.dumps(value))
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/save',lost);self.save();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(app.show('sample-operations')['sequence'],2);self.save();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(path.endswith('/api/save') for _,path in self.requests),1);self.page.unroute('**/api/save');self.reload(True);expect(self.page.locator('#message')).to_have_text('Scenario loaded');self.assertIn('Fictional uncertain reply',self.page.locator('#json').input_value());self.assertEqual(app.show('sample-operations')['sequence'],2)
    def test_restart_reopens_same_private_store(self):
        self.server.shutdown();self.thread.join(5);runtime.close();runtime.configure(self.root);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#message')).to_have_text('Scenario loaded');self.assertEqual(app.show('sample-operations')['sequence'],1)
    def test_narrow_keyboard_navigation_and_scroll_containment(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.page.locator('[data-tab=editor]').focus();self.page.keyboard.press('Enter');expect(self.page.locator('#json')).to_be_visible();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.tab('board');self.page.locator('#capacity').focus();self.assertEqual(self.page.evaluate('document.activeElement.tabIndex'),0);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('operations_analytics-board-narrow.png')

    def review_fields(self):
        self.tab('review');self.page.locator('#actor').fill('sample_reviewer');self.page.locator('#note').fill('Fictional assumptions checked')
    def review_save(self):self.page.locator('#review-form button[type=submit]').click()
    def test_all_scenario_form_domains_save_with_independent_expected_results(self):
        self.tab('forms')
        values=[('capacity','people','4'),('process','good_units','120'),('inventory','on_hand','20'),('dispatch','wait_hours','48'),('policy','age_horizon_hours','96')]
        for sequence,(domain,field,value) in enumerate(values,2):
            self.page.locator('#domain').select_option(domain)
            if domain=='dispatch':self.page.locator('#case').select_option(label='ready-a')
            self.page.locator('#fields [name="'+field+'"]').fill(value);self.page.locator('#case-form button[type=submit]').click();expect(self.page.locator('#message')).to_have_text('Validated revision '+str(sequence)+' saved');result=app.plan('sample-operations');self.assertEqual(result['capacity'][0]['whole_unit_capacity'],268)
            if domain=='process':self.assertEqual(result['process'][0]['oee_fraction'],0.5)
            if domain=='inventory':self.assertEqual(result['inventory'][0]['proposed_order_units'],0)
            if domain=='dispatch':self.assertEqual(result['dispatch']['ranked'][0]['priority_score'],0.9)
            if domain=='policy':self.assertEqual(result['dispatch']['ranked'][0]['priority_score'],0.6)
        self.image('operations_analytics-forms-wide.png')
    def test_case_draft_preserved_when_switching_domain_or_loading(self):
        self.tab('forms');self.page.locator('#fields [name=people]').fill('5');self.page.locator('#domain').select_option('inventory');expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');expect(self.page.locator('#domain')).to_have_value('capacity');expect(self.page.locator('#fields [name=people]')).to_have_value('5');self.reload();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.reload(True);expect(self.page.locator('#message')).to_have_text('Scenario loaded');expect(self.page.locator('#fields [name=people]')).to_have_value('3')
    def test_add_case_template_and_comparison_history(self):
        self.tab('forms');self.page.locator('#new-case').click();expect(self.page.locator('#message')).to_contain_text('unique ID');self.page.locator('#fields [name=id]').fill('sample-extra');self.page.locator('#case-form button[type=submit]').click();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');self.tab('compare');self.page.locator('#compare-run').click();expect(self.page.locator('#comparison')).to_contain_text('sample-extra');self.assertEqual(self.page.locator('#history-table tbody tr').count(),2);self.image('operations_analytics-comparison-wide.png')
    def test_review_is_revision_bound_and_stale_version_refused(self):
        self.review_fields();self.review_save();expect(self.page.locator('#message')).to_contain_text('Local review saved');self.assertEqual(app.plan('sample-operations')['reviews'][0]['row_version'],1);value=app.show('sample-operations');scenario=value['scenario'];scenario['title']='Fictional next revision';app.save(runtime.encode(scenario),value['revision_sha256']);self.review_fields();self.review_save();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');expect(self.page.locator('#note')).to_have_value('Fictional assumptions checked');self.assertEqual(app.plan('sample-operations')['reviews'],[]);self.reload(True);expect(self.page.locator('#message')).to_have_text('Scenario loaded');expect(self.page.locator('#note')).to_have_value('');self.review_fields();self.review_save();expect(self.page.locator('#message')).to_contain_text('Local review saved');self.assertEqual(app.plan('sample-operations',1)['reviews'][0]['row_version'],1)
    def test_completion_ingest_replay_and_historical_stability(self):
        self.tab('review');self.page.locator('#ingest').click();expect(self.page.locator('#message')).to_contain_text('inserted_events');self.assertEqual(app.plan('sample-operations')['snapshot']['completed_units'],33);self.assertEqual(app.plan('sample-operations',1)['snapshot']['completed_units'],25);self.page.locator('#ingest').click();expect(self.page.locator('#message')).to_contain_text('"created": false');self.assertEqual(len(app.history('sample-operations')['revisions']),2)
    def test_invalid_completion_batch_is_atomic_and_does_not_advance_revision(self):
        (self.root/'inbox/invalid-events.json').write_text('[{"fictional":"invalid"}]',encoding='utf-8');self.tab('review');self.page.locator('#events-file').fill('inbox/invalid-events.json');self.page.locator('#ingest').click();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(app.show('sample-operations')['sequence'],1);self.assertEqual(app.plan('sample-operations')['snapshot']['completed_units'],25)
    def test_literal_review_note_remains_text_without_external_request(self):
        self.review_fields();note='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>';self.page.locator('#note').fill(note);self.review_save();expect(self.page.locator('#message')).to_contain_text('Local review saved');expect(self.page.locator('#reviews')).to_contain_text(note);self.assertEqual(self.page.locator('#reviews img').count(),0);self.assertFalse(any('example.invalid' in url for _,url in self.requests));self.assertIsNone(self.page.evaluate('window.fixtureExecuted'))
    def make_actual_planning_report(self):
        companion=APP.parent/'production-planning-workbench';cli=companion/'workbench.py'
        if not cli.exists():
            if os.environ.get('WORKBENCH_REQUIRE_HANDOFF')=='1':self.fail('Companion public planning source required for integration acceptance')
            self.skipTest('Companion public planning source separately required for integration test')
        workspace=self.parent/'planning-instance';cmd=[sys.executable,'-B',str(cli),'--workspace',str(workspace)];completed=subprocess.run(cmd+['demo'],capture_output=True,text=True,encoding='utf-8',timeout=30);self.assertEqual(completed.returncode,0,completed.stdout);self.assertFalse((workspace/'.session-lock').exists());exported=subprocess.run(cmd+['export','--project','sample-workshop'],capture_output=True,text=True,encoding='utf-8',check=True,timeout=30);report=json.loads(exported.stdout);source=workspace/report['directory'];target=self.root/'inbox/planning-report';target.mkdir();self.assertEqual({p.name for p in source.iterdir()},{'plan.json','orders.csv','allocations.csv','readiness.csv','manifest.json'})
        for path in source.iterdir():shutil.copyfile(path,target/path.name)
        return target,report
    def attach(self):self.tab('review');self.page.locator('#planning-directory').fill('inbox/planning-report');self.page.locator('#attach').click()
    def test_actual_stopped_planning_export_browser_handoff_and_no_state_mapping(self):
        target,report=self.make_actual_planning_report();before=app.plan('sample-operations');self.attach();expect(self.page.locator('#message')).to_contain_text('"sequence": 2');after=app.plan('sample-operations');ref=after['planning_reference'];self.assertEqual(ref['revision_sha256'],report['manifest']['revision_sha256']);self.assertEqual(ref['manifest_sha256'],hashlib.sha256((target/'manifest.json').read_bytes()).hexdigest());self.assertEqual(ref['remaining_demand'],170);self.assertEqual(ref['dock_allocated_quantity'],25);self.assertEqual(ref['covered_quantity'],85);self.assertEqual(ref['uncovered_quantity'],60);self.assertEqual(before['dispatch'],after['dispatch']);self.assertEqual(before['snapshot'],after['snapshot']);self.assertIsNone(app.plan('sample-operations',1)['planning_reference']);self.image('operations_analytics-handoff-wide.png')
    def test_actual_handoff_tamper_or_extra_file_never_creates_revision(self):
        target,_=self.make_actual_planning_report();file=target/'orders.csv';raw=file.read_bytes();file.write_bytes(raw+b'fictional tamper');self.attach();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(app.show('sample-operations')['sequence'],1);file.write_bytes(raw);(target/'extra.json').write_text('{}',encoding='utf-8');self.attach();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertIsNone(app.plan('sample-operations')['planning_reference']);self.assertEqual(app.show('sample-operations')['sequence'],1)

    def test_fictional_template_creates_separate_project_without_changing_original(self):
        before=app.show('sample-operations');self.page.locator('#example').click();expect(self.page.locator('#message')).to_contain_text('Fictional');value=json.loads(self.page.locator('#json').input_value());value['project_id']='sample-separate';self.page.locator('#json').fill(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 1 saved');self.assertEqual(len(app.projects()['projects']),2);self.assertEqual(app.show('sample-operations'),before)
    def test_lost_backup_reply_does_not_repeat_write_until_reload(self):
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/backup',lost);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(list((self.root/'backups').iterdir())),1);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(path.endswith('/api/backup') for _,path in self.requests),1);self.page.unroute('**/api/backup');self.reload();expect(self.page.locator('#message')).to_have_text('Scenario loaded');self.assertEqual(len(list((self.root/'backups').iterdir())),1)

    def test_stale_review_version_does_not_overwrite_other_local_record(self):
        head=app.show('sample-operations')['revision_sha256'];app.review(runtime.encode(dict(project_id='sample-operations',revision_sha256=head,domain='capacity',case_id='base',expected_version=0,status='reviewed',actor='sample_other',note='Fictional first review')));self.review_fields();self.review_save();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(app.plan('sample-operations')['reviews'][0]['row_version'],1);self.assertEqual(app.plan('sample-operations')['reviews'][0]['actor'],'sample_other')
    def test_rehashed_handoff_authority_and_conservation_tamper_refused(self):
        target,_=self.make_actual_planning_report();original=(target/'plan.json').read_bytes();manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        for mode in ('authority','conservation'):
            value=json.loads(original)
            if mode=='authority':value['shipment_execution_authorized']=True
            else:value['products'][0]['remaining_demand']+=1
            changed=runtime.encode(value);(target/'plan.json').write_bytes(changed);manifest['files']['plan.json']=dict(bytes=len(changed),sha256=hashlib.sha256(changed).hexdigest());(target/'manifest.json').write_bytes(runtime.encode(manifest));self.attach();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(app.show('sample-operations')['sequence'],1);self.assertIsNone(app.plan('sample-operations')['planning_reference'])
