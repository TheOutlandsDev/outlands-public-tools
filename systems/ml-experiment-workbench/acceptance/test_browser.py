"""Real Chromium acceptance for the complete fictional experiment workflow."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from ml_workbench import application as app,fixtures,runtime as r,web


class ExperimentBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
        self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
        self.context=self.browser.new_context(viewport={'width':1440,'height':1050});self.addCleanup(self.context.close);self.external=[];self.errors=[]
        def route(request):
            if request.request.url.startswith(f'http://127.0.0.1:{self.server.server_port}/'):request.continue_()
            else:self.external.append(request.request.url.split(':',1)[0]);request.abort()
        self.context.route('**/*',route);self.page=self.context.new_page();self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.goto(f'http://127.0.0.1:{self.server.server_port}/');expect(self.page.locator('#status')).to_have_text('Ready. Import a fictional dataset to start.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def tearDown(self):
        self.assertEqual(self.external,[]);self.assertEqual(self.errors,[])
        destination=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if destination:
            target=Path(destination);target.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(target/(self._testMethodName+'.png')),full_page=True)
    def import_fixture(self,data=None):
        self.page.locator('#fictional').click();expect(self.page.locator('#status')).to_have_text('Fictional dataset loaded into draft. Import to persist it.')
        if data is not None:self.page.locator('#dataset-json').fill(json.dumps(data))
        self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('Immutable dataset imported. Load its pinned configuration template.');self.page.locator('#template').click();expect(self.page.locator('#status')).to_have_text('Pinned template loaded. Preparation uses training and validation only.')
    def prepare(self,identifier='sample-baseline'):
        self.page.locator('#experiment-id').fill(identifier);self.page.locator('#prepare').click();expect(self.page.locator('#status')).to_have_text('Experiment prepared. Holdout evaluation remains a separate step.')
    def evaluate(self):
        self.page.locator('#evaluate').click();expect(self.page.locator('#status')).to_have_text('Holdout evaluation recorded. Review is pending for this artifact.')
    def review(self):
        self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('Review recorded for this saved artifact.')
    def test_complete_import_train_evaluate_review_export(self):
        self.import_fixture();self.prepare();self.assertIsNone(app.show('sample-baseline')['evaluation']);expect(self.page.locator('#phase')).to_have_text('Prepared. Holdout has not been evaluated.');self.assertEqual(self.page.locator('#weights tbody tr').count(),3);self.assertEqual(self.page.locator('#threshold-chart circle').count(),5);self.evaluate();expect(self.page.locator('#evaluate')).to_be_disabled();self.review();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Approved artifact exported inside the private workspace.');self.assertEqual(json.loads(self.page.locator('#report-output').inner_text())['files'],8);self.assertEqual(app.show('sample-baseline')['review']['status'],'approved');self.assertGreater(self.page.locator('#reliability-chart circle').count(),0)
    def test_future_feature_import_rejected_draft_retained(self):
        data=fixtures.dataset();data['rows'][1]['feature_available_day']['signal']=2;draft=json.dumps(data);self.page.locator('#dataset-json').fill(draft);self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('FEATURE_NOT_AVAILABLE_AT_DECISION; drafts retained.');self.assertEqual(self.page.locator('#dataset-json').input_value(),draft);self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_invalid_chronology_retains_configuration(self):
        self.import_fixture();self.page.locator('#train-end').fill('140');draft=self.page.locator('#configuration-json').input_value();self.page.locator('#prepare').click();expect(self.page.locator('#status')).to_have_text('CHRONOLOGY_INVALID; drafts retained.');self.assertEqual(self.page.locator('#configuration-json').input_value(),draft);self.assertEqual(app.experiments(),dict(experiments=[]))
    def test_immutable_experiment_conflict_and_new_id(self):
        self.import_fixture();self.prepare();self.page.locator('#l2').fill('0.2');draft=self.page.locator('#configuration-json').input_value();self.page.locator('#prepare').click();expect(self.page.locator('#status')).to_have_text('EXPERIMENT_IMMUTABLE; drafts retained.');self.assertEqual(self.page.locator('#configuration-json').input_value(),draft);self.prepare('sample-new');self.assertEqual(len(app.experiments()['experiments']),2)
    def test_review_reset_after_holdout_and_export_gate(self):
        self.import_fixture();self.prepare();self.review();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('EVALUATION_REQUIRED_FOR_EXPORT; drafts retained.');self.evaluate();self.assertEqual(self.page.locator('#review-status').input_value(),'pending');self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('APPROVAL_REQUIRED; drafts retained.')
    def test_stale_review_preserves_note(self):
        self.import_fixture();self.prepare();self.evaluate();record=app.show('sample-baseline');app.review(r.encode(dict(experiment_id='sample-baseline',artifact_sha256=record['artifact_sha256'],expected_version=0,status='pending',actor='sample_other',note='Fictional parallel review',checks=dict(quality=False,privacy=False,rights=False,context=False))))
        self.page.locator('#note').fill('Retain this fictional note');self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('REVIEW_VERSION_CONFLICT; drafts retained.');self.assertEqual(self.page.locator('#note').input_value(),'Retain this fictional note');self.page.locator('#reload').click();expect(self.page.locator('#status')).to_have_text('Saved results and review reloaded.');self.assertEqual(self.page.locator('#note').input_value(),'Fictional parallel review')
    def test_comparison_and_backup(self):
        self.import_fixture();self.prepare();self.evaluate();self.page.locator('#l2').fill('0.2');self.prepare('sample-second');self.evaluate();self.page.locator('#left').select_option('sample-baseline');self.page.locator('#right').select_option('sample-second');self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Comparison calculated with explicit cohort checks.');comparison=json.loads(self.page.locator('#comparison').inner_text());self.assertTrue(comparison['same_test_cohort']);self.assertTrue(comparison['test_comparison_available']);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('Private database backup created.');self.assertIn('database_only',json.loads(self.page.locator('#report-output').inner_text())['scope'])
    def test_narrow_keyboard_form_and_svg(self):
        self.page.set_viewport_size({'width':390,'height':844});self.import_fixture();self.page.locator('#experiment-id').fill('sample-keyboard');self.page.locator('#experiment-id').press('Enter');expect(self.page.locator('#status')).to_have_text('Experiment prepared. Holdout evaluation remains a separate step.');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.assertEqual(self.page.locator('#threshold-chart').get_attribute('viewBox'),'0 0 500 220');self.evaluate()
    def test_untrusted_title_is_literal_text(self):
        data=fixtures.dataset();data['title']='<img src="https://example.invalid/test" onerror="throw Error(1)">';self.import_fixture(data);expect(self.page.locator('#dataset-summary')).to_contain_text(data['title']);self.assertEqual(self.page.locator('img').count(),0);self.prepare()
    def test_json_draft_application_and_pin_rejection(self):
        self.import_fixture();self.page.locator('summary').click();value=json.loads(self.page.locator('#configuration-json').input_value());value['dataset_sha256']='0'*64;draft=json.dumps(value);self.page.locator('#configuration-json').fill(draft);self.page.locator('#apply-json').click();expect(self.page.locator('#status')).to_have_text('Configuration JSON applied to form.');self.page.locator('#prepare').click();expect(self.page.locator('#status')).to_have_text('DATASET_PIN_MISMATCH; drafts retained.');self.assertEqual(json.loads(self.page.locator('#configuration-json').input_value())['dataset_sha256'],'0'*64)


if __name__=='__main__':unittest.main()
