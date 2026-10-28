"""Actual Chromium acceptance with invented observations and disposable stores."""
import copy
from datetime import timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from reliability import application as app,contracts as c,runtime as r,web
expect.set_options(timeout=10000)

def sample(seconds,state='healthy',observed=None,note='Fictional observation'):
    def at(value):return c.stamp(c.timestamp('2030-01-01T00:00:00Z')+timedelta(seconds=value))
    return dict(id='sample_'+str(seconds),at=at(seconds),services=[] if state is None else [dict(service_id='sample_service',signals=[dict(id='runtime',state=state,observed_at=at(seconds if observed is None else observed),note=note)])])

class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.fixture=r.decode((APP/'examples/sample-recording.json').read_bytes());self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context();self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.page.on('request',lambda request:self.requests.append(request.url));self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#status')).to_have_text('Private instance ready. Supplied observations only; no live probes or host control.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def load(self,recording=None):
        self.page.locator('#example').click();expect(self.page.locator('#status')).to_have_text('Fictional recording draft loaded. Submit to save it.')
        if recording is not None:self.page.locator('#editor').fill(json.dumps(recording))
        self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ')
    def health(self):return next(row for row in app.case('sample_reliability')['report']['incidents'] if row['kind']=='health')
    def select_health(self):self.page.locator('#incident-detail').select_option(self.health()['incident_id'])
    def acknowledge(self):
        self.select_health();self.page.locator('#acknowledge').click();expect(self.page.locator('#status')).to_have_text('Incident acknowledged in immutable history. Its health state was not changed.')
    def append(self,samples):
        self.page.locator('#operation').select_option('ingest');self.page.locator('#template').click();expect(self.page.locator('#status')).to_contain_text('Template loaded;');draft=json.loads(self.page.locator('#editor').input_value());draft['command']['data']['snapshots']=samples;self.page.locator('#editor').fill(json.dumps(draft));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ')
    def approve(self):
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
    def capture(self,name):
        evidence=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if evidence:
            directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(directory/name),full_page=True)
    def test_complete_replay_independent_coverage_and_no_remote_requests(self):
        self.load();expect(self.page.locator('#active-count')).to_have_text('2');expect(self.page.locator('#sample-count')).to_have_text('10');expect(self.page.locator('#coverage')).to_contain_text('healthy: 30s');expect(self.page.locator('#coverage')).to_contain_text('unknown: 25s');expect(self.page.locator('#timeline')).to_contain_text('maintenance');self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests));self.capture('reliability-wide.png')
    def test_acknowledgement_preserves_health_and_evidence(self):
        self.load();before=self.health();self.acknowledge();expect(self.page.locator('#incident-notes')).to_contain_text('"acknowledged": true');after=self.health();self.assertEqual(before['state'],after['state']);self.assertEqual(before['latest_evidence'],after['latest_evidence'])
    def test_escalation_requires_new_acknowledgement(self):
        recording=copy.deepcopy(self.fixture);recording['snapshots']=[sample(0,'degraded')];self.load(recording);self.acknowledge();self.append([sample(1,'down')]);self.select_health();expect(self.page.locator('#incident-notes')).to_contain_text('"acknowledged": false');expect(self.page.locator('#incident-notes')).to_contain_text('"escalations": 1')
    def test_cached_recovery_cannot_resolve_incidents(self):
        self.load();self.append([sample(110)]);expect(self.page.locator('#monitoring-count')).to_have_text('2');self.append([sample(120,observed=110)]);expect(self.page.locator('#resolved-count')).to_have_text('0');self.select_health();expect(self.page.locator('#incident-notes')).to_contain_text('"clean_count": 1')
    def test_stale_append_keeps_exact_draft_and_saved_binding(self):
        self.load();self.page.locator('#operation').select_option('ingest');self.page.locator('#template').click();expect(self.page.locator('#status')).to_contain_text('Template loaded;');draft=self.page.locator('#editor').input_value();selected=app.case('sample_reliability');app.act(r.encode(dict(case_id=selected['case_id'],expected_sha256=selected['sha256'],command=dict(operation='ingest',actor='sample_other',reason='Fictional competing append',data=dict(snapshots=[sample(110)])))));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('CASE_REVISION_CONFLICT');expect(self.page.locator('#editor')).to_have_value(draft)
    def test_historical_append_and_export_refused(self):
        self.load();self.acknowledge();self.page.locator('#versions').select_option('1');expect(self.page.locator('#status')).to_contain_text('Historical revision loaded;');self.page.locator('#operation').select_option('ingest');self.page.locator('#template').click();self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('CASE_REVISION_CONFLICT');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('CASE_REVISION_CONFLICT')
    def test_private_export_review_manifest_and_backup(self):
        self.load();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('EXPORT_REVIEW_REQUIRED');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Reviewed private reports created. Public publication is not authorized.');saved=json.loads(self.page.locator('#handoff').inner_text());self.assertFalse(saved['manifest']['public_release_authorized']);self.assertTrue((self.root/saved['directory']/'availability.csv').is_file());self.assertEqual(len(saved['manifest']['files']),8);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('Private database backup created and history replay verified.')
    def test_review_checks_reset_after_new_saved_revision(self):
        self.load();self.approve();self.append([sample(110)])
        for key in ('quality','privacy','rights','context'):expect(self.page.locator('#'+key)).not_to_be_checked()
    def test_markup_is_literal_and_never_runs(self):
        text='<img src="https://example.invalid/pixel" onerror="window.sampleExecuted=1">';recording=copy.deepcopy(self.fixture);recording['case']['title']=text;recording['snapshots']=[sample(0,'down',note=text)];self.load(recording);self.select_health();expect(self.page.locator('#incident-notes')).to_contain_text('<img');self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.sampleExecuted'));self.assertTrue(all(url.startswith('http://127.0.0.1:') for url in self.requests))
    def test_file_import_omits_source_filename(self):
        self.page.locator('#recording-file').set_input_files(dict(name='fictional-private-filename.json',mimeType='application/json',buffer=r.encode(self.fixture)));self.page.locator('#load-file').click();expect(self.page.locator('#status')).to_contain_text('Original filename was not recorded.');self.assertNotIn('fictional-private-filename',self.page.locator('#editor').input_value());self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ');self.assertNotIn('fictional-private-filename',r.encode(app.case('sample_reliability')).decode())
    def test_empty_file_and_malformed_draft_refused_without_data(self):
        self.page.locator('#recording-file').set_input_files(dict(name='sample.json',mimeType='application/json',buffer=b''));self.page.locator('#load-file').click();expect(self.page.locator('#status')).to_have_text('INPUT_LIMIT');draft='{"invented":"draft"}';self.page.locator('#editor').fill(draft);self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('FIELDS_INVALID');expect(self.page.locator('#editor')).to_have_value(draft);self.assertEqual(app.cases(),dict(cases=[]))
    def test_invalid_batch_is_atomic_and_draft_is_retained(self):
        self.load();self.page.locator('#operation').select_option('ingest');self.page.locator('#template').click();draft=json.loads(self.page.locator('#editor').input_value());draft['command']['data']['snapshots']=[sample(110),sample(105)];text=json.dumps(draft);self.page.locator('#editor').fill(text);self.page.locator('#submit').click();expect(self.page.locator('#status')).to_have_text('SNAPSHOT_ORDER_INVALID');expect(self.page.locator('#editor')).to_have_value(text);self.assertEqual(app.case('sample_reliability')['report']['snapshots'],10)
    def test_failed_history_fetch_preserves_current_binding(self):
        self.load();draft=self.page.locator('#editor').input_value();self.page.route('**/api/history?*',lambda route:route.fulfill(status=400,content_type='application/json',body='{"error":"FICTIONAL_HISTORY_FAILURE"}'));self.page.locator('#refresh').click();expect(self.page.locator('#status')).to_have_text('FICTIONAL_HISTORY_FAILURE');expect(self.page.locator('#identity')).to_contain_text('sample_reliability');expect(self.page.locator('#editor')).to_have_value(draft)
    def test_history_comparison_shows_separate_windows(self):
        self.load();self.append([sample(110)]);self.page.locator('#left').select_option('1');self.page.locator('#right').select_option('2');self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Saved revisions compared; observation windows are shown separately.');expect(self.page.locator('#diff')).to_contain_text('"windows_may_differ": true');expect(self.page.locator('#history')).to_contain_text('"command_sha256"')
    def test_narrow_keyboard_append_and_visual_layout(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.load();self.page.locator('#operation').select_option('ingest');self.page.locator('#template').click();draft=json.loads(self.page.locator('#editor').input_value());draft['command']['data']['snapshots']=[sample(110)];self.page.locator('#editor').focus();self.page.keyboard.press('ControlOrMeta+A');self.page.keyboard.insert_text(json.dumps(draft));self.page.locator('#submit').click();expect(self.page.locator('#status')).to_contain_text('Saved immutable revision ');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.capture('reliability-narrow.png')
    def test_shutdown_stops_the_owned_local_server(self):
        self.page.locator('#shutdown').click();expect(self.page.locator('#status')).to_have_text('Local server stopping. Close this page.');self.thread.join(timeout=5);self.assertFalse(self.thread.is_alive())

if __name__=='__main__':unittest.main()
