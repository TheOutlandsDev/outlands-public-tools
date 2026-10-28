"""Real Chromium private-workspace SQL/report workflows and failure preservation."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright,expect

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from sql_report import application as app,jobs,runtime as r,web


class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.addCleanup(jobs.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
        self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport={'width':1440,'height':1100});self.addCleanup(self.context.close);self.external=[];self.errors=[]
        def route(request):
            if request.request.url.startswith(f'http://127.0.0.1:{self.server.server_port}/'):request.continue_()
            else:self.external.append(request.request.url.split(':',1)[0]);request.abort()
        self.context.route('**/*',route);self.page=self.context.new_page();self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.goto(f'http://127.0.0.1:{self.server.server_port}/');expect(self.page.locator('#status')).to_have_text('Ready. Private workspace loaded.')
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def tearDown(self):
        self.assertEqual(self.external,[]);self.assertEqual(self.errors,[])
        destination=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if destination:
            target=Path(destination);target.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(target/(self._testMethodName+'.png')),full_page=True)
    def load(self):
        self.page.locator('#example-data').click();expect(self.page.locator('#status')).to_have_text('Fictional dataset loaded into draft.');self.page.locator('#import').click();expect(self.page.locator('#status')).to_have_text('Immutable SQLite snapshot imported.')
    def save(self):self.page.locator('#save-query').click();expect(self.page.locator('#status')).to_have_text('Immutable query revision saved; no SQL was executed.')
    def run_query(self,status='completed'):
        self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('Job finished: '+status+'. Saved artifact is pending review.');return self.page.locator('#artifacts').input_value()
    def approve(self):
        self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('Review recorded for this immutable artifact.')
    def set_query(self,sql,parameters=None,bindings=None):
        self.page.locator('#sql').fill(sql);self.page.locator('#parameters').fill(json.dumps(parameters or {}));self.page.locator('#bindings').fill(json.dumps(bindings or {}))
    def test_complete_query_review_export(self):
        self.load();self.save();self.assertEqual(app.artifacts()['artifacts'],[]);identifier=self.run_query();self.assertEqual(self.page.locator('#results tbody tr').count(),2);self.assertEqual(self.page.locator('#results tbody tr').first.inner_text(),'alpha\t8');self.approve();self.page.locator('#export').click();expect(self.page.locator('#status')).to_have_text('Approved artifact exported inside the private workspace.');result=json.loads(self.page.locator('#export-output').inner_text());self.assertFalse(result['manifest']['public_release_authorized']);self.assertEqual(app.artifact(identifier)['payload']['result']['rows'],[['alpha',8],['beta',11]])
    def test_dirty_and_stale_query_drafts_retained(self):
        self.load();self.save();self.page.locator('#sql').fill('SELECT :minimum AS draft');self.page.locator('#run').click();expect(self.page.locator('#status')).to_have_text('SAVE_OR_RELOAD_QUERY_DRAFT; drafts retained.');self.assertEqual(self.page.locator('#sql').input_value(),'SELECT :minimum AS draft');record=app.document('query','sample-summary');definition=record['definition'];definition['title']='Fictional parallel revision';app.save_query(r.encode(dict(definition=definition,expected_sha256=record['sha256'])));self.page.locator('#save-query').click();expect(self.page.locator('#status')).to_have_text('REVISION_CONFLICT; drafts retained.');self.assertEqual(self.page.locator('#sql').input_value(),'SELECT :minimum AS draft')
    def test_report_validation_and_explicit_query_draft(self):
        self.load();self.page.locator('summary').filter(has_text='Import or revise report XML').click();self.page.locator('#save-report').click();expect(self.page.locator('#status')).to_have_text('Inspected report revision saved; no datasets were run.');self.assertEqual(app.artifacts()['artifacts'],[]);self.page.locator('#validate-report').click();expect(self.page.locator('#status')).to_have_text('Job finished: completed. Saved artifact is pending review.');expect(self.page.locator('#result-state')).to_contain_text('fields valid: true');self.page.locator('#report-to-query').click();expect(self.page.locator('#status')).to_have_text('Report dataset SQL copied to an unsaved query draft.');self.assertTrue(self.page.locator('#query-id').input_value().startswith('report-'));self.save();self.run_query();self.assertEqual(self.page.locator('#results tbody tr').count(),2)
    def test_external_xml_and_doctype_refused_with_draft(self):
        self.page.locator('summary').filter(has_text='Import or revise report XML').click();original=self.page.locator('#report-xml').input_value()
        for text,code in ((original.replace('<DataSets>','<ConnectString>fictional</ConnectString><DataSets>'),'REPORT_EXTERNAL_OR_EXECUTABLE_CONTENT'),('<!DOCTYPE Report>'+original,'XML_DECLARATION_REFUSED')):
            self.page.locator('#report-xml').fill(text);self.page.locator('#save-report').click();expect(self.page.locator('#status')).to_have_text(code+'; drafts retained.');self.assertEqual(self.page.locator('#report-xml').input_value(),text)
        self.assertEqual(app.documents('report')['documents'],[])
    def test_parameter_text_and_result_are_literal(self):
        self.load();payload="<img src='https://example.invalid/fake' onerror='throw Error(1)'>";self.set_query('SELECT :value AS note',dict(value='text'),dict(value=payload));self.save();self.run_query();self.assertEqual(self.page.locator('#results tbody td').inner_text(),payload);self.assertEqual(self.page.locator('img').count(),0)
    def test_failed_query_cannot_be_approved(self):
        self.load();self.set_query('SELECT * FROM sqlite_master');self.save();identifier=self.run_query('refused');expect(self.page.locator('#result-state')).to_contain_text('SQL_AUTHORIZATION_REFUSED');self.page.locator('#review-status').select_option('approved')
        for key in ('quality','privacy','rights','context'):self.page.locator('#'+key).check()
        self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('REVIEW_INCOMPLETE_ARTIFACT; drafts retained.');self.assertEqual(app.artifact(identifier)['review']['status'],'pending')
    def test_query_budget_and_history(self):
        self.load();self.set_query('WITH RECURSIVE nums(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM nums WHERE x<100000000) SELECT SUM(x) FROM nums');self.save();self.run_query('budget_exceeded');expect(self.page.locator('#result-state')).to_contain_text('VM_OR_TIME_BUDGET');self.assertEqual(len(app.history('query','sample-summary')['versions']),1)
    def test_cancel_owned_worker_through_ui(self):
        self.load();self.set_query("WITH RECURSIVE nums(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM nums WHERE x<100000000) SELECT SUM(LENGTH(REPLACE(:value || x,'x','xx'))) FROM nums",dict(value='text'),dict(value='x'*1000));self.save();self.page.locator('#run').click();self.page.locator('#cancel').click();expect(self.page.locator('#status')).to_have_text('Job finished: cancelled. Saved artifact is pending review.');expect(self.page.locator('#cancel')).to_be_disabled();self.assertTrue(all(child.poll() is not None for job in jobs.JOBS.values() for child in job['control'].children))
    def test_new_run_pending_comparison_and_backup(self):
        self.load();self.save();first=self.run_query();self.approve();self.page.locator('#bindings').fill('{"minimum":4}');second=self.run_query();self.assertEqual(self.page.locator('#review-status').input_value(),'pending');self.page.locator('#left').select_option(first);self.page.locator('#right').select_option(second);self.page.locator('#compare').click();expect(self.page.locator('#status')).to_have_text('Returned-order preview comparison completed.');value=json.loads(self.page.locator('#comparison').inner_text());self.assertFalse(value['rows_equal_in_returned_order']);self.assertTrue(value['comparison_complete']);self.page.locator('#backup').click();expect(self.page.locator('#status')).to_have_text('State database backed up; snapshots are separate.');self.assertFalse(json.loads(self.page.locator('#export-output').inner_text())['snapshots_included'])
    def test_truncated_preview_is_visible(self):
        self.load();self.set_query('SELECT a.item_id FROM items a CROSS JOIN items b CROSS JOIN items c CROSS JOIN items d ORDER BY a.item_id');self.save();identifier=self.run_query();expect(self.page.locator('#result-state')).to_contain_text('TRUNCATED PREVIEW');self.assertEqual(self.page.locator('#results tbody tr').count(),200);self.assertTrue(app.artifact(identifier)['payload']['result']['truncated'])
    def test_stale_review_note_retained(self):
        self.load();self.save();identifier=self.run_query();record=app.artifact(identifier);app.review(r.encode(dict(artifact_id=identifier,artifact_sha256=record['artifact_sha256'],expected_version=0,status='pending',actor='sample_other',note='Fictional parallel note',checks=dict(quality=False,privacy=False,rights=False,context=False))));self.page.locator('#note').fill('Retain this fictional note');self.page.locator('#review-form button').click();expect(self.page.locator('#status')).to_have_text('REVIEW_VERSION_CONFLICT; drafts retained.');self.assertEqual(self.page.locator('#note').input_value(),'Retain this fictional note');self.page.locator('#load-artifact').click();expect(self.page.locator('#status')).to_have_text('Saved artifact and review loaded; editor drafts retained.');self.assertEqual(self.page.locator('#note').input_value(),'Fictional parallel note')
    def test_narrow_keyboard_workflow(self):
        self.page.set_viewport_size({'width':390,'height':844});self.load();self.page.locator('#save-query').focus();self.page.keyboard.press('Enter');expect(self.page.locator('#status')).to_have_text('Immutable query revision saved; no SQL was executed.');self.run_query();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)


if __name__=='__main__':unittest.main()
