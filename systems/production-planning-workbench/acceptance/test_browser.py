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
from planning import application as app,runtime,web
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(runtime.close);self.parent=Path(self.temp.name);self.root=self.parent/'instance';runtime.configure(self.root,create=True);runtime.initialize();app.import_file('inbox/sample-project.json');self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport=dict(width=1360,height=1000));self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.errors=[];self.page.on('request',lambda req:self.requests.append((req.method,req.url)));self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.url='http://127.0.0.1:'+str(self.server.server_port);self.page.goto(self.url);expect(self.page.locator('#message')).to_have_text('Project loaded')
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
        self.assertTrue(all(url.startswith(self.url) for _,url in self.requests));self.assertFalse(app.plan('sample-workshop')['external_system_writes']);self.assertGreater(self.page.locator('#stats .stat').count(),3);self.image('planning-board-wide.png')
    def test_json_save_creates_revision_and_preserves_old_snapshot(self):
        old=app.show('sample-workshop');value=old['project'];value['title']='Fictional revised scenario';self.edit(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');self.assertEqual(app.history('sample-workshop')['revisions'][1]['parent_sha256'],old['revision_sha256']);self.assertEqual(app.show('sample-workshop')['project']['title'],'Fictional revised scenario')
    def test_invalid_json_keeps_draft_and_revision(self):
        before=app.show('sample-workshop');draft='{"fictional":"unfinished"';self.edit(draft);self.save();expect(self.page.locator('#message')).to_have_class('error');expect(self.page.locator('#json')).to_have_value(draft);self.assertEqual(app.show('sample-workshop'),before)
    def test_schema_error_keeps_draft_without_disclosing_input(self):
        value=app.show('sample-workshop')['project'];value['fictional_unknown']='invented rejected text';draft=json.dumps(value);self.edit(draft);self.save();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');expect(self.page.locator('#json')).to_have_value(draft);self.assertEqual(app.show('sample-workshop')['sequence'],1)
    def test_reload_and_example_require_explicit_discard_of_json_draft(self):
        draft=self.page.locator('#json').input_value()+' ';self.edit(draft);self.reload();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');expect(self.page.locator('#json')).to_have_value(draft);self.page.locator('#example').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.reload(True);expect(self.page.locator('#message')).to_have_text('Project loaded');self.assertNotEqual(self.page.locator('#json').input_value(),draft)
    def test_stale_second_browser_save_refused_and_draft_retained(self):
        other=self.context.new_page();other.goto(self.url);expect(other.locator('#message')).to_have_text('Project loaded');value=app.show('sample-workshop')['project'];value['title']='Fictional first change';self.edit(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');value['title']='Fictional stale edit';other.locator('[data-tab=editor]').click();other.locator('#json').fill(json.dumps(value));other.locator('#save').click();expect(other.locator('#message')).to_have_text('OPERATION_REFUSED');expect(other.locator('#json')).to_have_value(json.dumps(value));self.assertEqual(app.show('sample-workshop')['project']['title'],'Fictional first change');other.close()
    def test_private_report_inventory_hashes_and_database_backup(self):
        self.page.locator('#export').click();expect(self.page.locator('#message')).to_contain_text('manifest');value=json.loads(self.page.locator('#message').inner_text());folder=self.root/value['directory'];self.assertEqual({p.name for p in folder.iterdir()},set(value['manifest']['files'])|{'manifest.json'})
        for name,item in value['manifest']['files'].items():self.assertEqual(item,dict(bytes=len((folder/name).read_bytes()),sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest()))
        self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('sha256');value=json.loads(self.page.locator('#message').inner_text());self.assertEqual(value['sha256'],hashlib.sha256((self.root/value['file']).read_bytes()).hexdigest())
    def test_stale_report_pin_refuses_before_creating_directory(self):
        old=app.show('sample-workshop');value=old['project'];value['title']='Fictional outside revision';app.save(runtime.encode(value),old['revision_sha256']);self.page.locator('#export').click();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_unsaved_json_blocks_reports_and_backup(self):
        self.edit(self.page.locator('#json').input_value()+' ');self.page.locator('#export').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.assertEqual(list((self.root/'reports').iterdir()),[]);self.assertEqual(list((self.root/'backups').iterdir()),[])
    def test_lost_save_reply_is_held_until_explicit_server_reload(self):
        value=app.show('sample-workshop')['project'];value['title']='Fictional uncertain reply';self.edit(json.dumps(value))
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/save',lost);self.save();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(app.show('sample-workshop')['sequence'],2);self.save();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(path.endswith('/api/save') for _,path in self.requests),1);self.page.unroute('**/api/save');self.reload(True);expect(self.page.locator('#message')).to_have_text('Project loaded');self.assertIn('Fictional uncertain reply',self.page.locator('#json').input_value());self.assertEqual(app.show('sample-workshop')['sequence'],2)
    def test_restart_reopens_same_private_store(self):
        self.server.shutdown();self.thread.join(5);runtime.close();runtime.configure(self.root);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#message')).to_have_text('Project loaded');self.assertEqual(app.show('sample-workshop')['sequence'],1)
    def test_narrow_keyboard_navigation_and_scroll_containment(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.page.locator('[data-tab=editor]').focus();self.page.keyboard.press('Enter');expect(self.page.locator('#json')).to_be_visible();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.tab('overview');self.page.locator('#products .scroll').first.focus();self.assertEqual(self.page.evaluate('document.activeElement.tabIndex'),0);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('planning-board-narrow.png')

    def review_fields(self,note='Fictional evidence checked'):
        self.page.locator('#actor').fill('sample_reviewer');self.page.locator('#note').fill(note)
    def command(self,name):self.page.locator('#actions').get_by_role('button',name=name,exact=True).first.click()
    def test_operator_acknowledge_exception_note_and_resolve(self):
        self.review_fields();self.command('ACKNOWLEDGE');expect(self.page.locator('#message')).to_have_text('Local review saved');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['status'],'ACKNOWLEDGED');self.review_fields();self.page.locator('#exception').fill('SAMPLE_CHECK');self.command('FLAG_EXCEPTION');expect(self.page.locator('#message')).to_have_text('Local review saved');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['status'],'EXCEPTION');self.review_fields('Fictional additional context');self.command('ADD_NOTE');expect(self.page.locator('#message')).to_have_text('Local review saved');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['exception_code'],'SAMPLE_CHECK');self.review_fields('Fictional resolution');self.command('RESOLVE_EXCEPTION');expect(self.page.locator('#message')).to_have_text('Local review saved');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['status'],'RESOLVED');self.image('planning-review-wide.png')
    def test_operator_draft_cannot_follow_reload_to_another_revision(self):
        self.review_fields();old=app.show('sample-workshop');value=old['project'];value['title']='Fictional second revision';app.save(runtime.encode(value),old['revision_sha256']);self.reload();expect(self.page.locator('#message')).to_contain_text('UNSAVED_DRAFT');self.command('ACKNOWLEDGE');expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertTrue(all(r['workflow']['row_version']==0 for r in app.plan('sample-workshop')['actions']));self.reload(True);expect(self.page.locator('#message')).to_have_text('Project loaded');expect(self.page.locator('#note')).to_have_value('');expect(self.page.locator('#actor')).to_have_value('')
    def test_stale_operator_version_refused_without_overwrite(self):
        plan=app.plan('sample-workshop');action=plan['actions'][0];app.apply_action(runtime.encode(dict(project_id='sample-workshop',revision_sha256=plan['revision_sha256'],action_id=action['action_id'],actor='sample_other',change=dict(command='ACKNOWLEDGE',expected_version=0))));self.review_fields();self.command('ACKNOWLEDGE');expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['row_version'],1);expect(self.page.locator('#note')).to_have_value('Fictional evidence checked')
    def test_literal_markup_note_is_text_and_never_fetched(self):
        note='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>';self.review_fields(note);self.command('ADD_NOTE');expect(self.page.locator('#message')).to_have_text('Local review saved');self.assertEqual(app.plan('sample-workshop')['actions'][0]['workflow']['latest_note'],note);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertFalse(any('example.invalid' in url for _,url in self.requests))
    def test_order_revision_history_append_and_new_review_boundary(self):
        self.page.locator('#actor').fill('sample_reviewer');self.command('ACKNOWLEDGE');expect(self.page.locator('#message')).to_have_text('Local review saved');value=app.show('sample-workshop')['project'];value['order_history'].append(json.loads((self.root/'inbox/sample-order-revision.json').read_text(encoding='utf-8')));self.edit(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 2 saved');self.assertTrue(all(a['workflow']['row_version']==0 for a in app.plan('sample-workshop')['actions']));self.tab('history');self.assertEqual(self.page.locator('#history-table tbody tr').count(),2)

    def test_fictional_template_creates_separate_project_without_changing_original(self):
        before=app.show('sample-workshop');self.page.locator('#example').click();expect(self.page.locator('#message')).to_contain_text('Fictional');value=json.loads(self.page.locator('#json').input_value());value['project_id']='sample-separate';self.page.locator('#json').fill(json.dumps(value));self.save();expect(self.page.locator('#message')).to_have_text('Validated revision 1 saved');self.assertEqual(len(app.projects()['projects']),2);self.assertEqual(app.show('sample-workshop'),before)
    def test_lost_backup_reply_does_not_repeat_write_until_reload(self):
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/backup',lost);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(list((self.root/'backups').iterdir())),1);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(path.endswith('/api/backup') for _,path in self.requests),1);self.page.unroute('**/api/backup');self.reload();expect(self.page.locator('#message')).to_have_text('Project loaded');self.assertEqual(len(list((self.root/'backups').iterdir())),1)
