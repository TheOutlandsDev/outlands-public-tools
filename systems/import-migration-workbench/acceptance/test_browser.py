"""Real Chromium workflows against fictional records and disposable local stores."""
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
from migration import application as app,destination as d,runtime as r,web
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append((request.method,request.url)));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Select fictional inputs and create a preview.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def preview(self):
        self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('Pinned preview saved. Review accepted, rejected, duplicate and conflicting rows.');return app.overview()['plans'][-1]
    def approve(self,rejections=True):
        for name in ('quality','privacy','rights','context'):self.page.locator('#'+name).check()
        if rejections:self.page.locator('#accept-rejections').check()
    def commit(self):
        self.approve();self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('Fresh SQLite store committed after logical readback and byte verification. Existing stores were not changed.');return app.overview()['imports'][-1]
    def refresh(self):self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_have_text('Journal reloaded. Inspect a saved preview before importing.')
    def inspect(self):self.page.locator('#inspect-plan').click();expect(self.page.locator('#status')).to_have_text('Saved preview and byte pin verified. Current input bytes will be rechecked at import.')
    def capture(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(directory/name),full_page=True)
    def test_full_preview_import_verify_private_export_and_backup(self):
        self.preview();out=self.commit();self.page.locator('#inspect-import').click();expect(self.page.locator('#status')).to_have_text('Registered store schema, bytes, normalized values and provenance verified.');records=json.loads(self.page.locator('#records').inner_text());self.assertEqual([v['quantity'] for v in records['records']],[3,7,0]);self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Reviewed private handoff created.');report=json.loads(self.page.locator('#handoff').inner_text());self.assertFalse(report['manifest']['public_release_authorized']);self.assertEqual(len(report['manifest']['files']),7);self.assertTrue((self.root/out['target']/'READY.json').is_file());self.page.locator('#backup-index').click();expect(self.page.locator('#status')).to_contain_text('Metadata index backup verified.');self.assertFalse(json.loads(self.page.locator('#handoff').inner_text())['includes_plan_or_store_bytes']);self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.capture('migration-wide.png')
    def test_mapping_editor_changes_normalized_output(self):
        contract=json.loads(self.page.locator('#contract').input_value());contract['fields'][1]['target']='units';self.page.locator('#contract').fill(json.dumps(contract));self.preview();plan=json.loads(self.page.locator('#plan-details').inner_text())['plan'];self.assertEqual(plan['records'][0]['data']['units'],3);self.assertNotIn('quantity',plan['records'][0]['data'])
    def test_duplicate_provenance_and_rejection_codes_visible(self):
        self.preview();plan=json.loads(self.page.locator('#plan-details').inner_text())['plan'];self.assertEqual(plan['summary']['duplicate_rows'],2);self.assertEqual(plan['summary']['rejected_rows'],2);self.assertEqual(len(plan['records'][0]['provenance']),2);expect(self.page.locator('#pin')).to_contain_text('Reviewed preview SHA-256:');expect(self.page.locator('#preview-summary')).to_have_text('7 input rows · 3 accepted · 2 duplicate extras · 2 rejected · 0 conflicting rows')
    def test_import_requires_all_review_assertions(self):
        self.preview();self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.assertEqual(app.overview()['imports'],[]);self.assertEqual(len(app.overview()['jobs']),1)
    def test_rejected_rows_need_separate_acceptance(self):
        self.preview();self.approve(False);self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('REJECTED_ROWS_REVIEW_REQUIRED');self.assertEqual(app.overview()['imports'],[])
    def test_conflicting_keys_block_import_without_partial_store(self):
        self.page.locator('#sources').fill(json.dumps([dict(path='inbox/orders.csv',format='csv'),dict(path='inbox/conflicts.jsonl',format='jsonl')]));self.preview();expect(self.page.locator('#plan-details')).to_contain_text('"conflict_rows": 3');self.approve();self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('CONFLICTING_KEYS_REQUIRE_NEW_PLAN');self.assertEqual(list((self.root/'stores').iterdir()),[])
    def test_exact_repeat_import_is_refused(self):
        self.preview();self.commit();self.preview();self.approve();self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('EXACT_PLAN_ALREADY_IMPORTED');self.assertEqual(len(app.overview()['imports']),1)
    def test_source_mutation_fails_with_private_attempt_record(self):
        self.preview();(self.root/'inbox/orders.csv').write_bytes(b'changed');self.approve();self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('SOURCE_BYTES_CHANGED');self.assertEqual(app.overview()['jobs'][-1]['status'],'failed');self.refresh();expect(self.page.locator('#failed-count')).to_have_text('1')
    def test_saved_preview_tampering_refused(self):
        plan=self.preview();(self.root/plan['target']/'plan.json').write_bytes(b'{}');self.page.locator('#inspect-plan').click();expect(self.page.locator('#status')).to_have_text('PLAN_HASH_MISMATCH');expect(self.page.locator('#import')).to_be_disabled()
    def test_store_tampering_refused_on_view(self):
        self.preview();out=self.commit();(self.root/out['target']/'data.sqlite3').write_bytes(b'fictional corruption');self.page.locator('#inspect-import').click();expect(self.page.locator('#status')).to_have_text('DESTINATION_HASH_MISMATCH')
    def test_stale_head_preserves_source_and_operator_drafts(self):
        app.plan(r.encode(dict(expected_head=app.overview()['head'],actor='sample_other',reason='Competing fictional preview',request=dict(sources=[dict(path='inbox/orders.csv',format='csv')],contract=app.example()))));self.page.locator('#reason').fill('Unsaved fictional evidence');source=self.page.locator('#sources').input_value();self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#reason')).to_have_value('Unsaved fictional evidence');expect(self.page.locator('#sources')).to_have_value(source);self.assertEqual(len(app.overview()['plans']),1)
    def test_invalid_form_and_outside_selector_do_not_start_jobs(self):
        self.page.locator('#sources').fill('not JSON');self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('FORM_JSON_INVALID');self.refresh();self.page.locator('#sources').fill(json.dumps([dict(path='../outside.csv',format='csv')]));self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('SELECTOR_INVALID');self.assertEqual(app.overview()['jobs'],[])
    def test_review_resets_on_selection_mapping_and_journal_change(self):
        first=self.preview();self.approve();self.page.locator('#contract').fill(self.page.locator('#contract').input_value()+' ');expect(self.page.locator('#quality')).not_to_be_checked();self.approve();self.preview();expect(self.page.locator('#privacy')).not_to_be_checked();self.page.locator('#plans').select_option(first['plan_id']);expect(self.page.locator('#import')).to_be_disabled();self.inspect();self.approve();self.refresh();self.assertTrue(self.page.locator('#import').is_enabled());self.assertTrue(self.page.locator('#quality').is_checked())
    def test_export_is_reviewed_and_mismatched_selection_refused(self):
        self.preview();self.commit();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.refresh();self.preview();self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('IMPORT_PLAN_MISMATCH')
    def test_literal_markup_is_text_and_never_executes(self):
        marker='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';self.page.locator('#actor').fill(marker);self.preview();expect(self.page.locator('#jobs')).to_contain_text('example.invalid');self.assertIsNone(self.page.evaluate('window.sampleExecuted'));self.assertEqual(self.page.locator('img').count(),0)
    def test_partial_store_failure_retains_output_and_reason(self):
        self.preview();self.page.locator('#reason').fill('Retain my fictional draft');self.approve()
        def partial(identifier,result):
            path=self.root/'stores'/identifier;r.mkdir(path);r.write_new(path/'partial.txt',b'fictional partial');raise OSError('withheld local detail')
        with mock.patch.object(d,'create',partial):self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('OPERATION_REFUSED')
        expect(self.page.locator('#reason')).to_have_value('Retain my fictional draft');job=app.overview()['jobs'][-1];self.assertTrue((self.root/'stores'/job['job_id']/'partial.txt').is_file());self.assertEqual(app.overview()['imports'],[])
    def test_lost_write_response_has_no_automatic_retry(self):
        def lost(route):route.fetch();route.abort('failed')
        self.page.route('**/api/plan',lost);self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('WRITE_RESPONSE_UNCERTAIN_RELOAD_REQUIRED');self.assertEqual(len(app.overview()['plans']),1);self.assertEqual(sum(method=='POST' and url.endswith('/api/plan') for method,url in self.requests),1);self.page.unroute('**/api/plan');self.refresh();expect(self.page.locator('#plan-count')).to_have_text('1')
    def test_failed_initial_read_disables_writes(self):
        self.page.route('**/api/overview',lambda route:route.fulfill(status=400,json=dict(error='FICTIONAL_READ_REFUSED')));self.page.reload();expect(self.page.locator('#status')).to_have_text('FICTIONAL_READ_REFUSED');expect(self.page.locator('#preview')).to_be_disabled();self.page.unroute('**/api/overview');self.refresh();expect(self.page.locator('#preview')).to_be_enabled()
    def test_history_and_owned_server_shutdown(self):
        self.preview();self.page.locator('#history-button').click();expect(self.page.locator('#status')).to_have_text('Typed hash-linked journal replay verified.');self.assertEqual(len(json.loads(self.page.locator('#history').inner_text())['events']),2);self.page.locator('#shutdown').click();expect(self.page.locator('#status')).to_contain_text('Local server stopping.');self.thread.join(timeout=5);self.assertFalse(self.thread.is_alive())
    def test_narrow_layout_and_keyboard_access(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.preview();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.page.locator('#actor').focus();self.page.keyboard.press('Tab');expect(self.page.locator('#reason')).to_be_focused();self.capture('migration-narrow.png')

if __name__=='__main__':unittest.main()
