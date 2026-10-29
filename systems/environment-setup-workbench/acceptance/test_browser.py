"""Actual Chromium fictional-profile, review, failure and private handoff acceptance."""
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
from setupplan import application as app,artifacts as a,runtime as r,web
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append((request.method,request.url)));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Fictional editor inputs are not saved until requested.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def save(self):
        self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('New profile revision saved. Earlier revisions remain unchanged.');return app.overview()['profiles'][-1]
    def evaluate(self):
        self.page.locator('#evaluate').click();expect(self.page.locator('#status')).to_have_text('Pinned evaluation saved. Inspect declared results and manual checkpoints.');return app.overview()['evaluations'][-1]
    def approve(self):
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
    def plan(self):
        self.approve();self.page.locator('#make-plan').click();expect(self.page.locator('#status')).to_have_text('Reviewed plan saved. No setup action or verification was performed.');return app.overview()['plans'][-1]
    def inspect_plan(self):self.page.locator('#inspect-plan').click();expect(self.page.locator('#status')).to_have_text('Registered plan and all upstream pins verified. Review before private handoff.')
    def observations(self,edit):
        value=json.loads(self.page.locator('#observations').input_value());edit(value);self.page.locator('#observations').fill(json.dumps(value))
    def profile(self,edit):
        value=json.loads(self.page.locator('#profile').input_value());edit(value);self.page.locator('#profile').fill(json.dumps(value))
    def capture(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            folder=Path(evidence);folder.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(folder/name),full_page=True)
    def test_complete_profile_evaluation_plan_export_and_backup(self):
        self.save();self.evaluate();expect(self.page.locator('#summary')).to_contain_text('DECLARATIONS_SATISFIED · 9 checks');self.assertEqual(self.page.locator('#checks tr').count(),9);self.assertEqual(self.page.locator('#steps .step').count(),3);self.plan();self.inspect_plan();self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Reviewed private handoff created.');manifest=json.loads(self.page.locator('#handoff').inner_text())['manifest'];self.assertFalse(manifest['public_release_authorized']);self.assertFalse(manifest['execution_authorized']);self.assertEqual(len(manifest['files']),5);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_contain_text('Private index backup verified.');self.assertFalse(json.loads(self.page.locator('#handoff').inner_text())['includes_artifact_files']);self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.capture('setup-wide.png')
    def test_blocked_readiness_propagates_and_review_keeps_blockers(self):
        self.save();self.observations(lambda v:v['prerequisites'].update(sample_runtime='MISSING'));self.evaluate();expect(self.page.locator('#summary')).to_contain_text('3 blocked steps');self.assertEqual(self.page.locator('#steps .blocked').count(),3);plan=self.plan();self.assertEqual(app.inspect('plan',plan['plan_id'])['content']['status'],'REVIEW_REQUIRED')
    def test_unknown_is_visible_without_false_absence_claim(self):
        self.save();self.observations(lambda v:v['prerequisites'].pop('sample_runtime'));self.evaluate();expect(self.page.locator('#checks')).to_contain_text('UNKNOWN')
    def test_configuration_values_are_excluded_from_result_display(self):
        self.save();self.observations(lambda v:v['settings'].update(FICTIONAL_PRIVATE_MARKER='invented-value-only'));self.evaluate();expect(self.page.locator('#evaluation-data')).not_to_contain_text('invented-value-only');expect(self.page.locator('#evaluation-data')).not_to_contain_text('FICTIONAL_PRIVATE_MARKER');expect(self.page.locator('#summary')).to_contain_text('REVIEW_REQUIRED')
    def test_literal_markup_is_text_and_never_fetched(self):
        text='<img src="https://example.invalid/fictional.png" onerror="window.fixtureExecuted=true">';self.profile(lambda v:v['steps'][0].update(verification=text));self.save();self.evaluate();expect(self.page.locator('#steps')).to_contain_text(text);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertFalse(any('example.invalid' in url for _,url in self.requests))
    def test_profile_revision_comparison_has_changed_identifier(self):
        first=self.save();self.profile(lambda v:v['steps'][0].update(label='Fictional changed step'));second=self.save();self.assertEqual(second['parent_id'],first['profile_id']);self.page.locator('#compare-profile').select_option(first['profile_id']);self.page.locator('#compare-profiles').click();expect(self.page.locator('#status')).to_have_text('Saved profiles compared without changing either revision.');self.assertEqual(json.loads(self.page.locator('#profile-diff').inner_text())['changes']['steps']['changed'],['prepare'])
    def test_evaluation_comparison_shows_changed_checks(self):
        self.save();first=self.evaluate();self.observations(lambda v:v['prerequisites'].update(sample_runtime='MISSING'));self.evaluate();self.page.locator('#compare-evaluation').select_option(first['evaluation_id']);self.page.locator('#compare-evaluations').click();expect(self.page.locator('#status')).to_contain_text('Saved evaluation statuses compared');self.assertEqual(json.loads(self.page.locator('#evaluation-diff').inner_text())['changes']['checks']['changed'],['prerequisite:sample_runtime'])
    def test_invalid_json_and_executable_field_refused(self):
        self.page.locator('#profile').fill('invalid');self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('FORM_JSON_INVALID');self.page.locator('#profile').fill(json.dumps(app.example()['profile']));self.profile(lambda v:v['steps'][0].update(command='fictional-command'));self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('FIELDS_INVALID');self.assertEqual(app.overview()['profiles'],[])
    def test_boolean_integer_produces_failed_check_without_coercion(self):
        self.save();self.observations(lambda v:v['settings'].update(WORKERS=True));self.evaluate();expect(self.page.locator('#checks')).to_contain_text('TYPE_MISMATCH');expect(self.page.locator('#checks')).to_contain_text('DEPENDENCY_INVALID')
    def test_conflicting_connections_are_visible(self):
        self.profile(lambda v:v['connections']['bindings'][1].update(port=8765));self.save();self.evaluate();expect(self.page.locator('#checks')).to_contain_text('CONFLICT');expect(self.page.locator('#summary')).to_contain_text('2 blocking checks')
    def test_review_required_before_plan_or_export(self):
        self.save();self.evaluate();self.page.locator('#make-plan').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.assertEqual(app.overview()['plans'],[]);self.plan();self.inspect_plan();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_drafts_invalidate_pins_and_clear_review(self):
        self.save();self.evaluate();self.approve();self.page.locator('#observations').fill(self.page.locator('#observations').input_value()+' ');expect(self.page.locator('#quality')).not_to_be_checked();expect(self.page.locator('#make-plan')).to_be_disabled();self.page.locator('#profile').fill(self.page.locator('#profile').input_value()+' ');expect(self.page.locator('#evaluate')).to_be_disabled()
    def test_stale_head_keeps_editor_and_reason_drafts(self):
        app.save_profile(r.encode(dict(expected_head=app.overview()['head'],actor='sample_other',reason='Competing fictional revision',request=dict(parent_id=None,profile=app.example()['profile']))));draft=self.page.locator('#profile').input_value();self.page.locator('#reason').fill('Retain this fictional draft');self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#reason')).to_have_value('Retain this fictional draft');expect(self.page.locator('#profile')).to_have_value(draft)
    def test_historical_evaluation_plan_uses_original_pins(self):
        self.save();first=self.evaluate();self.profile(lambda v:v.update(label='Fictional second revision'));self.save();self.page.locator('#evaluations').select_option(first['evaluation_id']);self.page.locator('#inspect-evaluation').click();expect(self.page.locator('#status')).to_contain_text('Saved evaluation and profile pins verified.');plan=self.plan();self.assertEqual(plan['evaluation_id'],first['evaluation_id'])
    def test_partial_failure_retained_and_no_registered_profile(self):
        original=r.write_new
        def fail(path,raw):
            if path.name=='READY.json':raise OSError('withheld details')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=fail):self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('OPERATION_REFUSED')
        self.assertEqual(app.overview()['profiles'],[]);job=app.overview()['jobs'][0];self.assertTrue((self.root/'profiles'/job['job_id']/'profile.json').is_file())
    def test_tampered_evaluation_refuses_plan(self):
        self.save();value=self.evaluate();(self.root/value['target']/'evaluation.json').write_bytes(b'{}');self.approve();self.page.locator('#make-plan').click();expect(self.page.locator('#status')).to_have_text('ARTIFACT_HASH_MISMATCH');self.assertEqual(app.overview()['plans'],[])
    def test_lost_save_response_never_automatically_retries(self):
        def lost(route):route.fetch();route.abort()
        self.page.route('**/api/profile',lost);self.page.locator('#save-profile').click();expect(self.page.locator('#status')).to_have_text('RESPONSE_UNCERTAIN_RELOAD_BEFORE_RETRY');self.assertEqual(len(app.overview()['profiles']),1);self.page.unroute('**/api/profile');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal reloaded.');self.assertEqual(len(app.overview()['profiles']),1)
    def test_history_is_explicit_and_contains_private_inputs(self):
        self.save();self.evaluate();self.page.locator('#history').click();expect(self.page.locator('#status')).to_contain_text('Private typed journal loaded.');expect(self.page.locator('#history-data')).to_contain_text('WORKERS')
    def test_load_saved_revision_restores_profile_without_discarding_observations(self):
        first=self.save();draft=self.page.locator('#observations').input_value();self.profile(lambda v:v.update(label='Unsaved fictional edit'));self.page.locator('#load-profile').click();expect(self.page.locator('#status')).to_contain_text('Saved profile loaded.');self.assertEqual(json.loads(self.page.locator('#profile').input_value()),app.example()['profile']);expect(self.page.locator('#observations')).to_have_value(draft);expect(self.page.locator('#evaluate')).to_be_enabled()
    def test_narrow_layout_keeps_page_width_and_review_controls_accessible(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.save();self.evaluate();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.page.locator('#context').focus();self.assertEqual(self.page.evaluate('document.activeElement.id'),'context');self.capture('setup-narrow.png')
