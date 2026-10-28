"""Actual Chromium copy, drill, retention and private journal workflows."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from recovery import application as app,filesystem as fs,runtime as r,web
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append(request.url));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Choose a quiescent fictional tree to begin.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def snapshot(self,source='inbox/sample-files-v1'):
        self.page.locator('#source').fill(source);self.page.locator('#quiescent').check();self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('Full snapshot committed after byte verification. Source files were not changed.');return app.overview()['snapshots'][-1]['snapshot_id']
    def restore(self):
        self.page.locator('#restore').click();expect(self.page.locator('#status')).to_have_text('Restore drill verified in a fresh private directory. No existing files replaced.');return app.overview()['jobs'][-1]
    def plan(self):
        self.page.locator('#retention').click();expect(self.page.locator('#status')).to_have_text('Advisory retention plan calculated from fresh verification. Nothing deleted.');return json.loads(self.page.locator('#retention-result').inner_text())
    def approve(self):
        for name in ('quality','privacy','rights','context'):self.page.locator('#'+name).check()
    def capture(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(directory/name),full_page=True)
    def test_complete_snapshot_restore_plan_and_verified_bytes(self):
        first=self.snapshot();restored=self.restore();self.assertEqual((self.root/restored['result']['target']/'files/data/sample.csv').read_bytes(),b'item,count\nsample,3\n');self.snapshot('inbox/sample-files-v2');self.assertEqual(self.plan()['candidates'],1);self.assertEqual(self.page.locator('#snapshots option').count(),2);self.page.locator('#snapshots').select_option(first);self.page.locator('#manifest').click();expect(self.page.locator('#snapshot-details')).to_contain_text('"payload_reverified": false');self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests));self.capture('backup-wide.png')
    def test_quiescent_assertion_required_before_any_job(self):
        self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('QUIESCENT_SOURCE_ASSERTION_REQUIRED');self.assertEqual(app.overview()['jobs'],[])
    def test_snapshot_reverification_is_a_journaled_job(self):
        self.snapshot();self.page.locator('#verify').click();expect(self.page.locator('#status')).to_have_text('Snapshot inventory, marker and every file hash verified.');expect(self.page.locator('#complete-count')).to_have_text('2');self.assertEqual(app.overview()['jobs'][-1]['kind'],'verify')
    def test_restore_targets_are_always_fresh(self):
        self.snapshot();first=self.restore();second=self.restore();self.assertNotEqual(first['result']['target'],second['result']['target']);self.assertTrue((self.root/first['result']['target']/'RESTORED.json').is_file())
    def test_holds_protect_and_release_only_retention_metadata(self):
        first=self.snapshot();self.restore();self.snapshot('inbox/sample-files-v2');self.page.locator('#snapshots').select_option(first);self.page.locator('#hold-on').click();expect(self.page.locator('#status')).to_have_text('Manual retention hold recorded in the journal.');self.assertEqual(self.plan()['candidates'],0);self.page.locator('#hold-off').click();expect(self.page.locator('#status')).to_have_text('Manual retention hold recorded in the journal.');self.assertEqual(self.plan()['candidates'],1)
    def test_corrupt_restore_revokes_current_drill_proof(self):
        first=self.snapshot();restored=self.restore();self.snapshot();(self.root/restored['result']['target']/'files/empty.txt').write_bytes(b'corrupt');plan=self.plan();old=next(row for row in plan['snapshots'] if row['snapshot_id']==first);self.assertFalse(old['restore_drill_verified']);self.assertEqual(old['status'],'protected')
    def test_corrupt_snapshot_failure_record_and_form_retention(self):
        identifier=self.snapshot();(self.root/'snapshots'/identifier/'files/empty.txt').write_bytes(b'corrupt');self.page.locator('#reason').fill('My fictional unsaved reason');self.page.locator('#verify').click();expect(self.page.locator('#status')).to_have_text('SNAPSHOT_CONTENT_MISMATCH');expect(self.page.locator('#reason')).to_have_value('My fictional unsaved reason');self.assertEqual(app.overview()['jobs'][-1]['status'],'failed');self.page.locator('#refresh').click();expect(self.page.locator('#failed-count')).to_have_text('1');expect(self.page.locator('#jobs')).to_contain_text('SNAPSHOT_CONTENT_MISMATCH')
    def test_stale_head_refuses_write_without_losing_selector(self):
        app.snapshot(r.encode(dict(expected_head=app.overview()['head'],actor='sample_other',reason='Fictional competing request',request=dict(source='inbox/sample-files-v1',exclusions=['cache'],quiescent=True))));self.page.locator('#source').fill('inbox/sample-files-v2');self.page.locator('#quiescent').check();self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('JOURNAL_HEAD_CONFLICT');expect(self.page.locator('#source')).to_have_value('inbox/sample-files-v2');self.assertEqual(len(app.overview()['snapshots']),1)
    def test_private_report_review_and_index_backup_scope(self):
        self.snapshot();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('EXPORT_REVIEW_REQUIRED');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Reviewed private metadata report created. Payload bytes were not exported.');report=json.loads(self.page.locator('#handoff').inner_text());self.assertFalse(report['manifest']['includes_snapshot_bytes']);self.assertFalse(report['manifest']['public_release_authorized']);self.assertEqual(len(report['manifest']['files']),5);self.assertTrue(any(name.startswith('manifests/') for name in report['manifest']['files']));self.page.locator('#backup-index').click();expect(self.page.locator('#status')).to_have_text('Metadata index backup verified. Snapshot payload bytes are not included.')
    def test_review_checkboxes_reset_when_journal_changes(self):
        self.snapshot();self.approve();self.page.locator('#verify').click();expect(self.page.locator('#status')).to_contain_text('Snapshot inventory, marker')
        for name in ('quality','privacy','rights','context'):expect(self.page.locator('#'+name)).not_to_be_checked()
    def test_literal_actor_markup_is_never_rendered(self):
        text='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';self.page.locator('#actor').fill(text);self.snapshot();self.page.locator('#job-details').click();expect(self.page.locator('#job')).to_contain_text('<img');self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'));self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests))
    def test_partial_failure_is_retained_and_no_snapshot_registered(self):
        original=r.write_new
        def fail(path,raw):
            if 'snapshots' in Path(path).parts and Path(path).name=='empty.txt':raise OSError('fictional')
            return original(path,raw)
        self.page.locator('#quiescent').check()
        with mock.patch.object(r,'write_new',side_effect=fail):self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('FILESYSTEM_REFUSED')
        row=app.overview()['jobs'][-1];self.assertTrue((self.root/'snapshots'/row['job_id']/'files/data/sample.csv').is_file());self.assertEqual(app.overview()['snapshots'],[]);self.page.locator('#refresh').click();expect(self.page.locator('#failed-count')).to_have_text('1')
    def test_pending_job_requires_explicit_stopped_recovery(self):
        with mock.patch.object(fs,'snapshot',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):app.snapshot(r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional interrupt',request=dict(source='inbox/sample-files-v1',exclusions=['cache'],quiescent=True))))
        self.page.locator('#refresh').click();expect(self.page.locator('#pending-count')).to_have_text('1');self.page.locator('#quiescent').check();self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('UNFINISHED_JOB_REVIEW_REQUIRED');self.assertEqual(self.page.locator('#delete').count(),0)
    def test_invalid_selector_and_exclusion_keep_draft(self):
        self.page.locator('#source').fill('../outside');self.page.locator('#quiescent').check();self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_have_text('RELATIVE_PATH_INVALID');expect(self.page.locator('#source')).to_have_value('../outside');self.assertEqual(app.overview()['jobs'],[])
    def test_failed_read_does_not_rebind_current_journal(self):
        self.snapshot();self.page.route('**/api/overview',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"FICTIONAL_READ_FAILURE"}'));self.page.locator('#source').fill('inbox/sample-files-v2');self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_have_text('FICTIONAL_READ_FAILURE');expect(self.page.locator('#snapshot-count')).to_have_text('1');expect(self.page.locator('#source')).to_have_value('inbox/sample-files-v2')
    def test_history_has_typed_hash_linked_events(self):
        self.snapshot();self.page.locator('#history').click();expect(self.page.locator('#status')).to_have_text('Hash-linked journal read and replay-checked.');expect(self.page.locator('#history-result')).to_contain_text('"operation": "job_started"');expect(self.page.locator('#history-result')).to_contain_text('"operation": "job_completed"')
    def test_narrow_keyboard_snapshot_and_visual_layout(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.page.locator('#source').focus();self.page.keyboard.press('ControlOrMeta+A');self.page.keyboard.insert_text('inbox/sample-files-v2');self.page.locator('#quiescent').check();self.page.locator('#snapshot').click();expect(self.page.locator('#status')).to_contain_text('Full snapshot committed');self.restore();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.capture('backup-narrow.png')
    def test_shutdown_stops_owned_server(self):
        self.page.locator('#shutdown').click();expect(self.page.locator('#status')).to_have_text('Local server stopping. Close this page.');self.thread.join(timeout=5);self.assertFalse(self.thread.is_alive())
    def test_reviewed_imported_snapshot_restores_without_adoption(self):
        identifier=self.snapshot();selected=app.overview()['snapshots'][0]['result'];shutil.copytree(self.root/'snapshots'/identifier,self.root/'inbox/reviewed-snapshot');self.page.locator('#import-pin').fill(selected['manifest_sha256']);self.page.locator('#restore-imported').click();expect(self.page.locator('#status')).to_have_text('Reviewed snapshot copy restored into a fresh directory. No snapshot was adopted.');row=app.overview()['jobs'][-1];self.assertEqual(row['kind'],'restore_imported');self.assertEqual(len(app.overview()['snapshots']),1);self.assertEqual((self.root/row['result']['target']/'files/empty.txt').read_bytes(),b'')

if __name__=='__main__':unittest.main()
