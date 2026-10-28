"""Real Chromium template/review/semantic preview and private download workflows."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from documents import application as app,artifacts as a,runtime as r,web
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(accept_downloads=True);self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append((request.method,request.url)));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Save the fictional template to begin.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def save(self):
        self.page.locator('#save-template').click();expect(self.page.locator('#status')).to_have_text('New template revision saved. Earlier revisions remain unchanged.');return app.overview()['templates'][-1]
    def preview(self):
        self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('Pinned semantic preview saved. Review content, sections, tables and totals.');return app.overview()['previews'][-1]
    def approve(self):
        for name in ('quality','privacy','rights','context'):self.page.locator('#'+name).check()
    def build(self):
        self.approve();self.page.locator('#build').click();expect(self.page.locator('#status')).to_have_text('Fresh DOCX built and its eight XML parts, values and neutral properties verified.');return app.overview()['builds'][-1]
    def refresh(self):self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_have_text('Journal reloaded. Inspect a saved preview before building.')
    def inspect(self):self.page.locator('#inspect-preview').click();expect(self.page.locator('#status')).to_have_text('Saved preview and source revision pins verified. Pixel layout is not simulated here.')
    def capture(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            folder=Path(evidence);folder.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(folder/name),full_page=True)
    def test_complete_revision_preview_build_download_export_and_backup(self):
        self.save();preview=self.preview();expect(self.page.locator('#semantic')).to_contain_text('Service handoff for Sample instrument');expect(self.page.locator('#semantic')).to_contain_text('Total quantity 7');self.assertEqual(self.page.locator('#semantic table tbody tr').count(),2);built=self.build();self.page.locator('#inspect-build').click();expect(self.page.locator('#status')).to_have_text('Registered DOCX bytes, XML parts and retained preview verified.');self.assertEqual(json.loads(self.page.locator('#inspection').inner_text())['inspection']['external_relationships'],0)
        with self.page.expect_download() as info:self.page.locator('#download').click()
        download=info.value;self.assertEqual(download.suggested_filename,'generated-document.docx');raw=Path(download.path()).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),built['document_sha256']);self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Reviewed private handoff created.');handoff=json.loads(self.page.locator('#handoff').inner_text());self.assertFalse(handoff['manifest']['public_release_authorized']);self.assertEqual(len(handoff['manifest']['files']),8);self.page.locator('#backup-index').click();expect(self.page.locator('#status')).to_contain_text('Private index backup verified.');backup=json.loads(self.page.locator('#handoff').inner_text());self.assertTrue(backup['contains_input_values']);self.assertFalse(backup['includes_document_files']);self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.capture('documents-wide.png')
    def test_optional_sections_and_required_section_control(self):
        self.save();required=self.page.get_by_role('checkbox',name='Summary',exact=True);expect(required).to_be_disabled();expect(required).to_be_checked();self.page.get_by_role('checkbox',name='Review notes',exact=True).uncheck();self.preview();expect(self.page.locator('#preview-summary')).to_contain_text('2 sections');expect(self.page.locator('#semantic')).not_to_contain_text('Review notes')
    def test_typed_value_edit_changes_quantity_summary(self):
        self.save();values=json.loads(self.page.locator('#values').input_value());values['items'][0]['quantity']=8;self.page.locator('#values').fill(json.dumps(values));self.preview();expect(self.page.locator('#semantic')).to_contain_text('Total quantity 12')
    def test_template_revision_editor_parent_and_comparison(self):
        first=self.save();template=json.loads(self.page.locator('#template').input_value());template['label']='Fictional revision two';template['sections'][1]['title']='Requested quantities';self.page.locator('#template').fill(json.dumps(template));expect(self.page.locator('#preview')).to_be_disabled();second=self.save();self.assertEqual(second['parent_id'],first['template_id']);self.page.locator('#compare-template').select_option(first['template_id']);self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Template revisions compared without changing either revision.');self.assertEqual(json.loads(self.page.locator('#comparison').inner_text())['sections']['changed'],['items'])
    def test_review_required_for_build(self):
        self.save();self.preview();self.page.locator('#build').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.assertEqual(app.overview()['builds'],[]);self.assertEqual(len(app.overview()['jobs']),2)
    def test_value_edit_invalidates_inspected_preview_and_review(self):
        self.save();self.preview();self.approve();self.page.locator('#values').fill(self.page.locator('#values').input_value()+' ');expect(self.page.locator('#quality')).not_to_be_checked();expect(self.page.locator('#build')).to_be_disabled();self.assertEqual(len(app.overview()['previews']),1)
    def test_bad_json_and_expression_placeholder_refused(self):
        self.page.locator('#template').fill('not JSON');self.page.locator('#save-template').click();expect(self.page.locator('#status')).to_have_text('FORM_JSON_INVALID');self.refresh();template=app.example()['template'];template['title']='{{project.__class__}}';self.page.locator('#template').fill(json.dumps(template));self.page.locator('#save-template').click();expect(self.page.locator('#status')).to_have_text('PLACEHOLDER_INVALID');self.assertEqual(app.overview()['templates'],[])
    def test_boolean_quantity_is_refused_without_new_preview(self):
        self.save();values=json.loads(self.page.locator('#values').input_value());values['items'][0]['quantity']=True;self.page.locator('#values').fill(json.dumps(values));self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('INTEGER_INVALID');self.assertEqual(app.overview()['previews'],[])
    def test_stale_head_keeps_editor_and_reason_drafts(self):
        app.save_template(r.encode(dict(expected_head=app.overview()['head'],actor='sample_other',reason='Competing fictional revision',request=dict(parent_id=None,template=app.example()['template']))));draft=self.page.locator('#template').input_value();self.page.locator('#reason').fill('Retain this fictional draft');self.page.locator('#save-template').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#reason')).to_have_value('Retain this fictional draft');expect(self.page.locator('#template')).to_have_value(draft)
    def test_historical_saved_preview_can_build_after_editor_revision(self):
        self.save();first=self.preview();template=json.loads(self.page.locator('#template').input_value());template['title']='Different fictional title';self.page.locator('#template').fill(json.dumps(template));self.save();self.page.locator('#previews').select_option(first['preview_id']);self.inspect();self.build();self.assertEqual(app.inspect_build(app.overview()['builds'][-1]['build_id'])['preview']['title'],'Service handoff for Sample instrument')
    def test_partial_build_failure_retains_output_and_reason(self):
        self.save();self.preview();self.page.locator('#reason').fill('Keep my fictional evidence');self.approve()
        def partial(identifier,request,state):
            folder=self.root/'builds'/identifier;r.mkdir(folder);r.write_new(folder/'document.docx',b'fictional partial');raise OSError('withheld detail')
        with mock.patch.object(a,'write_build',partial):self.page.locator('#build').click();expect(self.page.locator('#status')).to_have_text('OPERATION_REFUSED')
        expect(self.page.locator('#reason')).to_have_value('Keep my fictional evidence');job=app.overview()['jobs'][-1];self.assertTrue((self.root/'builds'/job['job_id']/'document.docx').is_file());self.assertEqual(app.overview()['builds'],[])
    def test_preview_tampering_refused_before_build(self):
        self.save();preview=self.preview();(self.root/preview['target']/'preview.json').write_bytes(b'{}');self.approve();self.page.locator('#build').click();expect(self.page.locator('#status')).to_have_text('PREVIEW_HASH_MISMATCH');self.assertEqual(app.overview()['builds'],[])
    def test_document_tampering_refuses_inspection_and_download(self):
        self.save();self.preview();built=self.build();(self.root/built['target']/'document.docx').write_bytes(b'fictional corruption');self.page.locator('#inspect-build').click();expect(self.page.locator('#status')).to_have_text('DOCUMENT_HASH_MISMATCH');self.refresh();self.page.locator('#download').click();expect(self.page.locator('#status')).to_have_text('DOCUMENT_HASH_MISMATCH')
    def test_literal_markup_appears_as_text_without_external_request(self):
        self.save();values=json.loads(self.page.locator('#values').input_value());values['summary']='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';self.page.locator('#values').fill(json.dumps(values));self.preview();expect(self.page.locator('#semantic')).to_contain_text('example.invalid');self.assertEqual(self.page.locator('#semantic img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'))
    def test_lost_write_response_is_not_automatically_retried(self):
        def lost(route):route.fetch();route.abort('failed')
        self.page.route('**/api/template',lost);self.page.locator('#save-template').click();expect(self.page.locator('#status')).to_have_text('WRITE_RESPONSE_UNCERTAIN_RELOAD_REQUIRED');self.assertEqual(len(app.overview()['templates']),1);self.assertEqual(sum(method=='POST' and url.endswith('/api/template') for method,url in self.requests),1);self.page.unroute('**/api/template');self.refresh();expect(self.page.locator('#template-count')).to_have_text('1')
    def test_failed_initial_read_disables_writes(self):
        self.page.route('**/api/overview',lambda route:route.fulfill(status=400,json=dict(error='FICTIONAL_READ_REFUSED')));self.page.reload();expect(self.page.locator('#status')).to_have_text('FICTIONAL_READ_REFUSED');expect(self.page.locator('#save-template')).to_be_disabled();self.page.unroute('**/api/overview');self.refresh();expect(self.page.locator('#save-template')).to_be_enabled()
    def test_export_requires_review_and_matching_build(self):
        self.save();self.preview();self.build();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.refresh();self.preview();self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('BUILD_PREVIEW_MISMATCH')
    def test_selection_and_journal_changes_reset_review(self):
        self.save();first=self.preview();self.approve();self.page.get_by_role('checkbox',name='Review notes',exact=True).uncheck();expect(self.page.locator('#privacy')).not_to_be_checked();self.preview();self.approve();self.page.locator('#previews').select_option(first['preview_id']);expect(self.page.locator('#quality')).not_to_be_checked();expect(self.page.locator('#build')).to_be_disabled()
    def test_history_and_owned_server_shutdown(self):
        self.save();self.page.locator('#history-button').click();expect(self.page.locator('#status')).to_have_text('Typed hash-linked journal replay verified.');self.assertEqual(len(json.loads(self.page.locator('#history').inner_text())['events']),2);self.page.locator('#shutdown').click();expect(self.page.locator('#status')).to_contain_text('Local server stopping.');self.thread.join(timeout=5);self.assertFalse(self.thread.is_alive())
    def test_narrow_semantic_table_layout_and_keyboard(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.save();self.preview();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.page.locator('#actor').focus();self.page.keyboard.press('Tab');expect(self.page.locator('#reason')).to_be_focused();self.capture('documents-narrow.png')

if __name__=='__main__':unittest.main()
