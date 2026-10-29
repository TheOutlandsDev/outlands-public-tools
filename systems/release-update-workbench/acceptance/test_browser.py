"""Real Chromium fictional snapshot, comparison, approval/revocation and private export flows."""
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
from releases import application as app,runtime as r,web
expect.set_options(timeout=20000)
POLICY_KEYS=('backup_confirmed','target_stopped_confirmed','readiness_confirmed','allow_removals','dependency_reviewed')

class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append((request.method,request.url)));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Invented inbox packages are available; nothing registered automatically.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def capture(self,version=None):
        if version:
            self.page.locator('#fixture').select_option(version);self.page.locator('#load-fixture').click();expect(self.page.locator('#status')).to_have_text('Invented request loaded into the editor. Nothing captured.')
        self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('Fresh private snapshot captured and verified. No payload was executed.');return app.overview()['candidates'][-1]
    def pair(self):return self.capture(),self.capture('v2')
    def compare(self,ready=True):
        if ready:
            for key in POLICY_KEYS:self.page.locator('#'+key).check()
        self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Pinned comparison saved. Review differences, assertions and blockers.');return app.overview()['comparisons'][-1]
    def plan(self):
        self.page.locator('#make-plan').click();expect(self.page.locator('#status')).to_have_text('Manual plan saved pending review. No target update was performed.');return app.overview()['plans'][-1]
    def checks(self):
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
    def approve(self):
        self.checks();self.page.locator('#approve').click();expect(self.page.locator('#status')).to_have_text('Plan approved for private handoff only. Target updates remain plan-only.')
    def ready_plan(self):self.pair();self.compare();return self.plan()
    def edit(self,fn):
        value=json.loads(self.page.locator('#capture').input_value());fn(value);self.page.locator('#capture').fill(json.dumps(value))
    def capture_image(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            folder=Path(evidence);folder.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(folder/name),full_page=True)
    def test_complete_capture_compare_approve_export_backup(self):
        self.ready_plan();expect(self.page.locator('#summary')).to_contain_text('ADD 1 · REPLACE 2 · REMOVE 1 · UNCHANGED 1');self.assertEqual(self.page.locator('#files tr').count(),5);self.approve();self.checks();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Approved private evidence handoff created.');manifest=json.loads(self.page.locator('#handoff').inner_text())['manifest'];self.assertEqual(len(manifest['files']),7);self.assertFalse(manifest['payload_files_included']);self.assertFalse(manifest['public_release_authorized']);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_contain_text('Private index backup verified.');self.assertFalse(json.loads(self.page.locator('#handoff').inner_text())['includes_payload_or_artifact_files']);self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.capture_image('release-wide.png')
    def test_unchecked_assertions_preserve_five_blockers_and_disable_approval(self):
        self.pair();comparison=self.compare(False);self.assertEqual(comparison['blocker_count'],5);self.plan();expect(self.page.locator('#approve')).to_be_disabled();expect(self.page.locator('#decision')).to_contain_text('REVIEW_REQUIRED');expect(self.page.locator('#blockers')).to_contain_text('BACKUP_ASSERTION_REQUIRED')
    def test_lock_declarations_expose_version_change_but_not_runtime_claim(self):
        self.pair();self.compare();value=json.loads(self.page.locator('#lock-data').inner_text());self.assertEqual(value['counts']['version_text_changed'],1);self.assertFalse(value['artifacts_verified']);self.assertFalse(value['packages_installed']);self.assertFalse(value['dependencies_resolved'])
    def test_pending_plan_has_no_approval_and_export_disabled(self):
        self.ready_plan();expect(self.page.locator('#decision')).to_contain_text('PENDING_REVIEW');expect(self.page.locator('#export')).to_be_disabled();self.assertEqual(app.overview()['reviews'],{})
    def test_review_checks_required_and_cleared_after_approval(self):
        self.ready_plan();self.page.locator('#approve').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED');self.approve();expect(self.page.locator('#privacy')).not_to_be_checked();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('REVIEW_REQUIRED')
    def test_revocation_blocks_future_exports_but_retains_previous_package(self):
        self.ready_plan();self.approve();self.checks();self.page.locator('#export').click();expect(self.page.locator('#status')).to_contain_text('Approved private evidence handoff created.');directory=json.loads(self.page.locator('#handoff').inner_text())['directory'];self.page.locator('#revoke').click();expect(self.page.locator('#status')).to_contain_text('Plan approval revoked.');expect(self.page.locator('#export')).to_be_disabled();self.assertTrue((self.root/directory/'manifest.json').exists());self.approve()
    def test_new_comparison_plan_never_inherits_previous_approval(self):
        first=self.ready_plan();self.approve();self.compare();second=self.plan();self.assertNotEqual(first['plan_id'],second['plan_id']);expect(self.page.locator('#decision')).to_contain_text('PENDING_REVIEW');expect(self.page.locator('#export')).to_be_disabled()
    def test_editor_policy_and_selection_changes_invalidate_current_pins(self):
        self.ready_plan();self.approve();self.page.locator('#allow_removals').uncheck();expect(self.page.locator('#make-plan')).to_be_disabled();expect(self.page.locator('#export')).to_be_disabled();expect(self.page.locator('#quality')).not_to_be_checked();self.page.locator('#capture').fill(self.page.locator('#capture').input_value()+' ');expect(self.page.locator('#approve')).to_be_disabled()
    def test_historical_plan_is_explicitly_inspected_again(self):
        first=self.ready_plan();self.approve();self.capture('v1');expect(self.page.locator('#export')).to_be_disabled();self.page.locator('#plans').select_option(first['plan_id']);self.page.locator('#inspect-plan').click();expect(self.page.locator('#status')).to_contain_text('Plan, comparison and snapshot bytes verified.');expect(self.page.locator('#decision')).to_contain_text('APPROVED_FOR_PRIVATE_HANDOFF');expect(self.page.locator('#export')).to_be_enabled()
    def test_invalid_json_and_untrusted_pin_do_not_capture(self):
        self.page.locator('#capture').fill('invalid');self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('FORM_JSON_INVALID');self.page.locator('#capture').fill(json.dumps(app.example()['v1']));self.edit(lambda v:v.update(manifest_sha256='f'*64));self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('TRUSTED_MANIFEST_PIN_MISMATCH');self.assertEqual(app.overview()['candidates'],[])
    def test_extra_payload_is_refused_and_reason_preserved(self):
        (self.root/'inbox/package-v1/extra.txt').write_bytes(b'invented extra');self.page.locator('#reason').fill('Retain this fictional note');self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('PAYLOAD_UNSAFE_OR_CHANGED');expect(self.page.locator('#reason')).to_have_value('Retain this fictional note');self.assertEqual(app.overview()['jobs'][0]['status'],'failed')
    def test_partial_capture_output_remains_unregistered(self):
        original=r.write_new
        def fail(path,raw):
            if path.name=='READY.json':raise OSError('withheld detail')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=fail):self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('OPERATION_REFUSED')
        job=app.overview()['jobs'][0];self.assertEqual(app.overview()['candidates'],[]);self.assertTrue((self.root/'candidates'/job['job_id']/'payload/bin/component.txt').exists())
    def test_tampered_snapshot_blocks_approval(self):
        plan=self.ready_plan();candidate=app.overview()['candidates'][-1];(self.root/candidate['target']/'payload/bin/component.txt').write_bytes(b'fictional changed bytes');self.checks();self.page.locator('#approve').click();expect(self.page.locator('#status')).to_have_text('PAYLOAD_UNSAFE_OR_CHANGED');self.assertNotIn(plan['plan_id'],app.overview()['reviews'])
    def test_tampered_approved_snapshot_blocks_handoff(self):
        self.ready_plan();self.approve();candidate=app.overview()['candidates'][0];(self.root/candidate['target']/'payload/obsolete.txt').write_bytes(b'changed');self.checks();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('PAYLOAD_UNSAFE_OR_CHANGED');self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_stale_head_keeps_editor_and_note_drafts(self):
        draft=self.page.locator('#capture').input_value();app.capture(r.encode(dict(expected_head=app.overview()['head'],actor='sample_other',reason='Competing fictional snapshot',request=app.example()['v1'])));self.page.locator('#reason').fill('Keep this fictional draft');self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#reason')).to_have_value('Keep this fictional draft');expect(self.page.locator('#capture')).to_have_value(draft)
    def test_lost_capture_response_never_automatically_retries(self):
        def lost(route):route.fetch();route.abort()
        self.page.route('**/api/capture',lost);self.page.locator('#capture-button').click();expect(self.page.locator('#status')).to_have_text('RESPONSE_UNCERTAIN_RELOAD_BEFORE_RETRY');self.assertEqual(len(app.overview()['candidates']),1);self.page.unroute('**/api/capture');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_contain_text('Journal reloaded.');self.assertEqual(len(app.overview()['candidates']),1)
    def test_literal_markup_in_label_is_text_and_never_fetched(self):
        text='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>';self.edit(lambda v:v.update(label=text));self.capture();expect(self.page.locator('#candidate')).to_contain_text(text);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertFalse(any('example.invalid' in url for _,url in self.requests))
    def test_inspect_snapshot_shows_verified_descriptor_without_running_launcher(self):
        self.capture();self.page.locator('#inspect-candidate').click();expect(self.page.locator('#status')).to_contain_text('Registered snapshot bytes, manifest and launcher declaration verified.');value=json.loads(self.page.locator('#candidate-data').inner_text());self.assertEqual(value['content']['files'],4);self.assertFalse(value['content']['runtime_verified']);self.assertEqual(value['content']['launcher']['executable'],'bin/component.txt')
    def test_history_is_explicit_and_private_input_scope_is_visible(self):
        self.capture();self.page.locator('#history').click();expect(self.page.locator('#status')).to_contain_text('Private typed history loaded.');expect(self.page.locator('#history-data')).to_contain_text('inbox/package-v1')
    def test_narrow_layout_and_keyboard_controls(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.ready_plan();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.page.locator('#context').focus();self.assertEqual(self.page.evaluate('document.activeElement.id'),'context');self.capture_image('release-narrow.png')
