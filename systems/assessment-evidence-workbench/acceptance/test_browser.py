"""Actual Chromium against fictional private assessment stores."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from assessment import application as app,runtime as r,web

class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.fixture=r.decode((APP/'examples/sample-assessment.json').read_bytes());self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append(request.url));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. No target or scanner execution available.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def create(self):self.page.locator('#example').click();expect(self.page.locator('#status')).to_contain_text('Fictional assessment created.')
    def act(self,index):
        command=self.fixture['commands'][index];self.page.locator('#operation').select_option(command['operation']);self.page.locator('#template').click();expect(self.page.locator('#status')).to_contain_text('Template loaded;');draft=json.loads(self.page.locator('#editor').input_value());draft['command']=command;self.page.locator('#editor').fill(json.dumps(draft));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ')
    def steps(self,count=6):
        self.create()
        for index in range(count):self.act(index)
    def test_actual_manual_workflow_and_reviewed_resolution(self):
        self.steps();expect(self.page.locator('#findings')).to_contain_text('Resolved');expect(self.page.locator('#retests')).to_contain_text('"review_state": "accept"');self.assertFalse(app.assessment('sample_assessment')['execution_performed']);self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests))
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(directory/'assessment-workflow.png'),full_page=True)
    def test_legacy_import_closure_claim_is_separate_unverified(self):
        self.create();self.act(6);expect(self.page.locator('#legacy')).to_contain_text('"outcomes_verified": false');expect(self.page.locator('#legacy')).to_contain_text('closure_claimed');self.assertEqual(self.page.locator('#findings tr').count(),0)
    def test_error_keeps_exact_json_draft(self):
        self.create();draft='{"invented":"draft"}';self.page.locator('#editor').fill(draft);self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('FIELDS_INVALID');expect(self.page.locator('#editor')).to_have_value(draft);self.assertEqual(app.assessment('sample_assessment')['version'],1)
    def test_stale_command_keeps_binding_and_draft(self):
        self.create();draft=self.page.locator('#editor').input_value();current=app.assessment('sample_assessment');app.act(r.encode(dict(assessment_id='sample_assessment',expected_sha256=current['sha256'],command=self.fixture['commands'][0])));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('ASSESSMENT_REVISION_CONFLICT');expect(self.page.locator('#editor')).to_have_value(draft)
    def test_historical_mutation_and_export_refused(self):
        self.steps(1);self.page.locator('#versions').select_option('1');expect(self.page.locator('#status')).to_contain_text('Historical revision');self.page.locator('#template').click();expect(self.page.locator('#status')).to_contain_text('Template loaded;');self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('ASSESSMENT_REVISION_CONFLICT');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('ASSESSMENT_REVISION_CONFLICT')
    def approve(self):
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
    def test_export_checks_manifest_and_private_backup(self):
        self.steps();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('EXPORT_REVIEW_REQUIRED');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Reviewed private handoff created.');result=json.loads(self.page.locator('#handoff').inner_text());self.assertFalse(result['manifest']['public_release_authorized']);self.assertTrue((self.root/result['directory']/'receipts/sample_original.bin').is_file());self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('Private database backup created and history replay verified.')
    def test_review_checkboxes_reset_on_saved_revision_change(self):
        self.create();self.approve();self.act(0)
        for key in ('quality','privacy','rights','context'):expect(self.page.locator('#'+key)).not_to_be_checked()
    def test_literal_markup_stays_text_without_external_requests(self):
        self.steps(2);command=json.loads(json.dumps(self.fixture['commands'][2]));command['data']['title']='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';current=app.assessment('sample_assessment');app.act(r.encode(dict(assessment_id='sample_assessment',expected_sha256=current['sha256'],command=command)));self.page.locator('#refresh').click();expect(self.page.locator('#findings')).to_contain_text('<img');self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'));self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests))
    def test_upload_opaque_bytes_omits_original_filename(self):
        self.create();self.page.locator('#receipt').set_input_files(dict(name='fictional-private-name.bin',mimeType='application/octet-stream',buffer=b'Fictional inert opaque bytes\x00'));self.page.locator('#attach').click();expect(self.page.locator('#status')).to_contain_text('Original filename was not recorded.');draft=self.page.locator('#editor').input_value();self.assertNotIn('fictional-private-name',draft);self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ');self.assertEqual(app.assessment('sample_assessment')['document']['submissions'][0]['receipt']['bytes'],len(b'Fictional inert opaque bytes\x00'))
    def test_compare_saved_versions_and_history(self):
        self.steps();self.page.locator('#left').select_option('4');self.page.locator('#right').select_option('7');self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Saved revisions compared.');expect(self.page.locator('#diff')).to_contain_text('"status": "changed"');expect(self.page.locator('#history')).to_contain_text('"command_sha256"')
    def test_failed_history_fetch_preserves_current_binding(self):
        self.create();self.page.route('**/api/history?*',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"FICTIONAL_HISTORY_FAILURE"}'));self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_have_text('FICTIONAL_HISTORY_FAILURE');expect(self.page.locator('#identity')).to_contain_text('sample_assessment');draft=json.loads(self.page.locator('#editor').input_value());self.assertEqual(draft['assessment_id'],'sample_assessment')
    def test_narrow_keyboard_command_and_visual_capture(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.create();self.page.locator('#editor').focus();self.page.keyboard.press('ControlOrMeta+A');draft=json.loads(self.page.locator('#editor').input_value());draft['command']=self.fixture['commands'][0];self.page.keyboard.insert_text(json.dumps(draft));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(directory/'assessment-narrow.png'),full_page=True);self.page.set_viewport_size(dict(width=1280,height=1000));self.page.screenshot(path=str(directory/'assessment-wide.png'),full_page=True)

if __name__=='__main__':unittest.main()
