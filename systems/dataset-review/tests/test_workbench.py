"""Fresh fictional instance, pin, compatibility, report and interruption tests."""
from contextlib import closing
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from dataset_workbench import application as a,web
import review_store as core

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name);self.root=self.parent/'instance';a.Workbench.initialize(self.root);self.app=a.Workbench(self.root);self.addCleanup(self.app.close)
    def act(self,op,**values):return self.app.mutate(op,dict(expected=self.app.state()['head'],**values))
    def load(self):return self.act('import',file='inbox/sample-records.jsonl')
    def first(self):return next(r for r in self.app.state()['records'] if r['split']=='train')['id']
    def approve(self):return self.act('review',id=self.first(),decision='approved',actor='sample_reviewer',note='Fictional evidence review',checks={k:True for k in core.CHECKS})
    def put(self,raw,name='invented.jsonl'):
        path=self.root/'inbox'/name;path.write_bytes(raw);return 'inbox/'+name

class Application(Fixture):
    def test_empty_instance_and_no_automatic_import(self):self.assertEqual(self.app.state()['total'],0)
    def test_import_dedup_and_conservative_linked_holdout(self):
        result=self.load();self.assertEqual(result['result']['added'],4);self.assertEqual(self.app.state()['total'],4);self.assertEqual(sorted(r['split'] for r in self.app.state()['records']),['test','test','train','validation']);self.assertEqual(self.app.state()['counts']['pending'],4)
    def test_imported_approval_cannot_approve(self):
        self.act('import',file=self.put(b'{"text":"Fictional review bypass attempt","group":"sample","status":"approved","checks":{"quality":true}}'));self.assertEqual(self.app.state()['counts']['approved'],0)
    def test_reimport_retains_approval_and_source_rows(self):
        self.load();self.approve();before=self.app.detail(self.first());self.load();after=self.app.detail(self.first());self.assertEqual(before,after)
    def test_search_status_split_and_pagination(self):
        self.load();self.approve();self.assertEqual(self.app.state(query='CHECKLIST',status='approved',split='train')['matched'],1);self.assertEqual(len(self.app.state(limit=1,offset=1)['records']),1)
    def test_detail_provenance_and_linked_group_receipt(self):
        self.load();row=next(r for r in self.app.state()['records'] if r['split']=='test');detail=self.app.detail(row['id']);self.assertEqual(detail['linked_records'],2);self.assertEqual(detail['aliases'],['sample-gamma']);self.assertTrue(detail['provenance']);self.assertNotIn(str(self.root),json.dumps(detail))
    def test_missing_review_assertions_refuse_without_mutation(self):
        self.load();head=self.app.state()['head']
        with self.assertRaisesRegex(a.Refused,'FOUR_CHECKS_REQUIRED'):self.act('review',id=self.first(),decision='approved',actor='sample',note='Fictional',checks={k:False for k in core.CHECKS})
        self.assertEqual(head,self.app.state()['head'])
    def test_stale_review_after_group_promotion_is_refused(self):
        self.load();head=self.app.state()['head'];identifier=self.first();self.act('import',file=self.put(a.encode(dict(text=self.app.detail(identifier)['text'],group='sample-alpha',split='test'))))
        with self.assertRaisesRegex(a.Refused,'STALE_STATE'):self.app.mutate('review',dict(expected=head,id=identifier,decision='approved',actor='sample',note='Fictional',checks={k:True for k in core.CHECKS}))
        self.assertEqual(self.app.detail(identifier)['status'],'pending')
    def test_strict_request_shapes_and_booleans(self):
        self.load()
        with self.assertRaises(a.Refused):self.act('review',id=self.first(),decision='approved',actor='sample',note='Fictional',checks={k:1 for k in core.CHECKS})
        with self.assertRaises(a.Refused):self.act('backup',extra='invented')
    def test_obvious_credential_pattern_needs_new_redacted_record(self):
        token='gh'+'p_'+'x'*30;self.act('import',file=self.put(a.encode(dict(text=token,group='sample'))));identifier=self.app.state()['records'][0]['id']
        with self.assertRaisesRegex(a.Refused,'NEW_REDACTED_RECORD'):self.act('review',id=identifier,decision='approved',actor='sample',note='Fictional',checks={k:True for k in core.CHECKS})
        self.assertEqual(self.app.detail(identifier)['status'],'pending')
    def test_private_export_exact_bytes_manifest_and_no_replacement(self):
        self.load();self.approve();result=self.act('export')['result'];folder=self.root/result['directory'];raw=(folder/'approved.jsonl').read_bytes();identifier=self.first();expected=core.canonical(dict(id=identifier,text=self.app.detail(identifier)['text'],split='train'))+'\n';self.assertEqual(raw,expected.encode());self.assertEqual(result['manifest']['files']['approved.jsonl'],dict(bytes=len(raw),sha256=a.digest(raw)));self.assertFalse(result['manifest']['public_release_authorized']);self.assertNotEqual(result['directory'],self.act('export')['result']['directory'])
    def test_empty_export_and_stale_export_refusal(self):
        head=self.app.state()['head'];result=self.act('export')['result'];self.assertEqual(result['manifest']['records'],0);self.load();before=list((self.root/'exports').iterdir())
        with self.assertRaises(a.Refused):self.app.mutate('export',dict(expected=head))
        self.assertEqual(before,list((self.root/'exports').iterdir()))
    def test_database_backup_is_compatible_and_content_pinned(self):
        self.load();self.approve();head=self.app.state()['head'];result=self.act('backup')['result'];path=self.root/result['file'];self.assertEqual(a.digest(path.read_bytes()),result['sha256']);self.assertEqual(core.records(path),core.records(self.app.store));self.assertEqual(head,self.app.state()['head']);self.assertTrue(result['database_only'])
    def test_copy_legacy_store_to_new_workspace_preserves_logical_data(self):
        legacy=self.parent/'legacy.sqlite3';core.initialize(legacy);core.import_records(legacy,self.root/'inbox/sample-records.jsonl');before=legacy.read_bytes();target=self.parent/'copy';a.Workbench.initialize(target,legacy)
        with a.Workbench(target) as cloned:self.assertEqual(core.records(legacy),core.records(cloned.store));self.assertEqual(cloned.state()['total'],4)
        self.assertEqual(before,legacy.read_bytes())
    def test_legacy_cli_can_reopen_workbench_store(self):
        self.load();self.app.close();p=subprocess.run([sys.executable,'-B',str(APP/'review_store.py'),'--store',str(self.root/'database/review.sqlite3'),'list'],capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0);self.assertEqual(len(json.loads(p.stdout)),4)
    def test_view_limit_rolls_back_import_before_commit(self):
        self.load();head=self.app.state()['head'];source=self.put(a.encode(dict(text='Fictional extra record',group='sample-extra')))
        with patch.dict(a.LIMITS,records=4),self.assertRaises(a.Refused):self.act('import',file=source)
        self.assertEqual(self.app.state()['head'],head);self.assertEqual(self.app.state()['total'],4)
    def test_invalid_tail_is_atomic_and_requires_explicit_refresh(self):
        head=self.app.state()['head'];file=self.put(b'{"text":"Fictional","group":"sample"}\nnull')
        with self.assertRaisesRegex(a.Refused,'UNCERTAIN'):self.act('import',file=file)
        self.assertEqual(self.app.state()['head'],head)
        with self.assertRaisesRegex(a.Refused,'UNCERTAIN'):self.act('backup')
        self.app.state(refresh=True);self.assertGreater(self.act('backup')['result']['bytes'],0)
    def test_post_commit_failure_is_not_silently_replayed(self):
        original=core.import_records
        def failed(*args,**kwargs):original(*args,**kwargs);raise OSError('Invented late failure')
        with patch.object(core,'import_records',side_effect=failed),self.assertRaisesRegex(a.Refused,'UNCERTAIN'):self.load()
        self.assertEqual(self.app.state()['total'],4);self.assertTrue(self.app.state()['refresh_required']);self.app.state(refresh=True);self.assertFalse(self.app.state()['refresh_required'])
    def test_schema_and_sidecar_failures_leave_existing_store_unchanged(self):
        (self.root/'database/review.sqlite3-wal').write_bytes(b'fictional');before=self.app.store.read_bytes()
        with self.assertRaises(core.ReviewError):self.app.state()
        self.assertEqual(self.app.store.read_bytes(),before)
    def test_session_lock_and_stopped_recovery(self):
        with self.assertRaises(OSError):a.Workbench(self.root)
        self.app.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(a.Refused):a.recover(self.root,False)
        a.recover(self.root,True);self.assertFalse((self.root/'.session-lock').exists())
    def test_nonempty_lock_and_path_escape_refused(self):
        with self.assertRaises(Exception):self.app.local('../fictional')
        with self.assertRaises(Exception):self.app.local(str(self.parent/'outside.json'))
        self.app.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/record').write_bytes(b'fictional')
        with self.assertRaises(a.Refused):a.recover(self.root,True)
    def test_json_limits_duplicate_nonfinite_and_depth(self):
        for raw in (b'{"x":1,"x":2}',b'1e999',b'NaN',b'['*66+b'0'+b']'*66,b'x'*(a.MAX_BODY+1)):
            with self.subTest(raw=raw[:20]),self.assertRaises((ValueError,RecursionError)):a.decode(raw)
    def test_no_implicit_network_or_code_execution(self):
        with patch('socket.socket',side_effect=AssertionError('Unexpected network')),patch('subprocess.Popen',side_effect=AssertionError('Unexpected process')):self.load();self.approve();self.act('export');self.act('backup')
    def test_guard_checks_inside_same_write_transaction(self):
        self.load();head=self.app.state()['head'];before=self.app.detail(self.first())
        with core.connect(self.app.store) as con:self.app._guard(head)(con);self.assertTrue(con.in_transaction)
        with self.assertRaises(a.Refused):core.review(self.app.store,self.first(),'approved','sample','Fictional',{k:True for k in core.CHECKS},_guard=self.app._guard('0'*64))
        self.assertEqual(self.app.detail(self.first()),before)

class BrowserApi(Fixture):
    def setUp(self):super().setUp();self.server=web.LocalServer(('127.0.0.1',0),self.app);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def request(self,path='/',method='GET',value=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:con.request(method,path,body=None if value is None else a.encode(value),headers=headers if headers is not None else {'X-Outlands-Token':self.server.token,'Origin':'http://127.0.0.1:'+str(self.server.server_port),'Content-Type':'application/json'});res=con.getresponse();return res.status,res.read(),dict(res.getheaders())
        finally:con.close()
    def test_page_nonce_and_no_store(self):
        status,raw,headers=self.request();self.assertEqual(status,200);self.assertIn(self.server.nonce.encode(),raw);self.assertIn("script-src 'nonce-",headers['Content-Security-Policy']);self.assertEqual(headers['Cache-Control'],'no-store');self.assertNotIn(b'__SESSION_TOKEN__',raw)
    def test_read_requires_token_and_exact_host(self):self.assertEqual(self.request('/api/state',headers={})[0],403);self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
    def test_post_origin_type_and_token_are_mandatory(self):
        for headers in ({},{'X-Outlands-Token':self.server.token},{'X-Outlands-Token':self.server.token,'Origin':'https://example.invalid','Content-Type':'application/json'}):self.assertEqual(self.request('/api/backup','POST',dict(expected=self.app.state()['head']),headers)[0],400)
    def test_real_import_review_export_and_fixed_errors(self):
        status,raw,_=self.request('/api/import','POST',dict(expected=self.app.state()['head'],file='inbox/sample-records.jsonl'));self.assertEqual(status,200);self.assertEqual(self.app.state()['total'],4);code,body,_=self.request('/api/detail?id=fictional');self.assertEqual(code,400);self.assertEqual(json.loads(body),{'error':'OPERATION_REFUSED'});self.assertNotIn(str(self.root).encode(),body)
    def test_ambiguous_query_body_and_length_refused(self):
        self.assertEqual(self.request('/api/state?limit=2&limit=3')[0],400);self.assertEqual(self.request('/api/state?unknown=invented')[0],400);self.assertEqual(self.request('/api/backup?ignored=1','POST',{})[0],400)
    def test_external_bind_refused(self):
        with self.assertRaises(a.Refused):web.LocalServer(('0.0.0.0',0),self.app)

    def test_duplicate_headers_and_transfer_encoding_refused(self):
        for extra in ([('Host','127.0.0.1:'+str(self.server.server_port))],[('X-Outlands-Token',self.server.token)],[('Origin','http://127.0.0.1:'+str(self.server.server_port))],[('Content-Length','2')],[('Transfer-Encoding','chunked')],[('Content-Type','application/json')]):
            con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
            try:
                con.putrequest('POST','/api/backup',skip_host=True)
                for key,value in [('Host','127.0.0.1:'+str(self.server.server_port)),('X-Outlands-Token',self.server.token),('Origin','http://127.0.0.1:'+str(self.server.server_port)),('Content-Type','application/json'),('Content-Length','2')]+extra:con.putheader(key,value)
                con.endheaders(b'{}');res=con.getresponse();self.assertEqual(res.status,400);res.read()
            finally:con.close()
        self.assertEqual(list((self.root/'backups').iterdir()),[])

class Processes(unittest.TestCase):
    def test_actual_cli_server_shutdown_and_reopen(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as temp:
            root=Path(temp)/'instance';cmd=[sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(root)];p=subprocess.run(cmd+['demo'],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stdout);demo=json.loads(p.stdout);self.assertEqual(demo,dict(mode='FICTIONAL_DATASET_REVIEW_DEMO',records=4,approved=1,exported=1,backup_validated=True,public_release_authorized=False,external_system_writes=False));proc=subprocess.Popen(cmd+['serve'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            try:
                url=json.loads(proc.stdout.readline())['url'];port=int(url.rsplit(':',1)[1]);con=http.client.HTTPConnection('127.0.0.1',port,timeout=5);con.request('GET','/');res=con.getresponse();html=res.read();con.close();token=re.search(rb"const token='([^']+)'",html).group(1).decode();con=http.client.HTTPConnection('127.0.0.1',port,timeout=5);con.request('POST','/api/shutdown',body=b'{}',headers={'Origin':url,'X-Outlands-Token':token,'Content-Type':'application/json'});res=con.getresponse();self.assertEqual(res.status,200);res.read();con.close();out,err=proc.communicate(timeout=15);self.assertEqual(proc.returncode,0,err);self.assertFalse((root/'.session-lock').exists());self.assertEqual(subprocess.run(cmd+['status'],capture_output=True,timeout=15).returncode,0)
            finally:
                if proc.poll() is None:proc.kill();proc.communicate(timeout=10)
    def test_actual_idle_kill_requires_explicit_stopped_recovery(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as temp:
            root=Path(temp)/'instance';cmd=[sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(root)];subprocess.run(cmd+['init'],check=True,capture_output=True,timeout=15);proc=subprocess.Popen(cmd+['serve'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8')
            try:json.loads(proc.stdout.readline());proc.kill();proc.communicate(timeout=10);self.assertNotEqual(subprocess.run(cmd+['status'],capture_output=True,timeout=15).returncode,0);self.assertEqual(subprocess.run(cmd+['recover','--confirm-stopped'],capture_output=True,timeout=15).returncode,0);self.assertEqual(subprocess.run(cmd+['status'],capture_output=True,timeout=15).returncode,0)
            finally:
                if proc.poll() is None:proc.kill();proc.communicate(timeout=10)
