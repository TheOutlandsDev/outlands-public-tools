"""Fresh local stores and invented records only. No installed model is contacted."""
import gzip
from contextlib import closing
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from workbench import corpus,models,runtime,web
from workbench.demo import FictionalClient,run


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'))
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(runtime.close)
        self.root=Path(self.temporary.name)/'instance'
        runtime.configure(self.root,create=True)
        corpus.initialize()
    def fixture(self,name,raw):
        path=self.root/'inbox'/name
        runtime.write_new(path,raw)
        return path
    def load(self):
        models.load_benchmarks()
        return corpus.import_jsonl('inbox/sample-corpus.jsonl')
    def approve(self):
        for row in corpus.list_records(limit=100)['records']:
            corpus.review_record(row['id'],'approved','sample_reviewer','Fictional independent checks',dict(quality=True,privacy=True,rights=True,context=True))


class Instance(Fixture):
    def test_full_fictional_application(self):
        result=run()
        self.assertEqual(result['imported'],dict(inserted=4,duplicate_provenance=1))
        self.assertEqual(result['benchmark_runs'],6)
        self.assertEqual(result['discussion_turns'],4)
        self.assertEqual(result['discussion_training_status'],'pending')
        self.assertFalse(result['real_inference_verified'])
        self.assertFalse(result['generated_code_executed'])
        self.assertEqual(result['sft_counts'],{'train.jsonl':1,'test.jsonl':1})
        self.assertEqual(result['rag_counts'],{'rag_chunks':1})
        self.assertEqual(result['embeddings_written'],1)
    def test_no_implicit_model_backend(self):
        with self.assertRaisesRegex(runtime.WorkbenchError,'MODEL_URL_REQUIRED'):models.discover()
    def test_empty_store(self):
        self.assertEqual(corpus.status()['records'],0)
        self.assertEqual(models.recommend('python')['model'],None)
    def test_dedup_and_provenance(self):
        self.load();self.load()
        self.assertEqual(corpus.status()['records'],4)
        self.assertEqual(corpus.status()['provenance_links'],5)
    def test_holdout_and_train_rag_separation(self):
        self.load();self.approve()
        self.assertEqual(corpus.status()['split'],{'test':2,'train':2})
        exported=corpus.export_dataset('rag')
        rows=list(runtime.jsonl(exported['directory']+'/rag.jsonl'))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1]['metadata']['split'],'train')
    def test_pending_not_exported(self):
        self.load()
        self.assertEqual(corpus.export_dataset('sft')['manifest']['counts'],{})
    def test_all_review_checks_required(self):
        self.load();identifier=corpus.list_records()['records'][0]['id']
        with self.assertRaises(ValueError):corpus.review_record(identifier,'approved','sample','note',{'quality':True})
        self.assertEqual(corpus.get_record(identifier)['status'],'pending')
    def test_boolean_review_checks_not_truthy_numbers(self):
        self.load();identifier=corpus.list_records()['records'][0]['id']
        with self.assertRaises(ValueError):corpus.review_record(identifier,'approved','sample','note',dict.fromkeys(('quality','privacy','rights','context'),1))
    def test_search_quotes_are_not_sql(self):
        self.load()
        self.assertEqual(corpus.list_records('Python')['total'],4)
        self.assertEqual(corpus.list_records('unknownterm OR 1=1')['total'],0)
    def test_export_hashes(self):
        self.load();self.approve();result=corpus.export_dataset('sft')
        for name,item in result['manifest']['files'].items():
            raw=runtime.read_bytes(self.root/result['directory']/name)
            self.assertEqual(item['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(item['bytes'],len(raw))
    def test_backup_is_independent_valid_store(self):
        self.load();result=corpus.backup()
        path=self.root/result['file']
        with closing(sqlite3.connect(path)) as con:
            runtime.validate_schema(con)
            self.assertEqual(con.execute('select count(*) from records').fetchone()[0],4)
        self.assertEqual(result['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
    def test_private_paths_not_in_status(self):
        self.assertNotIn(str(self.root),json.dumps(corpus.status()))
    def test_malformed_import_rolls_back(self):
        good=(APP/'examples/sample-corpus.jsonl').read_bytes().splitlines()[0]
        self.fixture('invalid.jsonl',good+b'\n{\n')
        with self.assertRaises(runtime.WorkbenchError):corpus.import_jsonl('inbox/invalid.jsonl')
        self.assertEqual(corpus.status()['records'],0)
        self.assertEqual(corpus.status()['sources'],0)
    def test_gzip_import(self):
        self.fixture('sample.jsonl.gz',gzip.compress((APP/'examples/sample-corpus.jsonl').read_bytes()))
        self.assertEqual(corpus.import_jsonl('inbox/sample.jsonl.gz')['inserted'],4)
    def test_gzip_expansion_bound(self):
        self.fixture('oversize.jsonl.gz',gzip.compress(b'x'*(runtime.MAX_INPUT+1)))
        with self.assertRaisesRegex(runtime.WorkbenchError,'IMPORT_LIMIT'):list(runtime.jsonl('inbox/oversize.jsonl.gz'))
    def test_record_size_bound(self):
        self.fixture('oversize.jsonl',b' '+b'x'*runtime.MAX_RECORD)
        with self.assertRaisesRegex(runtime.WorkbenchError,'IMPORT_LIMIT'):list(runtime.jsonl('inbox/oversize.jsonl'))
    def test_parent_escape_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('../outside',False)
    def test_source_as_private_instance_refused(self):
        runtime.close()
        with self.assertRaises((runtime.WorkbenchError,ValueError)):runtime.configure(APP,create=True)
    def test_new_files_never_replace(self):
        path=self.fixture('new.txt',b'first')
        with self.assertRaises(runtime.WorkbenchError):runtime.write_new(path,b'second')
        self.assertEqual(path.read_bytes(),b'first')
    def test_write_once_detects_conflict(self):
        path=self.fixture('once.txt',b'first')
        runtime.write_once(path,b'first')
        with self.assertRaisesRegex(runtime.WorkbenchError,'EXISTING_OUTPUT_CONFLICT'):runtime.write_once(path,b'changed')
    def test_schema_addition_refused(self):
        with closing(sqlite3.connect(corpus.DB)) as con:
            con.execute('CREATE TABLE unexpected(value)');con.commit()
        with self.assertRaisesRegex(runtime.WorkbenchError,'STORE_SCHEMA_REFUSED'):corpus.status()
    def test_store_version_refused(self):
        with closing(sqlite3.connect(corpus.DB)) as con:con.execute('PRAGMA user_version=2')
        with self.assertRaisesRegex(runtime.WorkbenchError,'STORE_VERSION_REFUSED'):corpus.status()
    def test_sidecar_refused(self):
        (self.root/'database/corpus.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(runtime.WorkbenchError):corpus.status()
    def test_second_session_refused(self):
        result=subprocess.run([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'status'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('INSTANCE_BUSY_OR_STALE',result.stdout)
        self.assertNotIn(str(self.root),result.stdout+result.stderr)
    def test_stale_lock_requires_explicit_assertion(self):
        runtime.close();(self.root/'.session-lock').mkdir()
        with self.assertRaisesRegex(runtime.WorkbenchError,'INSTANCE_BUSY_OR_STALE'):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True)
        self.assertEqual(corpus.status()['records'],0)
    def test_nonempty_stale_lock_refused(self):
        runtime.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/item').write_bytes(b'x')
        with self.assertRaisesRegex(runtime.WorkbenchError,'LOCK_REFUSED'):runtime.configure(self.root,confirm_stopped=True)
    def test_recovery_never_replays(self):
        models.load_benchmarks()
        with runtime.connect() as con:
            con.execute("INSERT INTO benchmark_runs(id,case_id,model,model_digest,status,request_json,created_utc) VALUES('sample','sample_case_0','fictional-model-a',?,'running','{}','fictional')",('a'*64,))
        result=runtime.recover()
        self.assertEqual(result['benchmark_runs_held'],1);self.assertFalse(result['automatically_replayed'])
    def test_fake_comparisons_require_manual_scores(self):
        models.load_benchmarks();runtime.set_client(FictionalClient())
        result=models.benchmark(['fictional-model-a'])
        self.assertTrue(models.recommend('python')['fallback'])
        for row in result['runs']:models.score(row['id'],4,'sample','Invented score')
        self.assertFalse(models.recommend('python')['fallback'])
        with runtime.connect() as con:
            self.assertNotIn('not retained',' '.join(row[0] for row in con.execute('SELECT answer FROM benchmark_runs')))
    def test_scoring_rejects_nonfinite(self):
        for value in (math.nan,math.inf,-1,6):
            with self.subTest(value=value),self.assertRaises(ValueError):models.score('missing',value,'sample','note')
    def test_prompt_budget_prevents_client_call(self):
        fake=FictionalClient();runtime.set_client(fake)
        with self.assertRaises(ValueError):models.chat('fictional-model-a',[{'role':'user','content':'x'*20000}])
        self.assertEqual(fake.calls['chat'],0)
    def test_failed_model_diagnostic_is_fixed(self):
        class Failing(FictionalClient):
            def request(self,endpoint,payload):
                if endpoint=='/api/chat':raise RuntimeError('invented-private-text')
                return super().request(endpoint,payload)
        runtime.set_client(Failing());models.load_benchmarks()
        result=models.benchmark(['fictional-model-a'])
        self.assertEqual({r['error'] for r in result['runs']},{'MODEL_OPERATION_FAILED'})
        self.assertNotIn('invented-private-text',json.dumps(models.overview()))
    def test_benchmark_definition_immutable(self):
        models.load_benchmarks()
        row=json.loads((APP/'examples/coding_devops_v1.jsonl').read_text(encoding='utf-8').splitlines()[0]);row['prompt']='Changed fictional case'
        self.fixture('changed.jsonl',json.dumps(row).encode())
        with self.assertRaises(ValueError):models.load_benchmarks('inbox/changed.jsonl')
    def test_linked_groups_promote_holdout(self):
        self.load()
        row=json.loads((APP/'examples/sample-corpus.jsonl').read_text(encoding='utf-8').splitlines()[0]);row['group_id']='fictional-new-group';row['split']='test'
        self.fixture('linked.jsonl',json.dumps(row).encode());corpus.import_jsonl('inbox/linked.jsonl')
        self.assertEqual(corpus.status()['records'],4)
        self.assertEqual(corpus.status()['split']['test'],3)
    def test_generated_discussion_stays_pending_and_queue_idempotent(self):
        runtime.set_client(FictionalClient())
        result=models.discuss('Fictional task','fictional-model-a','fictional-model-b','fictional-model-a',rounds=1)
        self.assertFalse(result['independently_verified'])
        self.assertTrue(models.queue_discussion(result['id'])['inserted'])
        self.assertFalse(models.queue_discussion(result['id'])['inserted'])
        record=corpus.get_record(corpus.list_records()['records'][0]['id'])
        self.assertEqual(record['status'],'pending');self.assertIn('model_review_only',record['flags'])
    def test_fts_and_vectors_require_approved_train_docs(self):
        self.load();runtime.set_client(FictionalClient())
        self.assertEqual(corpus.embed_corpus('fictional-model-a')['chunks_written'],0)
        self.approve();self.assertEqual(corpus.embed_corpus('fictional-model-a')['chunks_written'],1)
        self.assertEqual(len(corpus.semantic_search('Python','fictional-model-a')),1)
    def test_bad_embedding_vector(self):
        class Invalid(FictionalClient):
            def request(self,endpoint,payload):return {'embeddings':[[math.nan]]}
        runtime.set_client(Invalid())
        with self.assertRaisesRegex(runtime.WorkbenchError,'MODEL_VECTOR_INVALID'):runtime.model_request('/api/embed',{})
    def test_jsonl_bad_shapes_roll_back(self):
        for index,row in enumerate(([],None,{'kind':'unknown'},{'kind':'example','messages':[]})):
            self.fixture(str(index)+'.jsonl',json.dumps(row).encode())
            with self.assertRaises((ValueError,AttributeError,TypeError)):corpus.import_jsonl('inbox/'+str(index)+'.jsonl')
            self.assertEqual(corpus.status()['records'],0)
    def _link(self,kind):
        destination=self.root/'inbox/linked'
        source=self.root/'inbox/sample-corpus.jsonl'
        try:
            if kind=='hardlink':os.link(source,destination)
            elif kind=='directory':os.symlink(self.root/'inbox',self.root/'linked-directory',target_is_directory=True)
            else:os.symlink(source,destination)
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native fixture creation required')
            self.skipTest('Native link fixture unavailable on this filesystem')
        return self.root/'linked-directory/sample-corpus.jsonl' if kind=='directory' else destination
    def test_native_hardlink_input_refused(self):
        path=self._link('hardlink')
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(path)
    def test_native_symlink_input_refused(self):
        path=self._link('symlink')
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(path)
    def test_native_directory_link_refused(self):
        path=self._link('directory')
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(path)
    def test_native_database_hardlink_refused(self):
        try:os.link(corpus.DB,self.root/'database/alias.sqlite3')
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native fixture creation required')
            self.skipTest('Native link fixture unavailable on this filesystem')
        with self.assertRaises(runtime.WorkbenchError):corpus.status()
    @unittest.skipIf(os.name=='nt','POSIX-only special file')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream syntax')
    def test_windows_stream_name_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('inbox/sample-corpus.jsonl:stream')
    def test_actual_child_termination_requires_recovery(self):
        runtime.close()
        process=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--fictional-models','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            line=process.stdout.readline()
            self.assertEqual(json.loads(line)['mode'],'LOOPBACK_CORPUS_UI')
            process.kill();process.communicate(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=10)
        self.assertTrue((self.root/'.session-lock').is_dir())
        with self.assertRaisesRegex(runtime.WorkbenchError,'INSTANCE_BUSY_OR_STALE'):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True)
        self.assertFalse(runtime.recover()['automatically_replayed'])


class LoopbackModel(Fixture):
    def setUp(self):
        super().setUp()
        class LocalHandler(BaseHTTPRequestHandler):
            mode='tags'
            def log_message(self,*args):pass
            def do_GET(self):
                if self.mode=='redirect':
                    self.send_response(302);self.send_header('Location','https://example.invalid');self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                self.wfile.write(b'{"models":[]}' if self.mode=='tags' else b'{"models":NaN}')
        self.handler=LocalHandler
        self.server=ThreadingHTTPServer(('127.0.0.1',0),LocalHandler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.url='http://localhost:'+str(self.server.server_port)
    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def test_actual_loopback_request_ignores_proxy(self):
        with patch.dict(os.environ,{'http_proxy':'http://example.invalid','HTTP_PROXY':'http://example.invalid'}):
            self.assertEqual(runtime.model_request('/api/tags',url=self.url),{'models':[]})
    def test_actual_redirect_is_refused(self):
        self.handler.mode='redirect'
        with self.assertRaisesRegex(runtime.WorkbenchError,'MODEL_REDIRECT_REFUSED'):runtime.model_request('/api/tags',url=self.url)
    def test_actual_nonfinite_response_is_refused(self):
        self.handler.mode='invalid'
        with self.assertRaisesRegex(runtime.WorkbenchError,'JSON_NUMBER_INVALID'):runtime.model_request('/api/tags',url=self.url)


class JsonRules(unittest.TestCase):
    def test_duplicate_keys(self):
        with self.assertRaisesRegex(runtime.WorkbenchError,'JSON_DUPLICATE_KEY'):runtime.decode(b'{"x":1,"x":2}')
    def test_nonfinite_and_exponent_overflow(self):
        for text in (b'NaN',b'Infinity',b'-Infinity',b'1e999'):
            with self.subTest(text=text),self.assertRaises(runtime.WorkbenchError):runtime.decode(text)
    def test_depth_limit(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.decode(b'['*66+b'0'+b']'*66)
    def test_invalid_utf8(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.decode(bytes([255]))
    def test_external_or_credentialed_urls_refused(self):
        for url in ('https://example.invalid','http://example.invalid','http://name:pass@127.0.0.1','http://127.0.0.1/api','http://127.0.0.1?x=1','http://127.0.0.1#part','http://127.0.0.1:99999','http://localhost\n'):
            with self.subTest(url=url),self.assertRaises(runtime.WorkbenchError):runtime.validate_url(url)
    def test_localhost_is_literal(self):
        self.assertEqual(runtime.validate_url('http://localhost:1234/'),'http://127.0.0.1:1234')
        self.assertEqual(runtime.validate_url('http://[::1]:1234'),'http://[::1]:1234')


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp()
        self.server=web.ThreadingHTTPServer(('127.0.0.1',0),web.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,path='/',method='GET',raw=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            client.request(method,path,body=raw,headers=headers or {})
            response=client.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:client.close()
    def test_browser_page_and_no_cache(self):
        status,body,headers=self.request()
        self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),body)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
        self.assertNotIn(b'__SESSION_TOKEN__',body)
    def test_fictional_banner(self):
        runtime.set_client(FictionalClient())
        self.assertIn(b'FICTIONAL MODEL DEMONSTRATION',self.request()[1])
    def test_api_read_requires_token(self):
        self.assertEqual(self.request('/api/status')[0],403)
        self.assertEqual(self.request('/api/status',headers={'X-Outlands-Token':web.TOKEN})[0],200)
    def test_host_rebinding_refused(self):
        self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
    def test_cross_origin_write_refused(self):
        self.assertEqual(self.request('/api/backup','POST',b'{}',{'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403)
    def test_write_requires_token(self):
        self.assertEqual(self.request('/api/backup','POST',b'{}')[0],403)
    def test_json_duplicate_rejected_by_api(self):
        self.assertEqual(self.request('/api/backup','POST',b'{"x":1,"x":2}',{'X-Outlands-Token':web.TOKEN})[0],400)
    def test_nonobject_write_refused(self):
        for raw in (b'null',b'[]',b'1'):
            with self.subTest(raw=raw):self.assertEqual(self.request('/api/backup','POST',raw,{'X-Outlands-Token':web.TOKEN})[0],400)
    def test_transfer_encoding_write_refused(self):
        self.assertEqual(self.request('/api/backup','POST',b'{}',{'X-Outlands-Token':web.TOKEN,'Transfer-Encoding':'chunked'})[0],400)
    def test_duplicate_framing_and_host_refused(self):
        for field,expected in (('Content-Length',400),('Host',403)):
            client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
            try:
                client.putrequest('POST','/api/backup',skip_host=True)
                client.putheader('Host','127.0.0.1:'+str(self.server.server_port));client.putheader('Content-Length','2');client.putheader('X-Outlands-Token',web.TOKEN)
                client.putheader(field,'2' if field=='Content-Length' else '127.0.0.1:'+str(self.server.server_port));client.endheaders(b'{}')
                response=client.getresponse();self.assertEqual(response.status,expected);response.read()
            finally:client.close()
    def test_error_body_does_not_include_path(self):
        status,raw,_=self.request('/api/record?id=missing',headers={'X-Outlands-Token':web.TOKEN})
        self.assertEqual(status,400);self.assertEqual(json.loads(raw),{'error':'OPERATION_FAILED'})


if __name__=='__main__':unittest.main()
