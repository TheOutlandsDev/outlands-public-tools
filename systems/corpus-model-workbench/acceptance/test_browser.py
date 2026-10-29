"""Actual Chromium acceptance using fresh fictional stores and an in-process fake model."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from playwright.sync_api import sync_playwright,expect
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from workbench import corpus,models,runtime,web
from workbench.demo import FictionalClient
expect.set_options(timeout=15000)
CHECKS=('quality','privacy','rights','context')

class WorkbenchBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        try:cls.browser=cls.playwright.chromium.launch(headless=True)
        except BaseException:cls.playwright.stop();raise
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.playwright.stop()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(runtime.close)
        self.root=Path(self.temp.name)/'instance';runtime.configure(self.root,create=True);corpus.initialize();self.fake=FictionalClient();runtime.set_client(self.fake)
        web.STOPPING=False;web.drain_jobs();web.JOBS.clear()
        self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
        self.context=self.browser.new_context(viewport=dict(width=1360,height=1000));self.addCleanup(self.context.close);self.page=self.context.new_page();self.requests=[];self.errors=[]
        self.page.on('request',lambda req:self.requests.append((req.method,req.url)));self.page.on('pageerror',lambda err:self.errors.append(str(err)))
        self.page.goto('http://127.0.0.1:'+str(self.server.server_port));expect(self.page.locator('#count')).to_contain_text('0 matching records')
    def tearDown(self):self.assertEqual(self.errors,[])
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5);web.drain_jobs();web.STOPPING=False
    def import_rows(self):
        self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('Import complete; records require review.');self.assertEqual(corpus.status()['records'],4)
    def load_benchmarks(self):
        self.page.locator('#load-benchmarks').click();expect(self.page.locator('#message')).to_have_text('Benchmarks loaded; matching examples held out.')
    def select(self,title):self.page.locator('#records .record').filter(has_text=title).click();expect(self.page.locator('#detail h2')).to_have_text(title)
    def review(self,decision='approved',checked=True):
        self.page.locator('#actor').fill('sample_reviewer');self.page.locator('#review-note').fill('Fictional independent review assertion')
        for key in CHECKS:self.page.locator('#check-'+key).set_checked(checked)
        self.page.locator('[data-decision='+decision+']').click();expect(self.page.locator('#message')).to_have_text('Review saved')
    def approve_all(self):
        self.page.locator('#status').select_option('');self.page.locator('#search').click();expect(self.page.locator('#count')).to_contain_text('4 matching records')
        for title in ('Fictional training example','Fictional heldout match','Fictional Python reference','Fictional heldout document'):
            self.select(title);self.review()
    def export(self,kind):
        previous=self.page.locator('#message').inner_text()
        self.page.locator('[data-export='+kind+']').click();expect(self.page.locator('#message')).not_to_have_text(previous);expect(self.page.locator('#message')).to_contain_text('Export saved: ')
        relative=self.page.locator('#message').inner_text().splitlines()[0].removeprefix('Export saved: ');return self.root/relative
    def models_tab(self):
        self.page.locator('[data-tab=models]').click();expect(self.page.locator('#message')).to_have_text('Ready');self.page.locator('#discover').click();expect(self.page.locator('#message')).to_have_text('Completed');expect(self.page.locator('#model-choices')).to_contain_text('fictional-model-a')
    def image(self,name):
        value=os.environ.get('OUTLANDS_BROWSER_EVIDENCE')
        if value:
            folder=Path(value);folder.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(folder/name),full_page=True)
    def test_complete_browser_import_review_sft_rag_and_verified_backup(self):
        self.load_benchmarks();self.import_rows();review=self.export('review');self.assertEqual(len((review/'candidates.jsonl').read_text(encoding='utf-8').splitlines()),4)
        self.approve_all();sft=self.export('sft');rag=self.export('rag')
        self.assertEqual(len((sft/'train.jsonl').read_text(encoding='utf-8').splitlines()),1);self.assertEqual(len((sft/'test.jsonl').read_text(encoding='utf-8').splitlines()),1);self.assertEqual(len((rag/'rag.jsonl').read_text(encoding='utf-8').splitlines()),1)
        for folder in (review,sft,rag):
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            for name,entry in manifest['files'].items():self.assertEqual(entry,dict(bytes=len((folder/name).read_bytes()),sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest()))
        self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('Backup saved: ');self.assertEqual(len(list((self.root/'backups').glob('*.sqlite3'))),1)
        self.assertTrue(all(url.startswith('http://127.0.0.1:') for _,url in self.requests));self.image('corpus-wide.png')
    def test_late_benchmark_load_updates_existing_split(self):
        self.import_rows();self.assertEqual(corpus.status()['split'],dict(train=3,test=1));self.load_benchmarks();self.assertEqual(corpus.status()['split'],dict(train=2,test=2))
    def test_unchecked_approval_refused_and_drafts_preserved(self):
        self.import_rows();self.select('Fictional training example');self.page.locator('#actor').fill('sample');self.page.locator('#review-note').fill('Keep invented draft');self.page.locator('[data-decision=approved]').click();expect(self.page.locator('#message')).to_have_text('OPERATION_FAILED');expect(self.page.locator('#review-note')).to_have_value('Keep invented draft');self.assertEqual(corpus.status()['status'],{'pending':4})
    def test_revocation_blocks_future_sft_and_retains_old_output(self):
        self.load_benchmarks();self.import_rows();self.approve_all();old=self.export('sft');self.select('Fictional training example');self.review('pending',False);new=self.export('sft');self.assertEqual((new/'train.jsonl').read_bytes(),b'');self.assertTrue((old/'train.jsonl').read_bytes())
    def test_context_display_and_review_reset_are_explicit(self):
        self.import_rows();self.select('Fictional training example');self.page.locator('#context').click();expect(self.page.locator('#context-data')).to_contain_text('complete_supplied_messages');self.review();expect(self.page.locator('#check-quality')).not_to_be_checked()
    def test_fictional_model_comparison_and_independent_score(self):
        self.load_benchmarks();self.models_tab();self.page.locator('input[name=model]').first.check();self.page.locator('#benchmark-limit').fill('1');self.page.locator('#benchmark').click();expect(self.page.locator('#message')).to_have_text('Responses saved. Review outputs and score against the rubrics.')
        self.page.locator('#runs summary').first.click();self.page.locator('#runs input[placeholder="0-5"]').fill('4');self.page.locator('#runs input[placeholder=Reviewer]').fill('sample');self.page.locator('#runs input[placeholder="Evidence note"]').fill('Invented rubric score');self.page.locator('[data-score]').click();expect(self.page.locator('#message')).to_have_text('Score saved');self.assertEqual(models.overview()['recent_runs'][0]['score'],4);expect(self.page.locator('#leaderboard')).to_contain_text('more evidence needed');self.image('corpus-models.png')
    def test_fictional_discussion_transcript_and_idempotent_pending_queue(self):
        self.models_tab();self.page.locator('[data-tab=council]').click();self.page.locator('#task').fill('Explain an invented Python function.');self.page.locator('#rounds').select_option('1');self.page.locator('#discuss').click();expect(self.page.locator('#conversation')).to_contain_text('Final answer');expect(self.page.locator('#conversation [data-queue]')).to_be_visible();self.page.locator('[data-queue]').click();expect(self.page.locator('#message')).to_have_text('Answer added as a pending training candidate');self.page.locator('[data-queue]').click();expect(self.page.locator('#message')).to_have_text('Answer added as a pending training candidate');self.assertEqual(corpus.status()['status'],{'pending':1});self.assertEqual(len(models.get_discussion(models.overview()['discussions'][0]['id'])['turns']),4);self.image('corpus-discussion.png')
    def test_embeddings_search_and_rejected_document_removed(self):
        self.import_rows();self.approve_all();self.models_tab();self.page.locator('#embed').click();expect(self.page.locator('#message')).to_have_text('Vectors saved: 1');self.page.locator('#semantic-search').click();expect(self.page.locator('#semantic-results')).to_contain_text('Fictional Python reference');self.page.locator('[data-tab=corpus]').click();self.select('Fictional Python reference');self.review('rejected',False);self.page.locator('[data-tab=models]').click();self.page.locator('#semantic-search').click();expect(self.page.locator('#semantic-results')).to_have_text('[]')
    def test_markup_in_record_title_is_literal_and_never_fetched(self):
        title='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>'
        row=dict(kind='document',title=title,text='Invented Python reference');runtime.write_new(self.root/'inbox/markup.jsonl',json.dumps(row).encode());self.page.locator('#import-path').fill('inbox/markup.jsonl');self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('Import complete; records require review.');self.page.locator('#records .record').click();expect(self.page.locator('#detail h2')).to_have_text(title);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertFalse(any('example.invalid' in url for _,url in self.requests))
    def test_malformed_import_rolls_back_and_preserves_selection(self):
        runtime.write_new(self.root/'inbox/bad.jsonl',b'{\n');self.page.locator('#import-path').fill('inbox/bad.jsonl');self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('OPERATION_FAILED');expect(self.page.locator('#import-path')).to_have_value('inbox/bad.jsonl');self.assertEqual(corpus.status()['records'],0)
    def test_workspace_escape_is_refused(self):
        self.page.locator('#import-path').fill('../outside.jsonl');self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('OPERATION_FAILED');self.assertEqual(corpus.status()['sources'],0)
    def test_duplicate_import_adds_no_duplicate_records(self):
        self.import_rows();self.import_rows();self.assertEqual(corpus.status()['provenance_links'],5)
    def test_search_filters_and_pagination_empty_result(self):
        self.import_rows();self.page.locator('#kind').select_option('document');self.page.locator('#query').fill('Python');self.page.locator('#query').press('Enter');expect(self.page.locator('#count')).to_contain_text('2 matching records');self.page.locator('#query').fill('unknowninventedterm');self.page.locator('#search').click();expect(self.page.locator('#count')).to_contain_text('0 matching records');expect(self.page.locator('#previous')).to_be_disabled();expect(self.page.locator('#next')).to_be_disabled()
    def test_reload_retains_store_and_clears_unsubmitted_review_checks(self):
        self.import_rows();self.select('Fictional training example');self.page.locator('#check-quality').check();self.page.reload();expect(self.page.locator('#count')).to_contain_text('4 matching records');self.select('Fictional training example');expect(self.page.locator('#check-quality')).not_to_be_checked()
    def test_narrow_layout_and_keyboard_controls(self):
        self.page.set_viewport_size(dict(width=390,height=844));self.import_rows();self.select('Fictional training example');self.page.locator('#actor').focus();self.assertEqual(self.page.evaluate('document.activeElement.id'),'actor');self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('corpus-narrow.png')
    def test_unauthenticated_browser_request_cannot_read_private_status(self):
        response=self.page.request.get('http://127.0.0.1:'+str(self.server.server_port)+'/api/status');self.assertEqual(response.status,403)
    def test_unknown_job_stops_polling_and_requires_reload(self):
        self.page.route('**/api/job?*',lambda route:route.fulfill(json={'status':'unknown'}));self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('JOB_UNKNOWN_RELOAD_BEFORE_RETRY');self.assertEqual(len(list((self.root/'backups').glob('*.sqlite3'))),1)
    def test_model_failure_is_redacted_and_keeps_task_draft(self):
        self.models_tab()
        with mock.patch.object(self.fake,'request',side_effect=ValueError('invented-private-marker')):
            self.page.locator('#discover').click();expect(self.page.locator('#message')).to_have_text('OPERATION_FAILED')
        self.assertNotIn('invented-private-marker',self.page.content())
    def test_lost_import_response_is_not_retried_automatically(self):
        def lost(route):route.fetch();route.abort()
        self.page.route('**/api/import',lost);self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_RELOAD_BEFORE_RETRY');web.drain_jobs();self.assertEqual(corpus.status()['records'],4);self.assertEqual(sum(path.endswith('/api/import') for _,path in self.requests),1)
    def test_busy_job_blocks_browser_actions_and_stop(self):
        release=threading.Event();entered=threading.Event();original=corpus.backup
        def slow():entered.set();release.wait(10);return original()
        with mock.patch.object(corpus,'backup',side_effect=slow):
            self.page.locator('#backup').click();self.assertTrue(entered.wait(2));self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('A job is running. Wait before another action.');release.set();expect(self.page.locator('#message')).to_contain_text('Backup saved: ')
        self.assertEqual(corpus.status()['records'],0)

    def test_changed_supplement_is_skipped_until_browser_rereview(self):
        context=self.root/'inbox/dialogue.jsonl'
        raw=b'{"event_id":1,"kind":"message","data":{"role":"user","text":"Invented prior question"}}\n'
        runtime.write_new(context,raw)
        row=dict(kind='example',title='Invented context example',messages=[dict(role='user',content='Fictional question'),dict(role='assistant',content='Fictional answer')],metadata=dict(supplement_root='inbox',context=dict(relative_path='dialogue.jsonl',preceding_events=[1,1])))
        runtime.write_new(self.root/'inbox/context.jsonl',json.dumps(row).encode());self.page.locator('#import-path').fill('inbox/context.jsonl');self.page.locator('#import-jsonl').click();expect(self.page.locator('#message')).to_have_text('Import complete; records require review.');self.select('Invented context example');self.review();self.page.locator('#status').select_option('');self.page.locator('#search').click()
        first=self.export('sft');self.assertTrue((first/'train.jsonl').read_bytes())
        context.write_bytes(raw.replace(b'prior',b'changed'))
        second=self.export('sft');manifest=json.loads((second/'manifest.json').read_text(encoding='utf-8'));self.assertFalse(manifest['training_ready']);self.assertEqual(manifest['skipped'][0]['reason'],'CURRENT_CONTENT_REVIEW_REQUIRED')
        self.select('Invented context example');self.page.locator('#context').click();expect(self.page.locator('#context-data')).to_contain_text('Invented changed question');self.review();third=self.export('sft');self.assertTrue((third/'train.jsonl').read_bytes())
    def test_restart_reopens_fictional_store_and_preserves_review_pin(self):
        self.import_rows();self.approve_all();self.server.shutdown();self.thread.join(5);web.drain_jobs();runtime.close();runtime.configure(self.root);runtime.set_client(FictionalClient());self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#count')).to_contain_text('0 matching records');self.page.locator('#status').select_option('approved');self.page.locator('#search').click();expect(self.page.locator('#count')).to_contain_text('4 matching records');output=self.export('sft');self.assertEqual(sum(json.loads((output/'manifest.json').read_text(encoding='utf-8'))['counts'].values()),2)
