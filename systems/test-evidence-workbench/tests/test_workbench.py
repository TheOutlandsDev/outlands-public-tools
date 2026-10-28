"""Invented checks and evidence; no original registry or operational input is run."""
import base64
import copy
from contextlib import closing
import http.client
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
from unittest import mock

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from evidence import application as app,contracts as c,jobs,runner,runtime as r,web


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.addCleanup(jobs.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.example=r.decode((APP/'examples/sample-cases.json').read_bytes());self.base=copy.deepcopy(self.example['cases'][0])
    def load(self):return app.import_bundle(r.encode(self.example))
    def save(self,value=None,expected=None):return app.save_case(r.encode(dict(definition=value or self.base,expected_sha256=expected)))
    def trust_request(self,record,status='approved',version=0):return dict(case_id=record['definition']['case_id'],case_sha256=record['sha256'],expected_version=version,status=status,actor='sample_operator',note='Fictional script trust',checks=dict(code_reviewed=True,authority=True,input_reviewed=True,effects_reviewed=True))
    def approve_case(self,identifier='sample-total'):
        record=app.case(identifier);app.trust(r.encode(self.trust_request(record,version=record['trust']['row_version'])));record=app.case(identifier);return dict(case_id=identifier,expected_sha256=record['sha256'],trust_version=record['trust']['row_version'])
    def run_case(self,value=None):
        value=value or self.base;self.save(value);pin=self.approve_case(value['case_id']);finished=jobs.wait(app.start_run(r.encode(dict(cases=[pin])))['job_id']);return app.artifact(finished['artifact_id'])
    def review_request(self,record,status='approved',version=0):return dict(artifact_id=record['artifact_id'],artifact_sha256=record['artifact_sha256'],expected_version=version,status=status,actor='sample_reviewer',note='Fictional evidence review',checks=dict(quality=True,privacy=True,rights=True,context=True))
    def wait_child(self,identifier):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with jobs.LOCK:children=list(jobs.JOBS[identifier]['control'].children)
            if children:return children[0]
            time.sleep(.01)
        self.fail('Owned child did not start')


class Contracts(Fixture):
    def test_strict_json_duplicate_nonfinite_and_depth(self):
        for raw in (b'{"n":1,"n":2}',b'{"n":NaN}',b'{"n":1e999}',b'['*70+b'0'+b']'*70):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)
    def test_exact_fields_refuse_commands_environment_and_paths(self):
        for key in ('executable','arguments','environment','cwd','credentials','shell'):
            value={**self.base,key:'fictional'}
            with self.subTest(key=key),self.assertRaises(r.WorkbenchError):c.definition(value)
    def test_portable_case_ids_and_boolean_timeouts_refused(self):
        for identifier in ('../sample','sample/name','Sample','sample:stream','a'*49):
            with self.assertRaises(r.WorkbenchError):c.token(identifier)
        for value in (True,99,5001,'1000'):
            with self.assertRaises(r.WorkbenchError):c.definition({**self.base,'timeout_ms':value})
    def test_script_input_expected_and_stderr_limits(self):
        values=[{**self.base,'script':'x'*32769},{**self.base,'input':[]},{**self.base,'input':{'s':'x'*17000}},{**self.base,'expected':{**self.base['expected'],'stdout':{'s':'x'*9000}}},{**self.base,'expected':{**self.base['expected'],'stderr':'x'*2049}}]
        for value in values:
            with self.assertRaises(r.WorkbenchError):c.definition(value)
    def test_safe_json_numeric_normalization_and_type_distinction(self):
        value=c.definition({**self.base,'input':{'n':1.0,'b':True}});self.assertIs(type(value['input']['n']),int);self.assertIs(type(value['input']['b']),bool)
        with self.assertRaises(r.WorkbenchError):c.definition({**self.base,'input':{'n':10**16}})
    def test_bundle_duplicates_and_suite_limits(self):
        with self.assertRaises(r.WorkbenchError):c.bundle(r.encode(dict(format='outlands-check-bundle-v1',cases=[self.base,self.base])))
        for items in ([],[dict(case_id='sample-total',expected_sha256='0'*64,trust_version=1)]*9):
            with self.assertRaises(r.WorkbenchError):c.suite(r.encode(dict(cases=items)))
    def test_invalid_text_and_unknown_expectation_fields(self):
        for text in ('x\0y','\ud800'):
            with self.assertRaises(r.WorkbenchError):c.text(text,100)
        with self.assertRaises(r.WorkbenchError):c.definition({**self.base,'expected':{**self.base['expected'],'anything':True}})


class RegistryAndTrust(Fixture):
    def test_import_and_trust_never_execute(self):
        with mock.patch.object(runner.subprocess,'Popen',side_effect=AssertionError('Execution forbidden')):self.load();self.approve_case()
        self.assertEqual(list((self.root/'runs').iterdir()),[]);self.assertEqual(app.artifacts()['artifacts'],[])
    def test_import_idempotence_and_atomic_conflict(self):
        self.load();self.assertTrue(all(not v['created'] for v in self.load()['cases']));value=copy.deepcopy(self.example);value['cases'][0]['case_id']='sample-new';value['cases'][1]['title']='Changed'
        with self.assertRaises(r.WorkbenchError):app.import_bundle(r.encode(value))
        self.assertEqual(len(app.cases()['cases']),4)
    def test_revision_hash_parent_and_old_source_preserved(self):
        self.save();old=app.case('sample-total');value={**self.base,'title':'Changed fictional title'};saved=self.save(value,old['sha256']);self.assertEqual(saved['version'],2);self.assertEqual(app.case('sample-total',1)['definition'],self.base);self.assertEqual(app.history('sample-total')['versions'][1]['parent_sha256'],old['sha256'])
    def test_stale_save_and_trust_refused(self):
        self.save();old=app.case('sample-total');self.save({**self.base,'title':'Changed'},old['sha256'])
        with self.assertRaises(r.WorkbenchError):self.save(self.base,old['sha256'])
        with self.assertRaises(r.WorkbenchError):app.trust(r.encode(self.trust_request(old)))
    def test_every_revision_requires_fresh_trust(self):
        self.save();self.approve_case();old=app.case('sample-total');self.save({**self.base,'timeout_ms':2500},old['sha256']);self.assertEqual(app.case('sample-total')['trust'],dict(status='pending',row_version=0))
    def test_trust_checks_strict_boolean_and_all_required(self):
        self.save();record=app.case('sample-total');value=self.trust_request(record);value['checks']['effects_reviewed']=False
        with self.assertRaises(r.WorkbenchError):app.trust(r.encode(value))
        value['checks']['effects_reviewed']=1
        with self.assertRaises(r.WorkbenchError):app.trust(r.encode(value))
    def test_trust_conflict_and_revocation_block_future_plan(self):
        self.save();pin=self.approve_case();record=app.case('sample-total');app.trust(r.encode(self.trust_request(record,'revoked',1)))
        with self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[pin])))
        with self.assertRaises(r.WorkbenchError):app.trust(r.encode(self.trust_request(record,'approved',1)))
    def test_entire_suite_preflight_before_any_child_or_run_directory(self):
        self.load();pin=self.approve_case();other=dict(case_id='sample-nonzero',expected_sha256=app.case('sample-nonzero')['sha256'],trust_version=1)
        with mock.patch.object(runner.subprocess,'Popen',side_effect=AssertionError('No child allowed')),self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[pin,other])))
        self.assertEqual(list((self.root/'runs').iterdir()),[])
    def test_stale_plan_case_or_trust_version_refused(self):
        self.save();pin=self.approve_case()
        with self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[{**pin,'trust_version':2}])))
        with self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[{**pin,'expected_sha256':'0'*64}])))


class ActualRunner(Fixture):
    def observed(self,value=None):return self.run_case(value)['payload']['result']['cases'][0]['observed']
    def test_real_sum_against_independent_oracle_and_input_pins(self):
        result=self.observed();self.assertTrue(result['passed']);self.assertEqual(result['stdout_json']['total'],sum(self.base['input']['values']));self.assertEqual(result['script_sha256'],r.digest(self.base['script'].encode()));self.assertEqual(result['input_sha256'],r.digest(r.encode(self.base['input'])))
    def test_expected_nonzero_and_crlf_normalized_stderr(self):
        result=self.observed(self.example['cases'][1]);self.assertTrue(result['passed']);self.assertEqual(result['exit_code'],3);self.assertEqual(result['streams']['stderr']['text'].replace('\r\n','\n'),'fictional refusal\n')
    def test_expected_mismatch_is_complete_unmatched_evidence(self):
        result=self.run_case(self.example['cases'][2])['payload']['result'];self.assertTrue(result['complete']);self.assertEqual(result['matched'],0);self.assertEqual(result['unmatched'],1);self.assertFalse(result['cases'][0]['observed']['matches']['stdout'])
    def test_timeout_reaps_owned_child_and_preserves_timeout_verdict(self):
        result=self.run_case(self.example['cases'][3])['payload']['result'];self.assertEqual(result['cases'][0]['observed']['status'],'timeout');self.assertEqual(result['matched'],0)
        with jobs.LOCK:children=[child for job in jobs.JOBS.values() for child in job['control'].children]
        self.assertTrue(all(child.poll() is not None for child in children))
    def test_stdout_and_stderr_capture_are_bounded_without_line_reads(self):
        value={**self.base,'script':'import sys\nsys.stdout.buffer.write(b"x" * 1000000)\nsys.stderr.buffer.write(b"y" * 1000000)\n','expected':dict(exit_code=0,stdout={},stderr='')};result=self.observed(value);self.assertEqual(result['status'],'output_limited');self.assertFalse(result['passed']);self.assertTrue(any(s['truncated'] for s in result['streams'].values()))
        for stream in result['streams'].values():self.assertLessEqual(stream['bytes'],runner.CAPTURE_LIMIT)
    def test_exact_limit_without_newline_is_accepted(self):
        value={**self.base,'script':'import sys\nsys.stdout.buffer.write(b"{}" + b" " * 16382)\n','expected':dict(exit_code=0,stdout={},stderr='')};result=self.observed(value);self.assertTrue(result['passed']);self.assertEqual(result['streams']['stdout']['bytes'],16384);self.assertFalse(result['streams']['stdout']['truncated'])
    def test_stderr_overflow_is_bounded_and_not_a_match(self):
        value={**self.base,'script':'import sys\nsys.stderr.buffer.write(b"x" * 1000000)\nprint("{}")\n','expected':dict(exit_code=0,stdout={},stderr='')};result=self.observed(value);self.assertEqual(result['status'],'output_limited');self.assertTrue(result['streams']['stderr']['truncated']);self.assertEqual(result['streams']['stderr']['bytes'],16384);self.assertFalse(result['passed'])
    def test_invalid_utf8_capture_has_exact_bytes_and_fails_match(self):
        value={**self.base,'script':'import sys\nsys.stdout.buffer.write(bytes([255]))\n'};result=self.observed(value);self.assertFalse(result['passed']);self.assertFalse(result['streams']['stdout']['utf8_valid']);self.assertEqual(base64.b64decode(result['streams']['stdout']['base64']),b'\xff')
    def test_malformed_duplicate_nonfinite_or_extra_stdout_json_cannot_match(self):
        for index,text in enumerate(('{"n":1,"n":2}','{"n":NaN}','{} {}')):
            value={**self.base,'case_id':'sample-json-'+str(index),'script':'print('+repr(text)+')\n','expected':dict(exit_code=0,stdout={},stderr='')};result=self.observed(value);self.assertFalse(result['stdout_json_valid']);self.assertFalse(result['passed'])
    def test_boolean_and_numeric_stdout_are_not_interchangeable(self):
        value={**self.base,'script':'print(\'{"n":true}\')\n','expected':dict(exit_code=0,stdout={'n':1},stderr='')};self.assertFalse(self.observed(value)['passed'])
    def test_environment_is_minimal_and_interpreter_is_isolated(self):
        script='import json, os, sys\nprint(json.dumps({"sentinel_absent": "OUTLANDS_FICTIONAL_SENTINEL" not in os.environ, "isolated": sys.flags.isolated, "no_site": sys.flags.no_site, "stdin_empty": sys.stdin.read() == ""}))\n';value={**self.base,'script':script,'expected':dict(exit_code=0,stdout=dict(sentinel_absent=True,isolated=1,no_site=1,stdin_empty=True),stderr='')}
        with mock.patch.dict(os.environ,OUTLANDS_FICTIONAL_SENTINEL='fictional-only'):result=self.observed(value)
        self.assertTrue(result['passed']);self.assertFalse(result['descendant_containment'])
    def test_explicit_trust_precedes_actual_local_effect(self):
        value={**self.base,'script':'from pathlib import Path\nprint("{}")\nPath("fictional-effect.txt").write_text("fictional")\n','expected':dict(exit_code=0,stdout={},stderr='')};self.save(value);record=app.case('sample-total');pin=dict(case_id='sample-total',expected_sha256=record['sha256'],trust_version=1)
        with self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[pin])))
        self.assertEqual(list((self.root/'runs').iterdir()),[]);self.approve_case();result=jobs.wait(app.start_run(r.encode(dict(cases=[pin])))['job_id']);self.assertEqual(result['status'],'completed');self.assertEqual(len(list((self.root/'runs').glob('*/fictional-effect.txt'))),1)
    def test_cancel_before_start_has_no_child_or_materialized_input(self):
        control=runner.Control();control.cancel();self.assertEqual(control.execute(self.base)['status'],'not_run');self.assertEqual(control.children,[]);self.assertEqual(list((self.root/'runs').iterdir()),[])


class OwnedLifecycle(Fixture):
    def start_slow(self,two=False):
        self.load();pins=[self.approve_case('sample-timeout')];revision=app.case('sample-timeout');definition={**revision['definition'],'timeout_ms':5000};self.save(definition,revision['sha256']);pins=[self.approve_case('sample-timeout')]
        if two:pins.append(self.approve_case('sample-total'))
        return app.start_run(r.encode(dict(cases=pins)))['job_id']
    def test_actual_owned_cancel_reaps_child_and_marks_remaining_not_run(self):
        identifier=self.start_slow(two=True);child=self.wait_child(identifier);jobs.cancel(identifier);finished=jobs.wait(identifier);self.assertIsNotNone(child.poll());result=app.artifact(finished['artifact_id'])['payload']['result'];self.assertFalse(result['complete']);self.assertEqual(result['cases'][0]['observed']['status'],'cancelled');self.assertEqual(result['cases'][1]['observed']['status'],'not_run')
    def test_active_shutdown_joins_owned_child(self):
        identifier=self.start_slow();child=self.wait_child(identifier);jobs.close();self.assertIsNotNone(child.poll());self.assertEqual(jobs.JOBS,{})
    def test_single_active_suite_and_finished_cancel_idempotence(self):
        identifier=self.start_slow();self.wait_child(identifier);pin=self.approve_case('sample-total')
        try:
            with self.assertRaises(r.WorkbenchError):app.start_run(r.encode(dict(cases=[pin])))
        finally:jobs.cancel(identifier);jobs.wait(identifier)
        self.assertFalse(jobs.cancel(identifier)['cancel_requested'])


class EvidenceReview(Fixture):
    def test_each_run_has_distinct_pending_review(self):
        first=self.run_case();app.review(r.encode(self.review_request(first)));pin=dict(case_id='sample-total',expected_sha256=app.case('sample-total')['sha256'],trust_version=1);second=app.artifact(jobs.wait(app.start_run(r.encode(dict(cases=[pin])))['job_id'])['artifact_id']);self.assertNotEqual(first['artifact_sha256'],second['artifact_sha256']);self.assertEqual(second['review'],dict(status='pending',row_version=0))
    def test_failed_check_evidence_can_be_reviewed_without_changing_verdict(self):
        record=self.run_case(self.example['cases'][2]);before=record['payload']['result'];app.review(r.encode(self.review_request(record)));self.assertEqual(app.artifact(record['artifact_id'])['payload']['result'],before);self.assertEqual(before['matched'],0)
    def test_cancelled_evidence_cannot_be_approved(self):
        self.save({**self.base,'script':'import time\ntime.sleep(10)\n','timeout_ms':5000});pin=self.approve_case();identifier=app.start_run(r.encode(dict(cases=[pin])))['job_id'];self.wait_child(identifier);jobs.cancel(identifier);record=app.artifact(jobs.wait(identifier)['artifact_id'])
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(self.review_request(record)))
    def test_review_boolean_checks_and_stale_versions(self):
        record=self.run_case();request=self.review_request(record);request['checks']['privacy']=False
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(request))
        request['checks']['privacy']=1
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(request))
        request['checks']['privacy']=True;app.review(r.encode(request))
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(request))
    def test_export_approval_and_revocation_gate(self):
        record=self.run_case()
        with self.assertRaises(r.WorkbenchError):app.export(record['artifact_id'])
        app.review(r.encode(self.review_request(record)));app.review(r.encode(self.review_request(record,'rejected',1)))
        with self.assertRaises(r.WorkbenchError):app.export(record['artifact_id'])
    def test_export_exact_raw_streams_hashes_and_historical_case_pins(self):
        record=self.run_case();app.review(r.encode(self.review_request(record)));old=app.case('sample-total');self.save({**self.base,'title':'New untrusted revision'},old['sha256']);result=app.export(record['artifact_id']);directory=self.root/result['directory'];self.assertFalse(result['manifest']['public_release_authorized'])
        actual={p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()};self.assertEqual(actual,set(result['manifest']['files'])|{'manifest.json'})
        for name,pin in result['manifest']['files'].items():raw=(directory/name).read_bytes();self.assertEqual(pin,dict(bytes=len(raw),sha256=r.digest(raw)))
        cases=r.decode((directory/'cases.json').read_bytes());self.assertEqual(cases[0]['case_sha256'],old['sha256']);capture=record['payload']['result']['cases'][0]['observed']['streams']['stdout'];self.assertEqual((directory/'captures/sample-total/stdout.bin').read_bytes(),base64.b64decode(capture['base64']))
    def test_comparison_marks_changed_revisions_and_different_case_sets(self):
        first=self.run_case();old=app.case('sample-total');self.save({**self.base,'title':'Revised'},old['sha256']);pin=self.approve_case();second=app.artifact(jobs.wait(app.start_run(r.encode(dict(cases=[pin])))['job_id'])['artifact_id']);comparison=app.compare(first['artifact_id'],second['artifact_id']);self.assertTrue(comparison['same_case_set']);self.assertFalse(comparison['cases'][0]['same_case_revision']);self.assertTrue(comparison['cases'][0]['same_captured_stream_hashes'])


class Store(Fixture):
    def test_append_only_and_schema_tamper_rejection(self):
        self.load()
        with self.assertRaises(sqlite3.IntegrityError):
            with r.connect() as con:con.execute('DELETE FROM cases')
        with r.connect() as con:con.execute('CREATE TABLE extra(value TEXT)')
        with self.assertRaises(r.WorkbenchError):app.cases()
    def test_store_budget_rolls_back_case_revision(self):
        self.save();old=app.case('sample-total')
        with mock.patch.object(r,'MAX_STORE',1),self.assertRaises(r.WorkbenchError):self.save({**self.base,'title':'Changed'},old['sha256'])
        self.assertEqual(app.case('sample-total'),old)
    def test_backup_schema_and_case_contents(self):
        self.load();result=app.backup();self.assertEqual(r.digest((self.root/result['file']).read_bytes()),result['sha256'])
        with closing(sqlite3.connect(self.root/result['file'])) as con:r.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM cases').fetchone()[0],4)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request_http(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=r.encode(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_no_store_and_token_substitution(self):
        status,raw,headers=self.request_http();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertNotIn(b'__SESSION_TOKEN__',raw);self.assertEqual(headers['Cache-Control'],'no-store')
    def test_read_write_token_host_and_origin_guards(self):
        self.assertEqual(self.request_http('/api/cases')[0],403);self.assertEqual(self.request_http('/api/backup','POST',{})[0],403);self.assertEqual(self.request_http(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request_http('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_fixed_errors_and_duplicate_query(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/artifact?id=bad',headers=headers);self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='ARTIFACT_ID_INVALID'));self.assertEqual(self.request_http('/api/case?id=a&id=b',headers=headers)[0],400)
    def test_real_trusted_run_through_http(self):
        self.save();pin=self.approve_case();status,raw,_=self.request_http('/api/run','POST',dict(cases=[pin]),{'X-Outlands-Token':web.TOKEN});self.assertEqual(status,200);finished=jobs.wait(json.loads(raw)['job_id']);self.assertEqual(app.artifact(finished['artifact_id'])['payload']['result']['matched'],1)


class Filesystem(Fixture):
    def test_source_and_parent_escape_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('../outside',False)
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP,create=True)
    def test_existing_output_never_replaced(self):
        path=self.root/'inbox/existing';r.write_new(path,b'original')
        with self.assertRaises(r.WorkbenchError):r.write_new(path,b'replacement')
        self.assertEqual(path.read_bytes(),b'original')
    def make_link(self,action):
        try:action()
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixture required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-cases.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.cases()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-cases.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-cases.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-cases.json:stream')
    def test_stale_lock_requires_stopped_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.cases(),dict(cases=[]))
    def test_actual_idle_child_termination_and_restart(self):
        self.load();r.close();child=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(child.stdout.readline())['mode'],'LOOPBACK_TEST_EVIDENCE_UI');child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(len(app.cases()['cases']),4)
