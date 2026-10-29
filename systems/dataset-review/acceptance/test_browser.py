"""Actual Chromium; fresh fictional workspaces and no real corpus or profile."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from dataset_workbench import application as a,web
import review_store as core
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
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name);self.root=self.parent/'instance';a.Workbench.initialize(self.root);self.app=a.Workbench(self.root);self.addCleanup(self.app.close);self.server=web.LocalServer(('127.0.0.1',0),self.app);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop);self.context=self.browser.new_context(viewport=dict(width=1360,height=1000));self.addCleanup(self.context.close);self.page=self.context.new_page();self.errors=[];self.requests=[];self.page.on('pageerror',lambda error:self.errors.append(str(error)));self.page.on('request',lambda request:self.requests.append((request.method,request.url)));self.url='http://127.0.0.1:'+str(self.server.server_port);self.page.goto(self.url);expect(self.page.locator('#message')).to_have_text('Private store ready. Nothing imported or approved automatically.')
    def tearDown(self):self.assertEqual(self.errors,[])
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def tab(self,name):self.page.locator('[data-tab='+name+']').click()
    def load(self):
        self.tab('transfer');self.page.locator('#import').click();expect(self.page.locator('#message')).to_have_text('Import saved. New records are pending; holdouts remain conservative.');self.tab('records')
    def select_train(self):
        identifier=next(r['id'] for r in self.app.state()['records'] if r['split']=='train');self.page.locator('[data-record="'+identifier+'"]').click();expect(self.page.locator('#message')).to_have_text('Saved record loaded. Review assertions start unchecked.');return identifier
    def review_fields(self,decision='approved',note='Fictional evidence checked',all_checks=True):
        self.page.locator('#actor').fill('sample_reviewer');self.page.locator('#note').fill(note);self.page.locator('#decision').select_option(decision)
        if all_checks:
            for key in core.CHECKS:self.page.locator('#'+key).check()
    def approve(self):
        self.load();identifier=self.select_train();self.review_fields();self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('Local review saved. Public release remains unapproved.');return identifier
    def refresh(self,discard=False):
        if discard:self.page.locator('#discard').check()
        self.page.locator('#refresh').click()
    def image(self,name):
        if os.environ.get('OUTLANDS_BROWSER_EVIDENCE'):
            root=Path(os.environ['OUTLANDS_BROWSER_EVIDENCE']);root.mkdir(parents=True,exist_ok=True);self.page.screenshot(path=str(root/name),full_page=True)
    def test_empty_start_never_imports_or_approves(self):
        self.assertEqual(self.app.state()['total'],0);self.assertEqual(self.page.locator('#rows tbody tr').count(),0);self.assertTrue(all(url.startswith(self.url) for _,url in self.requests));self.image('dataset-empty-wide.png')
    def test_import_search_and_conservative_holdout_groups(self):
        self.load();self.assertEqual(self.app.state()['total'],4);self.page.locator('#query').fill('DUPLICATE');self.page.locator('#search').click();expect(self.page.locator('#page-info')).to_contain_text('1 of 1');expect(self.page.locator('#rows')).to_contain_text('test');self.page.locator('#rows button').click();expect(self.page.locator('#detail')).to_contain_text('sample-gamma');expect(self.page.locator('#detail')).to_contain_text('source_sha256');self.assertEqual(self.app.state()['counts']['pending'],4);self.image('dataset-provenance-wide.png')
    def test_explicit_review_and_fresh_unchecked_form(self):
        identifier=self.approve();self.assertEqual(self.app.detail(identifier)['status'],'approved');expect(self.page.locator('#actor')).to_have_value('');expect(self.page.locator('#note')).to_have_value('')
        for key in core.CHECKS:expect(self.page.locator('#'+key)).not_to_be_checked()
        self.image('dataset-review-wide.png')
    def test_missing_assertions_preserve_review_draft(self):
        self.load();identifier=self.select_train();self.review_fields(all_checks=False);self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('FOUR_CHECKS_REQUIRED');expect(self.page.locator('#note')).to_have_value('Fictional evidence checked');self.assertEqual(self.app.detail(identifier)['status'],'pending')
    def test_rejection_and_pending_review_remain_separate_from_approval(self):
        self.load();identifier=self.select_train();self.review_fields('rejected',all_checks=False);self.page.locator('#review').click();expect(self.page.locator('#message')).to_contain_text('Local review saved');self.assertEqual(self.app.detail(identifier)['status'],'rejected');self.review_fields('pending',all_checks=False);self.page.locator('#review').click();expect(self.page.locator('#message')).to_contain_text('Local review saved');self.assertEqual(self.app.detail(identifier)['status'],'pending');self.assertEqual(len(self.app.detail(identifier)['reviews']),2)
    def test_record_switch_refresh_and_search_preserve_unsaved_draft(self):
        self.load();identifier=self.select_train();self.review_fields();self.refresh();expect(self.page.locator('#message')).to_contain_text('UNSAVED_REVIEW_DRAFT');self.page.locator('#query').fill('fictional');self.page.locator('#search').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_REVIEW_DRAFT');other=next(r['id'] for r in self.app.state()['records'] if r['id']!=identifier);self.page.locator('[data-record="'+other+'"]').click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_REVIEW_DRAFT');expect(self.page.locator('#note')).to_have_value('Fictional evidence checked');self.refresh(True);expect(self.page.locator('#message')).to_have_text('Saved state refreshed. No action replayed.');expect(self.page.locator('#note')).to_have_value('')
    def test_dirty_review_blocks_import_export_and_backup(self):
        self.load();self.select_train();self.review_fields();self.tab('transfer')
        for key in ('import','export','backup'):self.page.locator('#'+key).click();expect(self.page.locator('#message')).to_contain_text('UNSAVED_REVIEW_DRAFT')
        self.assertEqual(list((self.root/'exports').iterdir()),[]);self.assertEqual(list((self.root/'backups').iterdir()),[])
    def test_second_tab_stale_review_refused_with_note_retained(self):
        self.load();identifier=self.select_train();self.review_fields();other=self.context.new_page();other.goto(self.url);expect(other.locator('#message')).to_contain_text('Private store ready');other.locator('[data-record="'+identifier+'"]').click();expect(other.locator('#message')).to_contain_text('Saved record loaded');other.locator('#actor').fill('sample_other');other.locator('#note').fill('Fictional independent rejection');other.locator('#decision').select_option('rejected');other.locator('#review').click();expect(other.locator('#message')).to_contain_text('Local review saved');self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('STALE_STATE_REFRESH_REQUIRED');expect(self.page.locator('#note')).to_have_value('Fictional evidence checked');self.assertEqual(self.app.detail(identifier)['status'],'rejected');other.close()
    def test_group_promotion_invalidates_stale_review_pin(self):
        self.load();identifier=self.select_train();self.review_fields();path=self.root/'inbox/promotion.jsonl';path.write_bytes(a.encode(dict(text=self.app.detail(identifier)['text'],group='sample-alpha',split='test')));self.app.mutate('import',dict(expected=self.app.state()['head'],file='inbox/promotion.jsonl'));self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('STALE_STATE_REFRESH_REQUIRED');self.assertEqual(self.app.detail(identifier)['status'],'pending');self.assertEqual(self.app.detail(identifier)['split'],'test')
    def test_approved_export_hash_inventory_and_database_backup(self):
        identifier=self.approve();self.tab('transfer');self.page.locator('#export').click();expect(self.page.locator('#message')).to_contain_text('Checked private export');result=json.loads(self.page.locator('#output').inner_text());folder=self.root/result['directory'];self.assertEqual({p.name for p in folder.iterdir()},{'approved.jsonl','manifest.json'});row=json.loads((folder/'approved.jsonl').read_bytes());self.assertEqual(row['id'],identifier);self.assertEqual(row['split'],'train');self.assertFalse(result['manifest']['public_release_authorized']);self.assertEqual(result['manifest']['files']['approved.jsonl']['sha256'],hashlib.sha256((folder/'approved.jsonl').read_bytes()).hexdigest());self.page.locator('#backup').click();expect(self.page.locator('#message')).to_contain_text('Checked database-only backup');backup=json.loads(self.page.locator('#output').inner_text());self.assertEqual(backup['sha256'],hashlib.sha256((self.root/backup['file']).read_bytes()).hexdigest());self.image('dataset-outputs-wide.png')
    def test_reimport_does_not_duplicate_or_overwrite_approval(self):
        identifier=self.approve();before=self.app.detail(identifier);self.tab('transfer');self.page.locator('#import').click();expect(self.page.locator('#message')).to_contain_text('Import saved');self.assertEqual(self.app.state()['total'],4);self.assertEqual(self.app.detail(identifier),before)
    def test_invalid_batch_keeps_store_and_requires_explicit_refresh(self):
        (self.root/'inbox/invalid.jsonl').write_bytes(b'{"text":"Fictional valid prefix","group":"sample"}\nnull');self.tab('transfer');self.page.locator('#import-file').fill('inbox/invalid.jsonl');self.page.locator('#import').click();expect(self.page.locator('#message')).to_have_text('OPERATION_UNCERTAIN_REFRESH_REQUIRED');self.assertEqual(self.app.state()['total'],0);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.refresh();expect(self.page.locator('#message')).to_contain_text('Saved state refreshed');self.assertFalse(self.app.state()['refresh_required'])
    def test_outside_path_refused_without_echo(self):
        self.tab('transfer');self.page.locator('#import-file').fill('../invented-private-path.jsonl');self.page.locator('#import').click();expect(self.page.locator('#message')).to_have_text('OPERATION_REFUSED');self.assertEqual(self.app.state()['total'],0)
    def test_credential_pattern_cannot_be_approved(self):
        (self.root/'inbox/invented-pattern.jsonl').write_bytes(a.encode(dict(text='gh'+'p_'+'x'*30,group='sample')));self.tab('transfer');self.page.locator('#import-file').fill('inbox/invented-pattern.jsonl');self.page.locator('#import').click();expect(self.page.locator('#message')).to_contain_text('Import saved');self.tab('records');self.page.locator('#rows button').click();expect(self.page.locator('#message')).to_contain_text('Saved record loaded');self.review_fields();self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('NEW_REDACTED_RECORD_REQUIRED');self.assertEqual(self.app.state()['counts']['approved'],0)
    def test_literal_text_and_notes_never_render_or_fetch_markup(self):
        value='<img src=https://example.invalid/x onerror=window.fixtureExecuted=true>';(self.root/'inbox/markup.jsonl').write_bytes(a.encode(dict(text=value,group='sample')));self.tab('transfer');self.page.locator('#import-file').fill('inbox/markup.jsonl');self.page.locator('#import').click();expect(self.page.locator('#message')).to_contain_text('Import saved');self.tab('records');self.page.locator('#rows button').click();expect(self.page.locator('#message')).to_contain_text('Saved record loaded');self.review_fields(note=value);self.page.locator('#review').click();expect(self.page.locator('#message')).to_contain_text('Local review saved');expect(self.page.locator('#body')).to_have_text(value);expect(self.page.locator('#detail')).to_contain_text(value);self.assertEqual(self.page.locator('img').count(),0);self.assertIsNone(self.page.evaluate('window.fixtureExecuted'));self.assertTrue(all(url.startswith(self.url) for _,url in self.requests))
    def test_lost_review_reply_blocks_replay_until_explicit_refresh(self):
        self.load();identifier=self.select_train();self.review_fields()
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/review',lost);self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(self.app.detail(identifier)['reviews']),1);self.page.locator('#review').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(sum(url.endswith('/api/review') for _,url in self.requests),1);self.page.unroute('**/api/review');self.refresh(True);expect(self.page.locator('#message')).to_contain_text('Saved state refreshed');self.assertEqual(len(self.app.detail(identifier)['reviews']),1)
    def test_lost_export_reply_leaves_one_artifact_without_replay(self):
        self.approve();self.tab('transfer')
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/export',lost);self.page.locator('#export').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.page.locator('#export').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(list((self.root/'exports').iterdir())),1);self.assertEqual(sum(url.endswith('/api/export') for _,url in self.requests),1);self.page.unroute('**/api/export');self.refresh();expect(self.page.locator('#message')).to_contain_text('Saved state refreshed')
    def test_failed_detail_fetch_never_rebinds_record_or_note(self):
        self.load();identifier=self.select_train();self.review_fields();self.page.locator('#discard').check();self.page.route('**/api/detail?*',lambda route:route.abort('failed'));self.page.locator('#rows button').first.click();expect(self.page.locator('#message')).to_have_text('READ_FAILED_DRAFT_RETAINED');expect(self.page.locator('#selection')).to_contain_text(identifier);expect(self.page.locator('#note')).to_have_value('Fictional evidence checked');self.page.unroute('**/api/detail?*')
    def test_partial_refresh_read_failure_keeps_prior_pin_and_draft(self):
        self.load();identifier=self.select_train();self.review_fields();before=self.page.locator('#head').text_content();self.page.route('**/api/detail?*',lambda route:route.abort('failed'));self.refresh(True);expect(self.page.locator('#message')).to_have_text('READ_FAILED_DRAFT_RETAINED');expect(self.page.locator('#head')).to_have_text(before);expect(self.page.locator('#note')).to_have_value('Fictional evidence checked');self.page.unroute('**/api/detail?*')
    def test_restart_reopens_private_store_without_import_or_review(self):
        identifier=self.approve();before=self.app.detail(identifier);self.server.shutdown();self.thread.join(5);self.app.close();self.app=a.Workbench(self.root);self.addCleanup(self.app.close);self.server.controller=self.app;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#message')).to_contain_text('Private store ready');self.assertEqual(self.app.detail(identifier),before)
    def test_narrow_keyboard_navigation_and_readable_scroll_table(self):
        self.load();self.select_train();self.page.set_viewport_size(dict(width=390,height=844));self.page.locator('#rows').focus();self.assertEqual(self.page.evaluate('document.activeElement.id'),'rows');self.assertGreaterEqual(self.page.locator('#rows table').bounding_box()['width'],700);self.assertGreater(self.page.locator('#rows').evaluate('(node)=>node.scrollWidth-node.clientWidth'),0);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.page.locator('[data-tab=transfer]').focus();self.page.keyboard.press('Enter');expect(self.page.locator('#import')).to_be_visible();self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390);self.image('dataset-transfer-narrow.png');self.tab('records');self.image('dataset-records-narrow.png')

    def test_pagination_and_status_split_filters(self):
        raw=b'\n'.join(a.encode(dict(text='Fictional numbered row '+str(i),group='sample-page',split='validation')) for i in range(105));(self.root/'inbox/pages.jsonl').write_bytes(raw);self.tab('transfer');self.page.locator('#import-file').fill('inbox/pages.jsonl');self.page.locator('#import').click();expect(self.page.locator('#message')).to_contain_text('Import saved');self.tab('records');self.assertEqual(self.page.locator('#rows tbody tr').count(),100);self.page.locator('#next').click();expect(self.page.locator('#page-info')).to_contain_text('offset 100');self.assertEqual(self.page.locator('#rows tbody tr').count(),5);self.page.locator('#previous').click();expect(self.page.locator('#page-info')).to_contain_text('offset 0');self.page.locator('#split').select_option('test');self.page.locator('#search').click();expect(self.page.locator('#page-info')).to_contain_text('0 of 0');self.page.locator('#split').select_option('validation');self.page.locator('#filter-status').select_option('approved');self.page.locator('#search').click();expect(self.page.locator('#page-info')).to_contain_text('0 of 0');self.page.locator('#filter-status').select_option('pending');self.page.locator('#search').click();expect(self.page.locator('#page-info')).to_contain_text('100 of 105')
    def test_copied_legacy_store_opens_in_browser_without_schema_or_source_change(self):
        legacy=self.parent/'legacy.sqlite3';core.initialize(legacy);core.import_records(legacy,self.root/'inbox/sample-records.jsonl');identifier=next(r['id'] for r in core.records(legacy) if r['split']=='train');core.review(legacy,identifier,'approved','sample_legacy','Fictional prior review',{k:True for k in core.CHECKS});before=legacy.read_bytes();target=self.parent/'copy';a.Workbench.initialize(target,legacy);self.server.shutdown();self.thread.join(5);self.app.close();self.root=target;self.app=a.Workbench(target);self.addCleanup(self.app.close);self.server.controller=self.app;self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.page.reload();expect(self.page.locator('#message')).to_contain_text('Private store ready');self.page.locator('[data-record="'+identifier+'"]').click();expect(self.page.locator('#message')).to_contain_text('Saved record loaded');expect(self.page.locator('#detail')).to_contain_text('sample_legacy');self.assertEqual(self.app.state()['counts']['approved'],1);self.assertEqual(legacy.read_bytes(),before)
        for key in core.CHECKS:expect(self.page.locator('#'+key)).not_to_be_checked()
    def test_lost_backup_reply_does_not_create_second_backup(self):
        self.tab('transfer')
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/backup',lost);self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.page.locator('#backup').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(len(list((self.root/'backups').iterdir())),1);self.assertEqual(sum(url.endswith('/api/backup') for _,url in self.requests),1);self.page.unroute('**/api/backup');self.refresh();expect(self.page.locator('#message')).to_contain_text('Saved state refreshed')
    def test_lost_import_reply_does_not_repeat_import(self):
        self.tab('transfer')
        def lost(route):response=route.fetch();self.assertEqual(response.status,200);route.abort('failed')
        self.page.route('**/api/import',lost);self.page.locator('#import').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.page.locator('#import').click();expect(self.page.locator('#message')).to_have_text('RESPONSE_UNCERTAIN_REFRESH_BEFORE_RETRY');self.assertEqual(self.app.state()['total'],4);self.assertEqual(sum(url.endswith('/api/import') for _,url in self.requests),1);self.page.unroute('**/api/import');self.refresh();expect(self.page.locator('#message')).to_contain_text('Saved state refreshed');self.assertEqual(self.page.locator('#rows tbody tr').count(),4)
