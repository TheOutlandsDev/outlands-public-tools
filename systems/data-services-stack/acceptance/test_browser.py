"""Real Chromium workflows; fresh journals, fictional records and fake attempts only."""
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
from data_services.contracts import canonical,decode,digest,fictional_configuration,fictional_input
from data_services.service import Stack
from data_services.workbench import Workbench
from data_services.web import LocalServer
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name);self.root=self.parent/'workspace';Stack.initialize(self.root);self.app=Stack(self.root);self.addCleanup(lambda:self.app.close());self.controller=Workbench(self.app,self.parent/'reports');self.addCleanup(self.controller.close);self.server=LocalServer(('127.0.0.1',0),self.controller);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport=dict(width=1360,height=1000));self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.errors=[];self.page.on('request',lambda req:self.requests.append((req.method,req.url)));self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private journal ready. Nothing configured or dispatched automatically.')
    def tearDown(self):self.assertEqual(self.errors,[])
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def configure(self,csv=False):
        self.page.locator('#example-config').click();expect(self.page.locator('#status')).to_have_text('Invented configuration loaded. Save explicitly.')
        if csv:
            value=json.loads(self.page.locator('#configuration').input_value());value['jobs'][0]['input_format']='csv';self.page.locator('#configuration').fill(json.dumps(value))
        self.page.locator('#configure').click();expect(self.page.locator('#status')).to_have_text('Configuration saved. Existing runs retain their original job snapshots.')
    def preview(self,csv=False):
        self.page.locator('#sample-csv' if csv else '#sample-jsonl').click();expect(self.page.locator('#status')).to_have_text('Invented input loaded. Preview before running.');self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('Preview clean and pinned. No run or notification created.')
    def run_job(self,key='sample_run'):
        self.page.locator('#run-key').fill(key);self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('Run saved. One durable notification is queued; no transport was called.')
    def ready(self):self.configure();self.preview();self.run_job()
    def queue_tab(self):self.page.locator('[data-tab=queue]').click();expect(self.page.locator('#status')).to_have_text('Ready')
    def dispatch(self,outcome='accept',tick='0'):
        self.page.locator('#outcome').select_option(outcome);self.page.locator('#tick').fill(tick);self.page.locator('#dispatch').click();expect(self.page.locator('#status')).to_have_text('Simulated interruption retained for review. No replay.' if outcome=='interrupt' else 'Fictional dispatch recorded. Adapter acceptance is not verified delivery.')
    def review(self):
        self.page.locator('#note').fill('Invented independent review of baseline limits')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
    def export(self):
        self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Checked private report created: ');return json.loads(self.page.locator('#report-result').inner_text())
    def image(self,name):
        value=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if value:
            root=Path(value);root.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(root/name),full_page=True)
    def test_complete_configuration_preview_run_forecast_report_and_fake_delivery(self):
        self.ready();expect(self.page.locator('#metrics')).to_have_text('Accepted 6 · duplicates 0 · holdout predictions 3 · MAE 4 · RMSE 4');self.assertEqual(self.page.locator('#forecast-points tr').count(),3);self.assertEqual(self.page.locator('#chart circle').count(),3);self.review();report=self.export();folder=self.parent/'reports'/report['directory']
        for name,item in report['manifest']['files'].items():self.assertEqual(item,dict(bytes=len((folder/name).read_bytes()),sha256=digest((folder/name).read_bytes())))
        run=decode((folder/'run.json').read_bytes());self.assertEqual(run['result']['forecast'],[dict(series='sample',period=i,value=10) for i in (6,7,8)]);self.assertFalse(report['manifest']['public_release_authorized']);self.image('services-runs-wide.png');self.queue_tab();self.dispatch('retry');expect(self.page.locator('#queue-rows')).to_contain_text('RETRY_SCHEDULED');self.dispatch(tick='1');expect(self.page.locator('#queue-rows')).to_contain_text('ACCEPTED');self.page.locator('#delivery-assertion').check();self.page.locator('#delivery').click();expect(self.page.locator('#status')).to_have_text('Caller assertion recorded. Real delivery remains unverified.');expect(self.page.locator('#queue-rows')).to_contain_text('DELIVERY_REPORTED');self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.image('services-queue-wide.png')
    def test_clean_preview_does_not_create_run_or_notification(self):
        self.configure();head=self.app.head;self.preview();self.assertEqual(self.app.head,head);self.assertEqual(self.app.status()['runs'],[]);self.assertEqual(self.app.queue(),[]);self.assertEqual(self.page.locator('#preview-records tr').count(),6);self.image('services-jobs-wide.png')
    def test_csv_preview_and_run(self):
        self.configure(True);self.preview(True);self.run_job();self.assertEqual(self.app.result('sample_run')['job']['input_format'],'csv');expect(self.page.locator('#metrics')).to_contain_text('MAE 4')
    def test_invalid_jsonl_shows_issue_and_disables_run(self):
        self.configure();self.page.locator('#content').fill('null');self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('Preview blocked. Correct the input or configuration.');expect(self.page.locator('#preview-summary')).to_contain_text('ROW_SCHEMA_INVALID');expect(self.page.locator('#run')).to_be_disabled();self.assertEqual(self.app.queue(),[])
    def test_gap_and_duplicate_conflict_block_forecasting(self):
        self.configure();raw=fictional_input().decode()+'\n'+canonical(dict(series='sample',period=0,value=99)).decode();self.page.locator('#content').fill(raw);self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('Preview blocked. Correct the input or configuration.');expect(self.page.locator('#preview-summary')).to_contain_text('RECORD_CONFLICT');expect(self.page.locator('#run')).to_be_disabled()
    def test_editing_input_or_job_configuration_invalidates_preview(self):
        self.configure();self.preview();self.page.locator('#content').fill(self.page.locator('#content').input_value()+'\n');expect(self.page.locator('#run')).to_be_disabled();self.page.locator('#preview').click();expect(self.page.locator('#run')).to_be_enabled();self.page.locator('#configuration').fill(self.page.locator('#configuration').input_value()+' ');expect(self.page.locator('#run')).to_be_disabled()
    def test_configuration_schema_error_keeps_draft_and_journal(self):
        head=self.app.head;self.page.locator('#configuration').fill('{"version":1,"jobs":[],"private_fixture":"invented"}');self.page.locator('#configure').click();expect(self.page.locator('#status')).to_have_text('CONFIGURATION_INVALID');self.assertIn('private_fixture',self.page.locator('#configuration').input_value());self.assertEqual(self.app.head,head)
    def test_identical_run_key_is_idempotent_and_changed_configuration_conflicts(self):
        self.ready();head=self.app.head;self.page.locator('[data-tab=jobs]').click();self.preview();self.run_job();self.assertEqual(self.app.head,head);self.assertEqual(len(self.app.queue()),1);self.page.locator('[data-tab=jobs]').click();value=json.loads(self.page.locator('#configuration').input_value());value['jobs'][0]['method']='last';self.page.locator('#configuration').fill(json.dumps(value));self.page.locator('#configure').click();expect(self.page.locator('#status')).to_contain_text('Configuration saved.');self.preview();self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('RUN_IDEMPOTENCY_CONFLICT');self.assertEqual(self.app.result('sample_run')['job']['method'],'mean')
    def test_reconfiguration_keeps_old_result_snapshot_visible(self):
        self.ready();self.page.locator('[data-tab=jobs]').click();value=json.loads(self.page.locator('#configuration').input_value());value['jobs'][0]['horizon']=5;self.page.locator('#configuration').fill(json.dumps(value));self.page.locator('#configure').click();expect(self.page.locator('#status')).to_contain_text('Configuration saved.');self.page.locator('[data-tab=runs]').click();self.page.locator('[data-run=sample_run]').click();expect(self.page.locator('#status')).to_have_text('Saved run inspected. Review assertions are clear.');self.assertEqual(self.page.locator('#forecast-points tr').count(),3)
    def test_review_required_and_checks_clear_after_export_and_refresh(self):
        self.ready();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.review();self.export();expect(self.page.locator('#quality')).not_to_be_checked();self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal refreshed.');expect(self.page.locator('#export')).to_be_disabled()
    def test_reports_remain_new_only_on_repeated_explicit_exports(self):
        self.ready();self.review();one=self.export();before=(self.parent/'reports'/one['directory']/'run.json').read_bytes();self.review();two=self.export();self.assertNotEqual(one['directory'],two['directory']);self.assertEqual((self.parent/'reports'/one['directory']/'run.json').read_bytes(),before)
    def test_retry_not_due_does_not_increase_attempt_count(self):
        self.ready();self.queue_tab();self.dispatch('retry');self.dispatch(tick='0');self.assertEqual(self.app.queue()[0]['attempts'],1);self.assertEqual(json.loads(self.page.locator('#dispatch-result').inner_text())['fake_calls'],0)
    def test_unknown_acceptance_stays_held_across_refresh_and_future_dispatch(self):
        self.ready();self.queue_tab();self.dispatch('accepted_then_unknown');expect(self.page.locator('#queue-rows')).to_contain_text('REVIEW_REQUIRED');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal refreshed.');self.dispatch(tick='100');self.assertEqual(json.loads(self.page.locator('#dispatch-result').inner_text())['fake_calls'],0);self.assertEqual(self.app.queue()[0]['attempts'],1)
    def test_simulated_interruption_records_review_state_and_no_resend(self):
        self.ready();self.queue_tab();self.dispatch('interrupt');expect(self.page.locator('#queue-rows')).to_contain_text('DELIVERY_INTERRUPTED');self.dispatch(tick='10');self.assertEqual(json.loads(self.page.locator('#dispatch-result').inner_text())['fake_calls'],0)
    def test_delivery_assertion_cannot_promote_uncertain_attempt(self):
        self.ready();self.queue_tab();self.dispatch('uncertain');self.page.locator('#delivery-assertion').check();self.page.locator('#delivery').click();expect(self.page.locator('#status')).to_have_text('DELIVERY_REPORT_REFUSED');self.assertEqual(self.app.queue()[0]['state'],'REVIEW_REQUIRED')
    def test_delivery_checkbox_and_matching_receipt_required(self):
        self.ready();self.queue_tab();self.dispatch();self.page.locator('#delivery').click();expect(self.page.locator('#status')).to_have_text('DELIVERY_ASSERTION_REQUIRED');self.page.locator('#delivery-assertion').check();self.page.locator('#receipt').fill('wrong_receipt');self.page.locator('#delivery').click();expect(self.page.locator('#status')).to_have_text('DELIVERY_REPORT_REFUSED');self.assertEqual(self.app.queue()[0]['state'],'ACCEPTED')
    def test_clock_regression_keeps_editor_and_no_new_attempt(self):
        self.ready();self.queue_tab();self.dispatch('retry','5');head=self.app.head;self.page.locator('#tick').fill('4');self.page.locator('#dispatch').click();expect(self.page.locator('#status')).to_have_text('CLOCK_INVALID');expect(self.page.locator('#tick')).to_have_value('4');self.assertEqual(self.app.head,head)
    def test_stale_journal_head_refuses_mutation_and_preserves_draft(self):
        self.configure();value=decode(fictional_configuration());value['jobs'][0]['window']=2;self.controller.apply('configure',dict(expected_head=self.app.head,configuration=canonical(value).decode()));self.page.locator('#content').fill('Retain invented draft');self.page.locator('#preview').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#content')).to_have_value('Retain invented draft');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal refreshed.')
    def test_lost_run_response_is_never_automatically_retried(self):
        self.configure();self.preview()
        def lost(route):route.fetch();route.abort()
        self.page.route('**/api/run',lost);self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(self.app.queue()),1);self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(path.endswith('/api/run') for _,path in self.requests),1);self.page.unroute('**/api/run');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal refreshed.');self.assertEqual(len(self.app.queue()),1)
    def test_restart_reopens_same_journal_without_dispatching_pending_work(self):
        self.ready();self.server.shutdown();self.thread.join(5);self.app.close();self.app=Stack(self.root);self.controller.stack=self.app;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#status')).to_have_text('Private journal ready. Nothing configured or dispatched automatically.');self.assertEqual(self.app.queue()[0]['attempts'],0);self.page.locator('[data-tab=runs]').click();self.page.locator('[data-run=sample_run]').click();expect(self.page.locator('#metrics')).to_contain_text('MAE 4')
    def test_literal_markup_in_review_note_remains_text_and_is_never_fetched(self):
        self.ready();self.review();value='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>';self.page.locator('#note').fill(value);report=self.export();review=decode((self.parent/'reports'/report['directory']/'review.json').read_bytes());self.assertEqual(review['note'],value);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertFalse(any('example.invalid' in path for _,path in self.requests))
    def test_narrow_layout_keyboard_and_queue_table(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.ready();self.page.locator('#actor').focus();self.assertEqual(self.page.evaluate('document.activeElement.id'),'actor');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('services-runs-narrow.png');self.queue_tab();self.dispatch('uncertain');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('services-queue-narrow.png');self.page.locator('#queue .table-scroll').focus();self.page.keyboard.press('End');self.assertGreater(self.page.locator('#queue .table-scroll').evaluate('(element)=>element.scrollWidth-element.clientWidth'),0)
    def test_browser_cannot_read_api_without_session_or_origin(self):
        response=self.page.request.post('http://127.0.0.1:'+str(self.server.server_port)+'/api/overview',data={});self.assertEqual(response.status,403)
    def test_busy_action_blocks_overlapping_actions(self):
        self.ready();self.queue_tab();release=threading.Event();entered=threading.Event();original=self.app.dispatch
        def slow(*args,**kwargs):entered.set();release.wait(5);return original(*args,**kwargs)
        with mock.patch.object(self.app,'dispatch',side_effect=slow):
            self.page.locator('#dispatch').click();self.assertTrue(entered.wait(2));self.page.locator('#stop').click();expect(self.page.locator('#status')).to_have_text('An operation is running. Wait for it to finish.');release.set();expect(self.page.locator('#status')).to_have_text('Fictional dispatch recorded. Adapter acceptance is not verified delivery.')
        self.assertFalse(self.server.stopping.is_set())
