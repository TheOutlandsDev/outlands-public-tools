"""Fictional regression cases for current-content approvals and native I/O."""
from contextlib import closing
import json
import os
import sqlite3
import subprocess
import threading
import unittest
from unittest import mock
from test_workbench import Fixture
from workbench import corpus,models,runtime,web
from workbench.demo import FictionalClient

CHECKS=dict(quality=True,privacy=True,rights=True,context=True)

class Contracts(Fixture):
    def supplemental(self):
        self.fixture('dialogue.jsonl',b'{"event_id":1,"kind":"message","data":{"role":"user","text":"Invented preceding question"}}\n')
        row=dict(kind='example',messages=[dict(role='user',content='Invented target question'),dict(role='assistant',content='Invented target answer')],metadata=dict(supplement_root='inbox',context=dict(relative_path='dialogue.jsonl',preceding_events=[1,1],completeness='fictional')))
        self.fixture('supplement.jsonl',json.dumps(row).encode());corpus.import_jsonl('inbox/supplement.jsonl')
        return corpus.list_records()['records'][0]['id']
    def test_supplement_changed_after_approval_is_not_exported(self):
        identifier=self.supplemental();self.approve()
        self.assertEqual(corpus.export_dataset('sft')['manifest']['counts'],{'train.jsonl':1})
        (self.root/'inbox/dialogue.jsonl').write_text('{"event_id":1,"kind":"message","data":{"role":"user","text":"Changed invented context"}}\n',encoding='utf-8')
        result=corpus.export_dataset('sft')['manifest']
        self.assertEqual(result['counts'],{});self.assertEqual(result['skipped'],[dict(id=identifier,reason='CURRENT_CONTENT_REVIEW_REQUIRED')])
        self.approve();self.assertEqual(corpus.export_dataset('sft')['manifest']['counts'],{'train.jsonl':1})
    def test_old_approval_keeps_store_compatible_but_requires_review_for_sft(self):
        self.load();self.approve()
        with runtime.connect() as con:con.execute('UPDATE reviews SET checks_json=?',(json.dumps(CHECKS),))
        result=corpus.export_dataset('sft')['manifest'];self.assertFalse(result['training_ready']);self.assertEqual(len(result['skipped']),2)
        self.approve();self.assertEqual(sum(corpus.export_dataset('sft')['manifest']['counts'].values()),2)
    def test_approval_rejects_unavailable_supplement_and_stays_pending(self):
        identifier=self.supplemental();(self.root/'inbox/dialogue.jsonl').unlink()
        with self.assertRaises(ValueError):corpus.review_record(identifier,'approved','sample','Fictional note',CHECKS)
        self.assertEqual(corpus.get_record(identifier)['status'],'pending')
    def test_no_supplement_still_enforces_materialization_limit(self):
        self.load();identifier=next(r['id'] for r in corpus.list_records()['records'] if r['kind']=='example')
        with self.assertRaises(ValueError):corpus.materialize(identifier,10)
    def test_invalid_materialization_limits_refused(self):
        self.load();identifier=corpus.list_records()['records'][0]['id']
        for value in (True,0,-1,200001,'20'):
            with self.subTest(value=value),self.assertRaises(ValueError):corpus.materialize(identifier,value)
    def test_late_benchmark_promotes_existing_records_and_duplicate_family(self):
        corpus.import_jsonl('inbox/sample-corpus.jsonl');self.assertEqual(corpus.status()['split'],dict(train=3,test=1))
        models.load_benchmarks();self.assertEqual(corpus.status()['split'],dict(train=2,test=2))
        models.load_benchmarks();self.assertEqual(corpus.status()['split'],dict(train=2,test=2))
    def test_late_benchmark_removes_existing_document_family_from_rag(self):
        corpus.import_jsonl('inbox/sample-corpus.jsonl')
        with runtime.connect() as con:
            group=con.execute("SELECT group_id FROM records WHERE title='Fictional heldout match'").fetchone()[0]
            con.execute("UPDATE records SET group_id=? WHERE title='Fictional Python reference'",(group,))
        self.approve();self.assertEqual(corpus.export_dataset('rag')['manifest']['counts'],{'rag_chunks':1})
        models.load_benchmarks();self.assertEqual(corpus.export_dataset('rag')['manifest']['counts'],{})
    def test_revocation_removes_preexisting_vector_from_search(self):
        self.load();self.approve();runtime.set_client(FictionalClient());corpus.embed_corpus('fictional-model-a')
        self.assertEqual(len(corpus.semantic_search('Python','fictional-model-a')),1)
        record=next(r['id'] for r in corpus.list_records()['records'] if r['title']=='Fictional Python reference')
        corpus.review_record(record,'pending','sample','Recheck fictional document',dict.fromkeys(CHECKS,False))
        self.assertEqual(corpus.semantic_search('Python','fictional-model-a'),[]);self.assertEqual(models.approved_rag_notes('Python'),[])
    def test_failed_export_never_writes_manifest_or_success_event(self):
        self.load();self.approve()
        with mock.patch.object(runtime.BoundedText,'write',side_effect=runtime.WorkbenchError('EXPORT_LIMIT')):
            with self.assertRaises(ValueError):corpus.export_dataset('sft')
        self.assertFalse(any((folder/'manifest.json').exists() for folder in (self.root/'exports').iterdir()))
        self.assertTrue(all(not list(folder.iterdir()) for folder in (self.root/'exports').iterdir()))
        with runtime.connect() as con:self.assertEqual(con.execute("SELECT COUNT(*) FROM events WHERE action='export'").fetchone()[0],0)
    def test_malformed_messages_do_not_change_store(self):
        for i,value in enumerate(('invalid',[None],[dict(role='user',content='question',extra='unknown')])):
            self.fixture(str(i)+'.jsonl',json.dumps(dict(messages=value)).encode())
            with self.assertRaises(ValueError):corpus.import_jsonl('inbox/'+str(i)+'.jsonl')
            self.assertEqual(corpus.status()['records'],0)
    def test_review_unknown_or_nonboolean_checks_refused(self):
        self.load();identifier=corpus.list_records()['records'][0]['id']
        for value in ({**CHECKS,'extra':True},{**CHECKS,'context':1},[],None):
            with self.subTest(value=value),self.assertRaises(ValueError):corpus.review_record(identifier,'pending','sample','Fictional note',value)
    def test_missing_schema_version_is_fixed_refusal(self):
        with closing(sqlite3.connect(corpus.DB)) as con:con.execute("DELETE FROM meta WHERE key='schema_version'");con.commit()
        with self.assertRaisesRegex(runtime.WorkbenchError,'STORE_VERSION_REFUSED'):corpus.status()
    def test_invalid_model_catalog_rows_are_refused(self):
        class Invalid:
            def request(self,endpoint,payload):return dict(models=self.rows)
        client=Invalid();runtime.set_client(client)
        for rows in ([None],[{}],[dict(name='sample',digest='a'),dict(name='sample',digest='b')],[dict(name='sample\n',digest='a')],[dict(name='sample',digest='a',details=[])]):
            client.rows=rows
            with self.subTest(rows=rows),self.assertRaisesRegex(runtime.WorkbenchError,'MODEL_RESPONSE_INVALID'):models.discover()
        self.assertEqual(models.overview()['models'],[])
    def test_generic_skipped_context_reason_contains_no_native_exception(self):
        self.load();self.approve()
        with mock.patch.object(corpus,'materialize',side_effect=ValueError('invented-private-marker')):result=corpus.export_dataset('sft')
        self.assertNotIn('invented-private-marker',json.dumps(result));self.assertTrue(result['manifest']['skipped'])
    def test_native_junction_or_directory_link_export_parent_refused(self):
        alias=self.root/'linked-exports';target=self.root/'exports'
        try:
            if os.name=='nt':
                p=subprocess.run(['cmd','/c','mklink','/J',str(alias),str(target)],capture_output=True)
                if p.returncode:raise OSError('Native junction unavailable')
            else:os.symlink(target,alias,target_is_directory=True)
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native fixture required')
            self.skipTest('Native link fixture unavailable')
        try:
            with self.assertRaises(runtime.WorkbenchError):runtime.write_new(alias/'new.txt',b'invented')
            self.assertFalse((target/'new.txt').exists())
        finally:
            if os.name=='nt':alias.rmdir()
            else:alias.unlink()
    def test_native_workspace_metadata_hardlink_refused(self):
        try:os.link(self.root/'workspace.json',self.root/'metadata-alias.json')
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native fixture required')
            self.skipTest('Native link fixture unavailable')
        runtime.close()
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(self.root)
    def test_owned_worker_drain_waits_and_blocks_another_job(self):
        web.STOPPING=False;web.drain_jobs();web.JOBS.clear();entered=threading.Event();release=threading.Event();drained=threading.Event()
        def action():entered.set();release.wait(5);return dict(fictional=True)
        job=web.launch_job(action);self.assertTrue(entered.wait(2))
        waiter=threading.Thread(target=lambda:(web.drain_jobs(),drained.set()));waiter.start()
        try:
            self.assertFalse(drained.wait(.05))
            with self.assertRaises(ValueError):web.launch_job(lambda:None)
        finally:release.set();waiter.join(5)
        self.assertTrue(drained.is_set());self.assertEqual(web.JOBS[job['job_id']]['status'],'complete')

    def test_import_hash_and_rows_use_same_bounded_snapshot(self):
        path=self.root/'inbox/sample-corpus.jsonl';before=path.read_bytes();original=corpus.register_source
        def changed(con,selected,collection,note,raw=None):
            selected.write_bytes(b'{"kind":"document","text":"Changed invented file"}\n')
            return original(con,selected,collection,note,raw)
        with mock.patch.object(corpus,'register_source',side_effect=changed):corpus.import_jsonl('inbox/sample-corpus.jsonl')
        self.assertEqual(corpus.status()['records'],4)
        import hashlib
        with runtime.connect() as con:
            source=con.execute('SELECT sha256,bytes FROM sources').fetchone()
            self.assertEqual(tuple(source),(hashlib.sha256(before).hexdigest(),len(before)))
