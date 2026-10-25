"""Synthetic owned fixtures only. No real customer records or external services."""
import contextlib
import csv
import gc
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tracker as t

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='outlands-tracker-')
        self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
        self.store=t.Store.create(self.path/'work.sqlite')
    def job(self,**updates):return self.store.new_job(dict(title='Fictional shelf',customer='Example A',**updates))
    def quote(self,job,**updates):return self.store.add_quote(job['id'],dict(amount='125.10',currency='USD',scope='Fictional scope',**updates),job['version'])
    def approve(self,job):return self.store.decide(job['id'],'approved','Fictional acceptance reference',job['version'])

class Core(Fixture):
    def test_reopen_persists_and_unicode(self):
        job=self.job(notes='Café 日本語');again=t.Store(self.store.path).get(job['id'])
        self.assertEqual(again['notes'],'Café 日本語');self.assertEqual(again['version'],1)
    def test_exact_decimal_no_float(self):
        self.assertEqual(t.amount('9999999.99'),999999999);self.assertEqual(t.amount('0.01'),1)
        self.assertEqual(t.display_amount(t.amount('125.10')),'125.10')
    def test_invalid_money_types_and_grammar(self):
        for value in [125.10,125,None,True,'1','1.0','01.00','1e2','-1.00','10000000.00',' NaN ','1,000.00']:
            with self.subTest(value=value),self.assertRaises(t.TrackerError):t.amount(value)
    def test_dates_and_job_fields(self):
        for raw in [{'title':'','customer':'A'},{'title':'A','customer':'B','follow_up':'2026-02-30'}, {'title':'A','customer':'B','secret':'x'}, {'title':'A','customer':'B','notes':'x\0'}]:
            with self.assertRaises(t.TrackerError):self.store.new_job(raw)
        self.assertEqual(t.day('2028-02-29'),'2028-02-29')
    def test_quote_revision_clears_approval_schedule(self):
        job=self.approve(self.quote(self.job()))
        job=self.store.set_status(job['id'],'scheduled',job['version'],'2026-12-01')
        job=self.quote(job)
        self.assertEqual(job['status'],'quoted');self.assertEqual(job['scheduled_date'],'')
        self.assertEqual(job['quotes'][0]['decision']['decision'],'approved');self.assertIsNone(job['quotes'][1]['decision'])
        with self.assertRaises(t.TrackerError):self.store.set_status(job['id'],'scheduled',job['version'],'2026-12-02')
    def test_decision_is_immutable(self):
        job=self.approve(self.quote(self.job()))
        with self.assertRaises(t.TrackerError):self.store.decide(job['id'],'rejected','Correction',job['version'])
        with self.store.connection(write=True) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE decisions SET decision=?',('rejected',))
    def test_quote_history_immutable(self):
        self.quote(self.job())
        with self.store.connection(write=True) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('DELETE FROM quotes')
    def test_rejected_revision_can_be_revised(self):
        job=self.quote(self.job());job=self.store.decide(job['id'],'rejected','Fictional rejection',job['version'])
        self.assertEqual(job['status'],'quoted');self.assertEqual(self.quote(job)['quotes'][-1]['revision'],2)
    def test_conflicting_writers_require_refresh(self):
        job=self.job();other=t.Store(self.store.path)
        self.store.edit_job(job['id'],{'notes':'first'},job['version'])
        with self.assertRaises(t.TrackerError):other.edit_job(job['id'],{'notes':'second'},job['version'])
        self.assertEqual(other.get(job['id'])['notes'],'first')
    def test_version_required_for_every_mutation(self):
        job=self.job()
        for version in [None,True,0,'1']:
            with self.assertRaises(t.TrackerError):self.store.edit_job(job['id'],{'notes':'x'},version)
            with self.assertRaises(t.TrackerError):self.store.add_quote(job['id'],{'amount':'1.00','currency':'USD','scope':'x'},version)
            with self.assertRaises(t.TrackerError):self.store.decide(job['id'],'approved','x',version)
            with self.assertRaises(t.TrackerError):self.store.set_status(job['id'],'cancelled',version)
    def test_full_workflow_and_archive(self):
        job=self.approve(self.quote(self.job()))
        for status,date in [('scheduled','2026-12-01'),('in_progress',''),('completed',''),('archived','')]:job=self.store.set_status(job['id'],status,job['version'],date)
        self.assertEqual(job['status'],'archived')
        with self.assertRaises(t.TrackerError):self.store.edit_job(job['id'],{'notes':'no'},job['version'])
        with self.assertRaises(t.TrackerError):self.quote(job)
    def test_invalid_transitions_and_appointment(self):
        job=self.job()
        for state,day in [('completed',''),('approved',''),('scheduled',''),('cancelled','2026-12-01')]:
            with self.assertRaises(t.TrackerError):self.store.set_status(job['id'],state,job['version'],day)
    def test_cancel_then_archive(self):
        job=self.job();job=self.store.set_status(job['id'],'cancelled',job['version']);job=self.store.set_status(job['id'],'archived',job['version'])
        self.assertEqual(job['status'],'archived')
    def test_due_filter_excludes_inactive(self):
        job=self.job(follow_up='2026-12-01');self.assertEqual(len(self.store.list_jobs(due_before='2026-12-01')),1)
        self.store.set_status(job['id'],'cancelled',job['version']);self.assertEqual(self.store.list_jobs(due_before='2026-12-01'),[])
    def test_sql_parameterization(self):
        job=self.job(notes="'); DROP TABLE jobs; --")
        self.assertEqual(self.store.get(job['id'])['notes'],"'); DROP TABLE jobs; --")
    def test_event_failure_rolls_back_job(self):
        with patch.object(t,'MAX_EVENTS',0),self.assertRaises(t.TrackerError):self.job()
        self.assertEqual(self.store.list_jobs(),[])
    def test_job_and_quote_limits_transactional(self):
        job=self.job()
        with patch.object(t,'MAX_JOBS',1),self.assertRaises(t.TrackerError):self.job()
        with patch.object(t,'MAX_QUOTES',0),self.assertRaises(t.TrackerError):self.quote(job)
        self.assertEqual(self.store.get(job['id'])['version'],1)
    def test_existing_and_unrelated_store_never_overwritten(self):
        raw=self.store.path.read_bytes()
        with self.assertRaises(t.TrackerError):t.Store.create(self.store.path)
        self.assertEqual(raw,self.store.path.read_bytes())
        unrelated=self.path/'other.sqlite';unrelated.write_bytes(b'not sqlite')
        with self.assertRaises(t.TrackerError):t.Store(unrelated)
        self.assertEqual(unrelated.read_bytes(),b'not sqlite')
    def test_missing_store_not_created(self):
        path=self.path/'missing.sqlite'
        with self.assertRaises(t.TrackerError):t.Store(path)
        self.assertFalse(path.exists())
    def test_input_duplicate_keys_and_numbers_rejected(self):
        path=self.path/'input.json'
        for data in ['{"title":"A","title":"B"}','{"amount":1.5}','{"amount":NaN}','[]']:
            path.write_text(data)
            with self.assertRaises(t.TrackerError):t.read_json(path)
    def test_backup_recovery_roundtrip(self):
        job=self.approve(self.quote(self.job()));folder=self.path/'backup';self.store.backup(folder)
        self.assertEqual(t.verify_backup(folder)['status'],'PASS')
        restored=self.path/'recovered.sqlite';t.restore_backup(folder,restored)
        self.assertEqual(t.Store(restored).get(job['id']),job)
        with self.assertRaises(t.TrackerError):t.restore_backup(folder,restored)
    def test_backup_includes_committed_wal(self):
        writer=sqlite3.connect(self.store.path)
        try:
            writer.execute('PRAGMA journal_mode=WAL');job=self.job(notes='WAL committed data')
            self.assertTrue(Path(str(self.store.path)+'-wal').exists())
            self.store.backup(self.path/'wal-backup');t.restore_backup(self.path/'wal-backup',self.path/'wal-recovered.sqlite')
            self.assertEqual(t.Store(self.path/'wal-recovered.sqlite').get(job['id'])['notes'],'WAL committed data')
        finally:writer.close()
    def test_backup_tamper_and_extra_files_refused(self):
        folder=self.path/'backup';self.store.backup(folder);(folder/'extra.txt').write_text('extra')
        with self.assertRaises(t.TrackerError):t.verify_backup(folder)
        (folder/'extra.txt').unlink();(folder/'store.sqlite').write_bytes(b'tampered')
        with self.assertRaises(t.TrackerError):t.restore_backup(folder,self.path/'never.sqlite')
        self.assertFalse((self.path/'never.sqlite').exists())
    def test_export_escape_csv_and_hashes(self):
        job=self.job(notes='<script>alert(1)</script>',contact='=SUM(1,1)');folder=self.path/'report'
        self.assertEqual(t.export_report(self.store,folder)['files'],5)
        page=(folder/'index.html').read_text();self.assertNotIn('<script>',page);self.assertIn('&lt;script&gt;',page)
        rows=list(csv.reader(io.StringIO((folder/'jobs.csv').read_text())));self.assertEqual(rows[1][3],"'=SUM(1,1)")
        for record in json.loads((folder/'MANIFEST.json').read_text())['files']:self.assertEqual(t.sha((folder/record['path']).read_bytes()),record['sha256'])
        self.assertEqual(json.loads((folder/'data.json').read_text())['jobs'][0]['id'],job['id'])
    def test_existing_output_and_precancel(self):
        folder=self.path/'existing';folder.mkdir();(folder/'keep').write_text('keep')
        with self.assertRaises(t.TrackerError):self.store.backup(folder)
        with self.assertRaises(t.TrackerError):t.export_report(self.store,folder)
        self.assertEqual((folder/'keep').read_text(),'keep')
        cancel=threading.Event();cancel.set()
        with self.assertRaises(t.TrackerError):self.store.backup(self.path/'cancelled',cancel)
        with self.assertRaises(t.TrackerError):t.export_report(self.store,self.path/'cancelled',cancel)
        self.assertFalse((self.path/'cancelled').exists())
    def test_symlink_store_rejected_when_available(self):
        link=self.path/'linked.sqlite'
        try:link.symlink_to(self.store.path)
        except OSError:self.skipTest('Native symlink privilege unavailable')
        with self.assertRaises(t.TrackerError):t.Store(link)
    def test_cli_demo_and_recovery(self):
        script=Path(t.__file__);demo=self.path/'demo.sqlite'
        for args in [('demo',str(demo)),('list',str(demo)),('backup',str(demo),str(self.path/'cli-backup')),('verify-backup',str(self.path/'cli-backup')),('restore',str(self.path/'cli-backup'),str(self.path/'cli-restored.sqlite'))]:
            result=subprocess.run([sys.executable,'-B',str(script),*args],capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr);json.loads(result.stdout)
        self.assertEqual(len(t.Store(self.path/'cli-restored.sqlite').list_jobs()),2)
    def test_cli_bad_input_controlled(self):
        result=subprocess.run([sys.executable,'-B',str(Path(t.__file__)),'show',str(self.store.path),'bad'],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2);self.assertEqual(json.loads(result.stderr)['status'],'FAIL');self.assertNotIn('Traceback',result.stderr)

class Desktop(Fixture):
    def setUp(self):
        super().setUp()
        import tkinter as tk
        try:self.root=tk.Tk()
        except tk.TclError:
            if os.environ.get('TRACKER_REQUIRE_TK')=='1':raise
            self.skipTest('Tk display unavailable; set TRACKER_REQUIRE_TK=1 to require it')
        from tracker_gui import App
        self.root.withdraw();self.app=App(self.root,self.store);self.root.update()
        self.addCleanup(self.cleanup_gui)
    def cleanup_gui(self):
        if self.app.worker:self.app.worker.join(12)
        self.app.dirty=False;self.app.close();del self.app;gc.collect()
    def pump(self):
        end=time.monotonic()+15
        while self.app.worker and self.app.worker.is_alive() and time.monotonic()<end:self.root.update();time.sleep(.01)
        self.root.update();self.app.poll()
        self.assertFalse(self.app.worker and self.app.worker.is_alive())
    def save_new(self):
        self.app.values['title'].set('Desktop fictional job');self.app.values['customer'].set('Example GUI');self.app.save();self.root.update()
        self.assertIsNotNone(self.app.loaded);return self.app.loaded
    def test_desktop_create_edit_reopen(self):
        job=self.save_new();self.app.notes.insert('1.0','Desktop note');self.app.save()
        self.assertEqual(t.Store(self.store.path).get(job['id'])['notes'],'Desktop note')
    def test_desktop_quote_decision_and_schedule(self):
        self.save_new();self.app.amount.set('40.25');self.app.scope.insert('1.0','Fictional desktop scope');self.app.quote()
        self.app.reference.set('Fictional recorded approval');self.app.decision('approved');self.app.appointment.set('2026-12-15');self.app.status()
        self.assertEqual(self.app.loaded['status'],'scheduled');self.assertEqual(self.app.loaded['quotes'][0]['amount'],'40.25')
    def test_desktop_history_is_readonly(self):
        self.save_new();self.assertEqual(str(self.app.history.cget('state')),'disabled');self.assertIn('job_created',self.app.history.get('1.0','end'))
    def test_desktop_conflict_surfaces_without_overwrite(self):
        job=self.save_new();self.store.edit_job(job['id'],{'notes':'Other writer'},job['version']);self.app.values['title'].set('Stale edit')
        with patch('tracker_gui.messagebox.showerror') as error:self.app.save();error.assert_called_once()
        self.assertEqual(self.store.get(job['id'])['title'],'Desktop fictional job')
    def test_desktop_background_backup_and_restore(self):
        job=self.save_new();folder=self.path/'desktop-backup'
        self.app.background(lambda:('done',self.store.backup(folder,self.app.cancel),str(folder)));self.pump()
        restored=self.path/'desktop-restored.sqlite'
        self.app.background(lambda:('restored',t.restore_backup(folder,restored),str(restored)));self.pump()
        self.assertEqual(self.app.store.path,restored);self.assertEqual(self.app.store.get(job['id'])['title'],job['title'])
    def test_desktop_filters_and_unsaved_guard(self):
        self.save_new();self.app.values['title'].set('Unsaved')
        with patch('tracker_gui.messagebox.askyesno',return_value=False):self.app.refresh()
        self.assertTrue(self.app.dirty);self.assertEqual(self.app.values['title'].get(),'Unsaved')

if __name__=='__main__':unittest.main()
