"""Actual Chromium workflows using only invented text in disposable private stores."""
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from developer import application as app,jobs,runtime as r,web


class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.addCleanup(jobs.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport={'width':1440,'height':1100});self.addCleanup(self.context.close);self.external=[];self.errors=[]
        def route(request):
            if request.request.url.startswith(f'http://127.0.0.1:{self.server.server_port}/'):request.continue_()
            else:self.external.append(request.request.url.split(':',1)[0]);request.abort()
        self.context.route('**/*',route);self.page=self.context.new_page();self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.goto(f'http://127.0.0.1:{self.server.server_port}/');expect(self.page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def tearDown(self):
        self.assertEqual(self.external,[]);self.assertEqual(self.errors,[]);destination=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if destination:
            target=Path(destination);target.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(target/(self._testMethodName+'.png')),full_page=True)
    def load(self):
        self.page.locator('#example').click();expect(self.page.locator('#status')).to_have_text('Fictional project loaded into import draft.');self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('Project imported into private immutable history.')
    def file(self,path):self.page.locator('#files').select_option(path);expect(self.page.locator('#path')).to_have_value(path)
    def save(self,text):
        self.page.locator('#editor').fill(text);self.page.locator('#save').click();expect(self.page.locator('#status')).to_have_text('File saved in immutable project history. No code executed.')
    def validate(self):
        self.page.locator('#validate').click();expect(self.page.locator('#status')).to_have_text('Validation finished: completed. New artifact is pending review.');return self.page.locator('#artifacts').input_value()
    def approve(self):
        self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('Review saved for this exact validation and source revision.')
    def test_full_import_edit_validate_review_and_historical_export(self):
        self.load();self.file('src/sample.py');self.save('value = 2\n');identifier=self.validate();expect(self.page.locator('#validation')).to_contain_text('"pass": 4');self.approve();self.save('value = 3\n');self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Approved source exported inside the private workspace. Review before sharing.');receipt=json.loads(self.page.locator('#receipt').inner_text());self.assertEqual(receipt['manifest']['project_version'],2);self.assertTrue((self.root/receipt['directory']/'project-source.zip').exists());self.assertEqual(app.artifact(identifier)['review']['status'],'approved')
    def test_unsaved_editor_refuses_file_switch_and_validation(self):
        self.load();self.file('src/sample.py');self.page.locator('#editor').fill('draft = 7\n');self.page.locator('#files').select_option('README.md');expect(self.page.locator('#status')).to_have_text('EDITOR_DRAFT_UNSAVED');expect(self.page.locator('#editor')).to_have_value('draft = 7\n');self.page.locator('#validate').click();expect(self.page.locator('#status')).to_have_text('EDITOR_DRAFT_UNSAVED');self.assertEqual(app.artifacts()['artifacts'],[]);self.page.locator('#discard').click();expect(self.page.locator('#status')).to_have_text('Editor draft discarded; latest saved revision loaded.')
    def test_stale_save_retains_editor_and_private_history(self):
        self.load();self.file('src/sample.py');old=app.project('sample-project');app.edit(r.encode(dict(project_id='sample-project',expected_sha256=old['sha256'],path='src/sample.py',content='other = 1\n',operation='save')));self.page.locator('#editor').fill('my_draft = 2\n');self.page.locator('#save').click();expect(self.page.locator('#status')).to_have_text('PROJECT_REVISION_CONFLICT');expect(self.page.locator('#editor')).to_have_value('my_draft = 2\n');self.assertEqual(len(app.history('sample-project')['versions']),2)
    def test_invalid_python_diagnostic_and_approval_refusal(self):
        self.load();self.file('src/sample.py');self.save('def broken(:\n');self.validate();expect(self.page.locator('#validation')).to_contain_text('PYTHON_SYNTAX_INVALID');self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRES_PASSING_CHECKS');self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('APPROVAL_REQUIRED')
    def test_add_delete_confirmation_and_saved_comparison(self):
        self.load();self.page.locator('#path').fill('notes/new.txt');self.save('fictional note\n');self.page.locator('#delete').click();expect(self.page.locator('#confirm-delete')).to_be_visible();self.page.locator('#confirm-delete').click();expect(self.page.locator('#status')).to_have_text('File deleted in a new immutable revision.');self.page.locator('#left').select_option('1');self.page.locator('#right').select_option('2');self.page.locator('#compare').click();expect(self.page.locator('#diff')).to_contain_text('"status": "added"');self.assertEqual(len(app.history('sample-project')['versions']),3)
    def test_literal_untrusted_source_never_runs_or_inserts_markup(self):
        self.load();self.page.locator('#path').fill('web/sample.html');text='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1"><script>window.sampleExecuted=1</script>';self.save(text);self.validate();expect(self.page.locator('#editor')).to_have_value(text);self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'));expect(self.page.locator('#validation')).to_contain_text('NOT_CHECKED')
    def test_unsafe_path_refused_without_losing_draft(self):
        self.load();self.page.locator('#path').fill('../outside.py');self.page.locator('#editor').fill('value = 1\n');self.page.locator('#save').click();expect(self.page.locator('#status')).to_have_text('SOURCE_PATH_INVALID');expect(self.page.locator('#path')).to_have_value('../outside.py');self.assertEqual(len(app.history('sample-project')['versions']),1)
    def test_repeated_validation_resets_review_and_requires_export_approval(self):
        self.load();first=self.validate();self.approve();second=self.validate();self.assertNotEqual(first,second);expect(self.page.locator('#review-status')).to_have_value('pending');expect(self.page.locator('#quality')).not_to_be_checked();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('APPROVAL_REQUIRED')
    def test_stale_review_keeps_note_and_reports_conflict(self):
        self.load();identifier=self.validate();record=app.artifact(identifier);app.review(r.encode(dict(artifact_id=identifier,artifact_sha256=record['artifact_sha256'],expected_version=0,status='pending',actor='sample_reviewer',note='Saved elsewhere',checks=dict(quality=False,privacy=False,rights=False,context=False))));self.page.locator('#note').fill('My unsaved note');self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('REVIEW_VERSION_CONFLICT');expect(self.page.locator('#note')).to_have_value('My unsaved note')
    def test_historical_fork_and_database_backup(self):
        self.load();self.file('src/sample.py');self.save('value = 5\n');self.page.locator('#versions').select_option('1');expect(self.page.locator('#versions')).to_have_value('1');self.page.locator('#fork-id').fill('sample-fork');self.page.locator('#fork').click();expect(self.page.locator('#status')).to_have_text('Saved revision forked into a separate private project.');self.assertEqual(app.project('sample-fork')['definition']['files'],app.project('sample-project',1)['definition']['files']);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('Private database backup created and schema verified.')
    def test_xml_entities_and_duplicate_json_are_reported(self):
        self.load();self.file('reports/sample.xml');self.save('<!DOCTYPE x [<!ENTITY y "sample">]><x>&y;</x>');self.file('config/sample.json');self.save('{"n":1,"n":2}');self.validate();expect(self.page.locator('#validation')).to_contain_text('XML_DECLARATION_REFUSED');expect(self.page.locator('#validation')).to_contain_text('JSON_DUPLICATE_KEY')
    def test_cancel_button_reaps_actual_owned_stalled_child(self):
        self.load();original=subprocess.Popen
        with mock.patch.object(jobs.subprocess,'Popen',side_effect=lambda *args,**kwargs:original([sys.executable,'-I','-S','-B','-c','import time;time.sleep(30)'],stdin=kwargs['stdin'],stdout=kwargs['stdout'],stderr=kwargs['stderr'],cwd=kwargs['cwd'])):
            self.page.locator('#validate').click();expect(self.page.locator('#cancel')).to_be_enabled();self.page.wait_for_function('document.querySelector("#status").textContent.includes("Validation worker running")');self.page.locator('#cancel').click();expect(self.page.locator('#status')).to_have_text('Validation finished: cancelled. New artifact is pending review.')
        with jobs.LOCK:children=[child for job in jobs.JOBS.values() for child in job['control'].children]
        self.assertEqual(len(children),1);self.assertIsNotNone(children[0].poll());expect(self.page.locator('#cancel')).to_be_disabled()
    def test_historical_validation_refused_without_changing_saved_selection(self):
        self.load();self.file('src/sample.py');self.save('value = 8\n');self.page.locator('#versions').select_option('1');self.page.locator('#validate').click();expect(self.page.locator('#status')).to_have_text('PROJECT_REVISION_CONFLICT');expect(self.page.locator('#versions')).to_have_value('1');self.assertEqual(app.artifacts()['artifacts'],[])
    def test_failed_history_fetch_does_not_rebind_editor_to_another_project(self):
        self.load();self.file('src/sample.py');self.page.route('**/api/history?*',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"FICTIONAL_HISTORY_FAILURE"}'));self.page.locator('#fork-id').fill('sample-fork');self.page.locator('#fork').click();expect(self.page.locator('#status')).to_have_text('FICTIONAL_HISTORY_FAILURE');expect(self.page.locator('#projects')).to_have_value('sample-project');expect(self.page.locator('#identity')).to_contain_text('"project_id": "sample-project"');self.page.unroute('**/api/history?*');self.save('value = 17\n');self.assertEqual(app.project('sample-project')['version'],2);self.assertEqual(app.project('sample-fork')['version'],1)
    def test_narrow_keyboard_edit_and_validation(self):
        self.page.set_viewport_size({'width':390,'height':844});self.load();self.file('src/sample.py');self.page.locator('#editor').focus();self.page.keyboard.press('ControlOrMeta+A');self.page.keyboard.insert_text('value = 9\n');self.page.locator('#save').click();expect(self.page.locator('#status')).to_have_text('File saved in immutable project history. No code executed.');self.validate();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)


if __name__=='__main__':unittest.main()
