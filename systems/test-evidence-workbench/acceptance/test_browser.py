"""Real Chromium case/trust/run/evidence workflows with fictional scripts only."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from evidence import application as app,jobs,runtime as r,web


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
            path=Path(destination);path.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(path/(self._testMethodName+'.png')),full_page=True)
    def load(self):
        self.page.locator('#example').click();expect(self.page.locator('#status')).to_have_text('Fictional cases loaded into import draft. No code executed.');self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('Cases imported. Execution trust is separate; no code ran.')
    def choose(self,identifier):self.page.locator('#cases').select_option(identifier);expect(self.page.locator('#case-id')).to_have_value(identifier)
    def save(self):self.page.locator('#save-case').click();expect(self.page.locator('#status')).to_have_text('Immutable case saved. New revisions require execution trust.')
    def trust(self):
        for key in ('code_reviewed','authority','input_reviewed','effects_reviewed'):self.page.locator('#'+key).check()
        self.page.locator('#trust').click();expect(self.page.locator('#status')).to_have_text('Execution trust saved. No code ran.')
    def plan(self,identifiers):
        self.page.locator('#suite-cases').select_option(identifiers);self.page.locator('#build-plan').click();expect(self.page.locator('#status')).to_have_text('Pinned plan prepared. Run is a separate action.')
    def run_plan(self,status='completed'):
        self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('Evidence saved: '+status+'. Review is pending.');return self.page.locator('#artifacts').input_value()
    def approve(self):
        self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('Evidence review saved. Check verdicts are unchanged.')
    def trust_request(self,record,version=0):return dict(case_id=record['definition']['case_id'],case_sha256=record['sha256'],expected_version=version,status='approved',actor='sample_operator',note='Fictional trust',checks=dict(code_reviewed=True,authority=True,input_reviewed=True,effects_reviewed=True))
    def test_complete_trust_run_review_export_workflow(self):
        self.load();self.assertEqual(list((self.root/'runs').iterdir()),[]);self.trust();self.assertEqual(list((self.root/'runs').iterdir()),[]);self.plan(['sample-total']);identifier=self.run_plan();expect(self.page.locator('#summary')).to_contain_text('"matched": 1');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Evidence exported inside the private workspace. Review before sharing.');receipt=json.loads(self.page.locator('#receipt').inner_text());self.assertTrue((self.root/receipt['directory']/'manifest.json').exists());self.assertEqual(app.artifact(identifier)['payload']['result']['matched'],1)
    def test_untrusted_plan_is_refused_before_execution(self):
        self.load();record=app.case('sample-total');self.page.locator('#plan').fill(json.dumps(dict(cases=[dict(case_id='sample-total',expected_sha256=record['sha256'],trust_version=1)])));self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('EXECUTION_TRUST_REQUIRED');self.assertEqual(app.artifacts()['artifacts'],[]);self.assertEqual(list((self.root/'runs').iterdir()),[])
    def test_trust_requires_all_four_assertions(self):
        self.load();self.page.locator('#trust').click();expect(self.page.locator('#status')).to_have_text('TRUST_CHECKS_REQUIRED');self.assertEqual(app.case('sample-total')['trust']['status'],'pending')
    def test_saved_revision_resets_trust_and_stale_plan_refuses(self):
        self.load();self.trust();self.plan(['sample-total']);old=app.case('sample-total');app.save_case(r.encode(dict(definition={**old['definition'],'title':'Changed elsewhere'},expected_sha256=old['sha256'])));self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('CASE_REVISION_CONFLICT');self.assertEqual(app.case('sample-total')['trust']['status'],'pending');self.assertEqual(list((self.root/'runs').iterdir()),[])
    def test_dirty_case_refuses_switch_trust_and_run(self):
        self.load();self.page.locator('#script').fill('print("{}")\n');self.page.locator('#cases').select_option('sample-nonzero');expect(self.page.locator('#status')).to_have_text('CASE_DRAFT_UNSAVED');expect(self.page.locator('#cases')).to_have_value('sample-total');self.page.locator('#trust').click();expect(self.page.locator('#status')).to_have_text('CASE_DRAFT_UNSAVED');expect(self.page.locator('#script')).to_have_value('print("{}")\n');self.page.locator('#discard').click();expect(self.page.locator('#status')).to_have_text('Case draft discarded; saved source was not changed.')
    def test_mismatch_evidence_approval_preserves_failed_verdict(self):
        self.load();self.choose('sample-mismatch');self.trust();self.plan(['sample-mismatch']);identifier=self.run_plan();expect(self.page.locator('#case-result')).to_contain_text('"passed": false');self.approve();self.assertEqual(app.artifact(identifier)['payload']['result']['unmatched'],1);self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Evidence exported inside the private workspace. Review before sharing.');self.assertEqual(json.loads(self.page.locator('#receipt').inner_text())['manifest']['unmatched'],1)
    def test_timeout_and_expected_nonzero_are_distinct_verdicts(self):
        self.load();self.choose('sample-nonzero');self.trust();self.choose('sample-timeout');self.trust();self.plan(['sample-nonzero','sample-timeout']);self.run_plan();self.page.locator('#result-cases').select_option('sample-nonzero');expect(self.page.locator('#case-result')).to_contain_text('"exit_code": 3');expect(self.page.locator('#case-result')).to_contain_text('"passed": true');self.page.locator('#result-cases').select_option('sample-timeout');expect(self.page.locator('#case-result')).to_contain_text('"status": "timeout"')
    def test_actual_cancel_reaps_child_and_partial_evidence_cannot_be_approved(self):
        self.load();self.choose('sample-timeout');self.page.locator('#timeout').fill('5000');self.save();self.trust();self.plan(['sample-timeout']);self.page.locator('#run').click();expect(self.page.locator('#cancel')).to_be_enabled();deadline=time.monotonic()+5;children=[]
        while time.monotonic()<deadline:
            with jobs.LOCK:children=[child for job in jobs.JOBS.values() for child in job['control'].children]
            if children:break
            time.sleep(.01)
        self.assertEqual(len(children),1);self.page.locator('#cancel').click();expect(self.page.locator('#status')).to_have_text('Evidence saved: cancelled. Review is pending.');self.assertIsNotNone(children[0].poll());self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRES_COMPLETE_EVIDENCE')
    def test_stdout_overflow_is_visible(self):
        self.load();self.page.locator('#script').fill('import sys\nsys.stdout.buffer.write(b"x" * 1000000)\n');self.save();self.trust();self.plan(['sample-total']);self.run_plan();expect(self.page.locator('#case-result')).to_contain_text('"status": "output_limited"');expect(self.page.locator('#case-result')).to_contain_text('"truncated": true')
    def test_untrusted_output_is_literal_text_and_no_external_request_occurs(self):
        self.load();text='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';self.page.locator('#script').fill('import json\nprint(json.dumps({"html": '+repr(text)+'}))\n');self.page.locator('#expected').fill(json.dumps({'html':text}));self.save();self.trust();self.plan(['sample-total']);self.run_plan();expect(self.page.locator('#case-result')).to_contain_text('<img');self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'))
    def test_stale_trust_save_retains_private_note(self):
        self.load();record=app.case('sample-total');app.trust(r.encode(self.trust_request(record)));self.page.locator('#trust-note').fill('Keep this fictional note')
        for key in ('code_reviewed','authority','input_reviewed','effects_reviewed'):self.page.locator('#'+key).check()
        self.page.locator('#trust').click();expect(self.page.locator('#status')).to_have_text('TRUST_VERSION_CONFLICT');expect(self.page.locator('#trust-note')).to_have_value('Keep this fictional note')
    def test_stale_evidence_review_retains_note(self):
        self.load();self.trust();self.plan(['sample-total']);identifier=self.run_plan();record=app.artifact(identifier);app.review(r.encode(dict(artifact_id=identifier,artifact_sha256=record['artifact_sha256'],expected_version=0,status='pending',actor='sample_reviewer',note='Saved elsewhere',checks=dict(quality=False,privacy=False,rights=False,context=False))));self.page.locator('#note').fill('Keep my review note');self.page.locator('#review').click();expect(self.page.locator('#status')).to_have_text('REVIEW_VERSION_CONFLICT');expect(self.page.locator('#note')).to_have_value('Keep my review note')
    def test_identical_rerun_has_fresh_review_comparison_and_backup(self):
        self.load();self.trust();self.plan(['sample-total']);first=self.run_plan();self.approve();second=self.run_plan();self.assertNotEqual(first,second);expect(self.page.locator('#review-status')).to_have_value('pending');expect(self.page.locator('#quality')).not_to_be_checked();self.page.locator('#compare').click();expect(self.page.locator('#comparison')).to_contain_text('"same_case_revision": true');self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('Private database backup created and schema verified.')
    def test_failed_history_fetch_does_not_rebind_case_editor(self):
        self.load();self.page.route('**/api/history?*',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"FICTIONAL_HISTORY_FAILURE"}'));self.page.locator('#cases').select_option('sample-nonzero');expect(self.page.locator('#status')).to_have_text('FICTIONAL_HISTORY_FAILURE');expect(self.page.locator('#case-id')).to_have_value('sample-total');expect(self.page.locator('#cases')).to_have_value('sample-total');self.page.unroute('**/api/history?*');self.page.locator('#title').fill('Changed original selection');self.save();self.assertEqual(app.case('sample-total')['version'],2);self.assertEqual(app.case('sample-nonzero')['version'],1)
    def test_narrow_keyboard_edit_trust_and_run(self):
        self.page.set_viewport_size({'width':390,'height':844});self.load();self.page.locator('#script').focus();self.page.keyboard.press('ControlOrMeta+A');self.page.keyboard.insert_text('print(\'{"total":8}\')\n');self.save();self.trust();self.plan(['sample-total']);self.run_plan();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
    def test_editing_draft_during_run_does_not_change_captured_case(self):
        self.load();self.choose('sample-timeout');self.trust();self.plan(['sample-timeout']);old=app.case('sample-timeout')['definition']['script'];self.page.locator('#run').click();expect(self.page.locator('#cancel')).to_be_enabled();draft='print("{}")\n';self.page.locator('#script').fill(draft);expect(self.page.locator('#status')).to_have_text('Evidence saved: completed. Review is pending.');expect(self.page.locator('#script')).to_have_value(draft);self.assertEqual(app.case('sample-timeout')['definition']['script'],old)


if __name__=='__main__':unittest.main()
