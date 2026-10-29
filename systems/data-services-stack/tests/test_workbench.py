"""Fictional browser-controller and real loopback HTTP boundaries."""
from base import APP,Fixture,fictional_configuration,fictional_input
from copy import deepcopy
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest import mock
from data_services import files
from data_services.contracts import StackError,canonical,decode,digest
from data_services.service import Stack
from data_services.workbench import Workbench
from data_services.web import LocalServer,MAX_BODY

class Controller(Fixture):
    def setUp(self):
        super().setUp();self.create();self.app=Stack(self.root);self.addCleanup(self.app.close);self.controller=Workbench(self.app,self.parent/'reports');self.addCleanup(self.controller.close)
    def call(self,action,**data):
        if action not in ('overview','fixtures','inspect'):data=dict(expected_head=self.app.head,**data)
        return self.controller.apply(action,data)
    def preview(self,content=None):return self.call('preview',job_id='sample',content=fictional_input().decode() if content is None else content)
    def run_job(self,key='notice',content=None):
        content=fictional_input().decode() if content is None else content;p=self.preview(content);return self.call('run',job_id='sample',key=key,content=content,preview_sha256=p['preview_sha256'])
    def export(self,key='notice',**updates):
        selected=self.call('inspect',key=key);data=dict(key=key,result_sha256=selected['result_sha256'],review=dict(actor='sample_reviewer',note='Invented independent review',checks=dict.fromkeys(('quality','privacy','rights','context'),True)));data.update(updates);return self.call('export',**data)
    def test_preview_is_nonmutating_and_independent_numeric_oracle(self):
        before=self.hashes();p=self.preview();self.assertTrue(p['clean']);self.assertEqual(p['estimate']['forecast'],[dict(series='sample',period=i,value=10) for i in (6,7,8)]);self.assertEqual(p['estimate']['score'],dict(count=3,mae=4,rmse=4));self.assertEqual(self.hashes(),before);self.assertEqual(self.app.queue(),[])
    def test_duplicate_preview_and_csv_follow_public_ingestion_rules(self):
        raw=fictional_input().decode();p=self.preview(raw+'\n'+raw.splitlines()[0]);self.assertEqual(p['duplicates'],1);self.assertTrue(p['clean'])
        config=decode(fictional_configuration());config['jobs'][0]['input_format']='csv';self.call('configure',configuration=canonical(config).decode());p=self.preview(self.call('fixtures')['csv']);self.assertTrue(p['clean']);self.assertEqual(p['estimate']['accepted'],6)
    def test_invalid_row_diagnostics_omit_payload_and_do_not_create_run(self):
        p=self.preview('{"series":"invented-invalid-marker","period":0,"value":null}');self.assertFalse(p['clean']);self.assertNotIn('invented-invalid-marker',json.dumps(p));self.assertTrue(p['issues']);self.assertEqual(self.app.status()['runs'],[])
    def test_noncontiguous_or_insufficient_series_block_preview(self):
        for raw in ('{"series":"sample","period":0,"value":2}',fictional_input().decode().replace('"period":2','"period":9')):
            self.assertFalse(self.preview(raw)['clean'])
    def test_changed_input_refuses_old_preview_without_creating_run(self):
        p=self.preview();before=self.hashes()
        with self.assertRaisesRegex(StackError,'PREVIEW_PIN_MISMATCH'):self.call('run',job_id='sample',key='notice',content=fictional_input().decode()+'\n',preview_sha256=p['preview_sha256'])
        self.assertEqual(self.hashes(),before)
    def test_changed_configuration_refuses_stale_journal_head(self):
        p=self.preview();old=self.app.head;config=decode(fictional_configuration());config['jobs'][0]['window']=2;self.call('configure',configuration=canonical(config).decode())
        with self.assertRaisesRegex(StackError,'JOURNAL_HEAD_CONFLICT'):self.controller.apply('run',dict(expected_head=old,job_id='sample',key='notice',content=fictional_input().decode(),preview_sha256=p['preview_sha256']))
    def test_preview_is_rechecked_even_when_caller_supplies_its_hash(self):
        p=self.preview('null');self.assertFalse(p['clean'])
        with self.assertRaisesRegex(StackError,'BATCH_REVIEW_REQUIRED'):self.call('run',job_id='sample',key='notice',content='null',preview_sha256=p['preview_sha256'])
    def test_run_replay_is_idempotent_and_changed_content_conflicts(self):
        self.run_job();head=self.app.head;self.run_job();self.assertEqual(self.app.head,head);self.assertEqual(len(self.app.queue()),1)
        with self.assertRaisesRegex(StackError,'RUN_IDEMPOTENCY_CONFLICT'):self.run_job(content=fictional_input().decode()+'\n')
    def test_reconfiguration_preserves_saved_job_snapshot(self):
        self.run_job();before=self.app.result('notice');config=decode(fictional_configuration());config['jobs'][0]['method']='last';self.call('configure',configuration=canonical(config).decode());self.assertEqual(self.app.result('notice'),before)
    def test_retry_due_tick_acceptance_and_no_replay(self):
        self.run_job();first=self.call('dispatch',now=0,limit=1,outcomes=['retry']);self.assertEqual(first['queue'][0]['next_attempt'],1);self.assertEqual(self.call('dispatch',now=0,limit=1,outcomes=[])['fake_calls'],0);self.assertEqual(self.call('dispatch',now=1,limit=1,outcomes=[])['queue'][0]['state'],'ACCEPTED');self.assertEqual(self.call('dispatch',now=100,limit=1,outcomes=[])['fake_calls'],0)
    def test_unknown_and_interrupted_outcomes_are_held_without_replay(self):
        self.run_job('first');self.call('dispatch',now=0,limit=1,outcomes=['accepted_then_unknown']);self.run_job('second');result=self.call('dispatch',now=1,limit=1,outcomes=['interrupt']);self.assertEqual(result['state'],'INTERRUPTED_REVIEW_REQUIRED');self.assertEqual({q['state'] for q in self.app.queue()},{'REVIEW_REQUIRED'});self.assertEqual(self.call('dispatch',now=100,limit=1,outcomes=[])['fake_calls'],0)
    def test_delivery_assertion_requires_checkbox_and_matching_receipt(self):
        self.run_job();self.call('dispatch',now=0,limit=1,outcomes=[])
        with self.assertRaisesRegex(StackError,'DELIVERY_ASSERTION_REQUIRED'):self.call('report-delivery',key='notice',receipt='fake_receipt',assertion=False)
        with self.assertRaisesRegex(StackError,'DELIVERY_REPORT_REFUSED'):self.call('report-delivery',key='notice',receipt='wrong_receipt',assertion=True)
        result=self.call('report-delivery',key='notice',receipt='fake_receipt',assertion=True);self.assertFalse(result['real_delivery_verified']);self.assertEqual(self.app.queue()[0]['state'],'DELIVERY_REPORTED')
    def test_monotonic_clock_and_invalid_fake_outcomes_do_not_send(self):
        self.run_job();self.call('dispatch',now=5,limit=1,outcomes=['retry'])
        for data in (dict(now=4,limit=1,outcomes=[]),dict(now=6,limit=True,outcomes=[]),dict(now=6,limit=1,outcomes=['provider'])):
            before=self.hashes()
            with self.assertRaises(StackError):self.call('dispatch',**data)
            self.assertEqual(self.hashes(),before)
    def test_reports_have_verified_primary_bytes_hashes_and_no_input_snapshot(self):
        self.run_job();before=self.hashes();result=self.export();folder=self.parent/'reports'/result['directory'];manifest=result['manifest'];self.assertEqual(set(p.name for p in folder.iterdir()),{'run.json','review.json','manifest.json'})
        for name,item in manifest['files'].items():self.assertEqual(item,dict(bytes=len((folder/name).read_bytes()),sha256=digest((folder/name).read_bytes())))
        self.assertEqual(decode((folder/'run.json').read_bytes()),self.app.result('notice'));self.assertFalse(manifest['source_input_included']);self.assertFalse(manifest['public_release_authorized']);self.assertEqual(self.hashes(),before)
    def test_report_requires_fresh_complete_review_and_exact_result_pin(self):
        self.run_job()
        for change in (dict(result_sha256='0'*64),dict(review=dict(actor='sample',note='Invented note',checks=dict(quality=True)))):
            with self.assertRaises(StackError):self.export(**change)
        self.assertEqual(list((self.parent/'reports').iterdir()),[])
    def test_rejected_runs_cannot_be_exported_as_completed_results(self):
        self.app.run('sample','bad',b'null')
        with self.assertRaisesRegex(StackError,'COMPLETED_RUN_REQUIRED'):self.export('bad')
    def test_report_write_failure_retains_partial_and_has_no_manifest(self):
        self.run_job();original=files.write_new
        def fail(path,raw):
            if Path(path).name=='review.json':raise StackError('INVENTED_WRITE_FAILURE')
            return original(path,raw)
        with mock.patch.object(files,'write_new',side_effect=fail),self.assertRaises(StackError):self.export()
        folder=next((self.parent/'reports').iterdir());self.assertTrue((folder/'run.json').exists());self.assertFalse((folder/'manifest.json').exists());self.assertEqual(self.app.queue()[0]['state'],'PENDING')
    def test_reports_are_new_only_and_do_not_replace_previous_report(self):
        self.run_job();one=self.export();folder=self.parent/'reports'/one['directory'];before={p.name:p.read_bytes() for p in folder.iterdir()};two=self.export();self.assertNotEqual(one['directory'],two['directory']);self.assertEqual({p.name:p.read_bytes() for p in folder.iterdir()},before)
    def test_report_root_cannot_overlap_journal_or_source(self):
        for root in (self.root/'reports',APP/'forbidden-reports',self.root):
            with self.assertRaises(StackError):Workbench(self.app,root)
    def test_report_capacity_refuses_before_creating_directory(self):
        self.run_job()
        with mock.patch('data_services.workbench.MAX_REPORTS',0),self.assertRaisesRegex(StackError,'REPORT_CAPACITY'):self.export()
        self.assertEqual(list((self.parent/'reports').iterdir()),[])
    def test_recovery_required_instance_can_be_inspected_but_not_run(self):
        state=deepcopy(self.app._state);state['runs']['interrupted']=dict(job=state['jobs']['sample'],input_sha256=digest(fictional_input()),fingerprint='placeholder',state='RUNNING',code='RUN_STARTED',result=None)
        from data_services.state import fingerprint
        state['runs']['interrupted']['fingerprint']=fingerprint(state['jobs']['sample'],digest(fictional_input()));self.app.commit(state)
        self.assertTrue(self.call('overview')['recovery_required'])
        with self.assertRaisesRegex(StackError,'RECOVERY_REQUIRED'):self.preview()
    def test_no_provider_or_arbitrary_path_operations_exist(self):
        for action in ('send-email','recover','open-file','run-command'):
            with self.assertRaisesRegex(StackError,'OPERATION_REFUSED'):self.controller.apply(action,{})
    def test_unknown_fields_and_invalid_unicode_are_refused(self):
        with self.assertRaisesRegex(StackError,'REQUEST_SCHEMA_INVALID'):self.controller.apply('overview',dict(extra=True))
        with self.assertRaises(StackError):self.preview('\ud800')
    def test_finite_json_and_depth_limits_apply_before_use(self):
        for raw in (b'{"x":1e999}',b'['*66+b'0'+b']'*66):
            with self.assertRaises(StackError):decode(raw)
    def test_native_report_root_link_refused(self):
        alias=self.parent/'report-alias';target=self.parent/'real-reports';target.mkdir()
        try:
            if os.name=='nt':
                p=subprocess.run(['cmd','/c','mklink','/J',str(alias),str(target)],capture_output=True)
                if p.returncode:raise OSError('Native fixture unavailable')
            else:os.symlink(target,alias,target_is_directory=True)
        except OSError:
            if os.environ.get('STACK_REQUIRE_LINKS')=='1':self.fail('Native fixture required')
            self.skipTest('Native link fixture unavailable')
        try:
            with self.assertRaises(StackError):Workbench(self.app,alias)
        finally:
            if os.name=='nt':alias.rmdir()
            else:alias.unlink()

class HttpBoundary(Fixture):
    def setUp(self):
        super().setUp();self.create();self.app=Stack(self.root);self.addCleanup(self.app.close);self.controller=Workbench(self.app,self.parent/'reports');self.addCleanup(self.controller.close);self.server=LocalServer(('127.0.0.1',0),self.controller);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(5)
    def request(self,path='/',method='GET',raw=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            c.request(method,path,body=raw,headers=headers or {});response=c.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:c.close()
    def headers(self):return {'Content-Type':'application/json','X-Outlands-Token':self.server.token,'Origin':'http://127.0.0.1:'+str(self.server.server_port)}
    def test_real_page_has_nonce_csp_no_store_no_referrer(self):
        code,raw,h=self.request();self.assertEqual(code,200);self.assertIn(b'FAKE TRANSPORT ONLY',raw);self.assertIn(self.server.token.encode(),raw);self.assertNotIn(b'__SCRIPT_NONCE__',raw);self.assertIn("script-src 'nonce-",h['Content-Security-Policy']);self.assertNotIn("script-src 'unsafe-inline'",h['Content-Security-Policy']);self.assertEqual(h['Cache-Control'],'no-store');self.assertEqual(h['Referrer-Policy'],'no-referrer')
    def test_real_browser_api_requires_token_and_exact_origin(self):
        self.assertEqual(self.request('/api/overview','POST',b'{}')[0],403)
        for origin in ('https://example.invalid','null','http://localhost:'+str(self.server.server_port)):
            headers=self.headers();headers['Origin']=origin;self.assertEqual(self.request('/api/overview','POST',b'{}',headers)[0],403)
        self.assertEqual(self.request('/api/overview','POST',b'{}',self.headers())[0],200)
    def test_bad_host_get_and_static_path_traversal_refused(self):
        self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
        self.assertEqual(self.request('/data_services/workbench.py')[0],404);self.assertEqual(self.request('/../stack.py')[0],404)
    def test_nonobject_and_duplicate_json_refused(self):
        for raw in (b'null',b'[]',b'{"x":1,"x":2}'):
            self.assertEqual(self.request('/api/overview','POST',raw,self.headers())[0],400)
    def test_oversized_and_ambiguous_transfer_framing_refused(self):
        headers=self.headers();headers['Content-Length']=str(MAX_BODY+1);self.assertEqual(self.request('/api/overview','POST',b'{}',headers)[0],400)
        headers=self.headers();headers['Transfer-Encoding']='chunked';self.assertEqual(self.request('/api/overview','POST',b'{}',headers)[0],400)
    def test_content_type_required_and_errors_do_not_echo_private_text(self):
        headers=self.headers();headers['Content-Type']='text/plain';self.assertEqual(self.request('/api/overview','POST',b'{}',headers)[0],400)
        code,raw,_=self.request('/api/inspect','POST',b'{"key":"invented_missing"}',self.headers());self.assertEqual(code,400);self.assertNotIn(b'invented_missing',raw);self.assertNotIn(str(self.root).encode(),raw)
    def test_generic_exception_is_fixed_code(self):
        with mock.patch.object(self.controller,'apply',side_effect=RuntimeError('invented-private-marker')):code,raw,_=self.request('/api/overview','POST',b'{}',self.headers())
        self.assertEqual(json.loads(raw),dict(code='OPERATION_REFUSED'))
    def test_competing_http_mutations_with_one_pin_commit_only_once(self):
        head=self.app.head;config=decode(fictional_configuration());config['jobs'][0]['window']=2;payload=canonical(dict(expected_head=head,configuration=canonical(config).decode()));results=[]
        def mutate():results.append(self.request('/api/configure','POST',payload,self.headers())[0])
        threads=[threading.Thread(target=mutate) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(5)
        self.assertEqual(sorted(results),[200,400]);self.assertEqual(self.app.sequence,2)
    def test_duplicate_host_and_length_headers_refused(self):
        for field,expected in (('Host',403),('Content-Length',400)):
            c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
            try:
                c.putrequest('POST','/api/overview',skip_host=True);c.putheader('Host','127.0.0.1:'+str(self.server.server_port));c.putheader('Content-Length','2')
                for key,value in self.headers().items():c.putheader(key,value)
                c.putheader(field,'2' if field=='Content-Length' else '127.0.0.1:'+str(self.server.server_port));c.endheaders(b'{}');response=c.getresponse();self.assertEqual(response.status,expected);response.read()
            finally:c.close()


class ServeProcess(Fixture):
    def test_actual_serve_shutdown_releases_writer_lock_and_reopens(self):
        import re
        from urllib.parse import urlsplit
        self.create()
        child=subprocess.Popen([sys.executable,'-B',str(APP/'stack.py'),'--workspace',str(self.root),'serve','--reports',str(self.parent/'reports'),'--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            startup=json.loads(child.stdout.readline());self.assertEqual(startup['mode'],'FICTIONAL_DATA_SERVICES_UI');port=urlsplit(startup['url']).port
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            try:c.request('GET','/');response=c.getresponse();page=response.read().decode()
            finally:c.close()
            selected=re.search("const token='([^']+)'",page)[1]
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            headers={'Content-Type':'application/json','Origin':startup['url'],'X-Outlands-Token':selected}
            try:
                c.request('POST','/api/overview',body=b'{}',headers=headers);response=c.getresponse();head=json.loads(response.read())['result']['head_sha256']
            finally:c.close()
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            try:c.request('POST','/api/shutdown',body=canonical(dict(expected_head=head)),headers=headers);response=c.getresponse();self.assertEqual(response.status,200);response.read()
            finally:c.close()
            output,error=child.communicate(timeout=10);self.assertEqual((child.returncode,output,error),(0,'',''));self.assertFalse((self.root/'.writer-lock').exists())
            with Stack(self.root) as reopened:self.assertEqual(reopened.status()['runs'],[])
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
