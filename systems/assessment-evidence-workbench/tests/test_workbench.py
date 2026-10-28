"""Fictional records, independent workflow outcomes and guarded I/O."""
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
import unittest
from unittest import mock

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from assessment import application as app,contracts as c,runtime as r,web

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.fixture=r.decode((APP/'examples/sample-assessment.json').read_bytes());self.identifier='sample_assessment'
    def load(self):return app.create(r.encode(self.fixture['create']))
    def current(self):return app.assessment(self.identifier)
    def act(self,command,pin=None):return app.act(r.encode(dict(assessment_id=self.identifier,expected_sha256=pin or self.current()['sha256'],command=command)))
    def steps(self,count=6):
        self.load()
        for command in self.fixture['commands'][:count]:self.act(command)
        return self.current()
    def command(self,index):return copy.deepcopy(self.fixture['commands'][index])
    def review(self):return dict(assessment_id=self.identifier,expected_sha256=self.current()['sha256'],actor='sample_reviewer',reason='Fictional private handoff',checks=dict(quality=True,privacy=True,rights=True,context=True))
    def refused(self,command,code=None):
        before=self.current()
        with self.assertRaises(r.WorkbenchError) as error:self.act(command)
        if code:self.assertEqual(str(error.exception),code)
        self.assertEqual(self.current(),before)

class Contracts(Fixture):
    def test_create_unknown_fields_and_missing_authorization(self):
        value=copy.deepcopy(self.fixture['create']);value['assessment']['extra']=True
        with self.assertRaises(r.WorkbenchError):app.create(r.encode(value))
        value=copy.deepcopy(self.fixture['create']);value['assessment']['authorization_reference']=''
        with self.assertRaises(r.WorkbenchError):app.create(r.encode(value))
        self.assertEqual(app.assessments(),dict(assessments=[]))
    def test_duplicate_nonfinite_depth_and_unicode_json(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*70+b'0'+b']'*70,b'\xff'):
            with self.subTest(raw=raw[:20]),self.assertRaises(r.WorkbenchError):r.decode(raw)
        for text in ('x\0y','\ud800'):
            with self.assertRaises(r.WorkbenchError):c.text(text)
    def test_strict_scalar_identifiers_and_limits(self):
        for value in (True,1.0,'1'):
            with self.assertRaises(r.WorkbenchError):c.integer(value)
        for value in ('../sample','a/b','a:stream','x'*41,'Upper'):
            with self.assertRaises(r.WorkbenchError):c.token(value)
    def test_receipt_exact_bytes_hash_and_no_filename(self):
        self.steps(1);row=self.current()['document']['submissions'][0];raw=b'Fictional inert receipt 1\n';self.assertEqual(row['receipt'],dict(bytes=len(raw),sha256=r.digest(raw),content_base64=base64.b64encode(raw).decode()));self.assertNotIn('filename',row)
    def test_receipt_invalid_encoding_empty_and_large(self):
        self.load()
        for value in ('','====','aGVsbG8=\n',base64.b64encode(b'x'*49153).decode()):
            command=self.command(0);command['data']['receipt_base64']=value;self.refused(command)
    def test_receipt_is_never_unpacked_or_executed(self):
        self.load();command=self.command(0);raw=b'PK\x03\x04<script>throw Error("invented")</script>\x00';command['data']['receipt_base64']=base64.b64encode(raw).decode();self.act(command);self.assertEqual(self.current()['document']['submissions'][0]['receipt']['sha256'],r.digest(raw));self.assertEqual(list((self.root/'inbox').iterdir()),[self.root/'inbox/sample-assessment.json'])
    def test_duplicate_global_ids_and_series_revisions(self):
        self.steps(1);command=self.command(1);command['data']['id']='sample_original';self.refused(command,'DUPLICATE_RECORD_ID');command=self.command(1);command['data']['revision']=1;self.refused(command,'DUPLICATE_SERIES_REVISION')
    def test_unknown_execution_commands_refused(self):
        self.load()
        for op in ('run','scan','unpack','worker','shell','install'):
            self.refused(dict(operation=op,actor='sample_actor',reason='Fictional',data={}), 'CHOICE_INVALID')

class Workflow(Fixture):
    def test_complete_manual_resolution_and_immutable_old_state(self):
        value=self.steps();self.assertEqual(value['document']['findings'][0]['state'],'Resolved');self.assertFalse(value['execution_performed']);self.assertTrue(value['operator_assertions_unverified']);self.assertEqual(app.assessment(self.identifier,4)['document']['findings'][0]['state'],'New');self.assertEqual(value['document']['retests'][0]['reviewer'],'sample_reviewer')
    def test_direct_resolution_or_retesting_forbidden(self):
        self.steps(3)
        for state in ('Resolved','Retesting'):
            command=self.command(3);command['data']['state']=state;self.refused(command,'TRANSITION_REFUSED')
    def test_finding_requires_received_submission(self):
        self.load();self.refused(self.command(2),'RECORD_NOT_FOUND')
    def test_retest_requires_triage_and_later_same_series(self):
        self.steps(3);command=self.command(4);command['data']['expected_revision']=1;self.refused(command,'RETEST_REQUIRES_TRIAGE');self.act(self.command(3));command=self.command(4);command['data']['replacement_submission_id']='sample_original';self.refused(command,'REPLACEMENT_NOT_LATER_IN_SERIES')
        command=self.command(1);command['data'].update(id='other_build',series_id='other_series',revision=3);self.act(command);command=self.command(4);command['data']['replacement_submission_id']='other_build';self.refused(command,'REPLACEMENT_NOT_LATER_IN_SERIES')
    def test_fixed_retest_requires_all_three_notes(self):
        self.steps(4)
        for name in ('reproduction_notes','positive_control_notes','evidence_reference'):
            command=self.command(4);command['data'][name]='';self.refused(command,'TEXT_INVALID')
    def test_inconclusive_needs_notes_or_limitations(self):
        self.steps(4);command=self.command(4);command['data'].update(outcome='Inconclusive',reproduction_notes='',limitations='');self.refused(command,'RETEST_NOTES_REQUIRED');command['data']['limitations']='Fictional limitation';self.act(command);self.act(self.command(5));self.assertEqual(self.current()['document']['findings'][0]['state'],'Triaged')
    def test_reject_fixed_does_not_resolve(self):
        self.steps(5);command=self.command(5);command['data']['decision']='reject';self.act(command);self.assertEqual(self.current()['document']['findings'][0]['state'],'Triaged')
    def test_pending_review_and_repeat_review_refused(self):
        self.steps(5);command=self.command(4);command['data'].update(id='another_retest',expected_revision=3);self.refused(command,'RETEST_REVIEW_PENDING');self.act(self.command(5));command=self.command(5);command['data']['expected_revision']=4;self.refused(command,'RETEST_REVIEW_STALE')
    def test_transition_invalidates_pending_retest(self):
        self.steps(5);command=self.command(3);command['data'].update(expected_revision=3,state='Triaged');self.act(command);command=self.command(5);command['data']['expected_revision']=4;self.refused(command,'RETEST_REVIEW_STALE')
    def test_later_submission_blocks_stale_fixed_acceptance(self):
        self.steps(5);command=self.command(1);command['data'].update(id='sample_newest',revision=3);self.act(command);self.refused(self.command(5),'REPLACEMENT_NOT_LATEST');command=self.command(5);command['data']['decision']='reject';self.act(command)
    def test_duplicate_canonical_rules_prevent_cycles(self):
        self.steps(3);command=self.command(2);command['data']['id']='second_finding';self.act(command);transition=self.command(3);transition['data'].update(finding_id='second_finding',state='Duplicate',duplicate_of='sample_finding');self.act(transition);transition=self.command(3);transition['data'].update(state='Duplicate',duplicate_of='second_finding');self.refused(transition,'DUPLICATE_REFERENCE_REFUSED');transition['data']['duplicate_of']='sample_finding';self.refused(transition,'DUPLICATE_REFERENCE_REFUSED')
    def test_risk_owner_condition_and_inapplicable_fields(self):
        self.steps(3);command=self.command(3);command['data']['state']='Accepted risk';self.refused(command,'TEXT_INVALID');command['data'].update(risk_owner='sample_owner',review_condition='Review the next fictional revision');self.act(command);self.assertEqual(self.current()['document']['findings'][0]['state'],'Accepted risk');command['data'].update(state='Triaged',expected_revision=2);self.refused(command,'RISK_FIELDS_REFUSED');command['data'].update(risk_owner='',review_condition='');self.act(command)
    def test_amend_is_revision_checked_and_resolved_is_read_only(self):
        self.steps(3);command=dict(operation='amend',actor='sample_actor',reason='Fictional correction',data={k:v for k,v in self.command(2)['data'].items() if k not in ('id','submission_id')});command['data'].update(finding_id='sample_finding',expected_revision=1,title='Changed fictional title');self.act(command);self.assertEqual(self.current()['document']['findings'][0]['revision'],2);self.refused(command,'FINDING_REVISION_CONFLICT')
    def test_stale_assessment_hash_never_writes(self):
        self.load();pin=self.current()['sha256'];self.act(self.command(0));before=app.history(self.identifier)
        with self.assertRaisesRegex(r.WorkbenchError,'ASSESSMENT_REVISION_CONFLICT'):self.act(self.command(1),pin)
        self.assertEqual(app.history(self.identifier),before)
    def test_finding_revision_conflict_is_atomic(self):
        self.steps(4);self.refused(self.command(3),'FINDING_REVISION_CONFLICT')
    def test_history_chain_and_independent_comparison(self):
        self.steps();rows=app.history(self.identifier)['versions'];self.assertEqual([v['version'] for v in rows],list(range(1,8)));self.assertEqual(rows[1]['parent_sha256'],rows[0]['sha256']);diff=app.compare(self.identifier,4,7);self.assertEqual({(v['kind'],v.get('id'),v['status']) for v in diff['changes']},{('findings','sample_finding','changed'),('retests','sample_retest','added')})
    def test_history_limit_is_atomic(self):
        self.load()
        with mock.patch.object(c,'MAX_REVISIONS',1):self.refused(self.command(0),'HISTORY_LIMIT')
    def test_legacy_exact_roundtrip_no_promoted_finding(self):
        self.load();self.act(self.command(6));value=self.current();self.assertEqual(value['document']['legacy_records'],self.command(6)['data']['records']);self.assertEqual(value['document']['findings'],[]);self.assertEqual(value['legacy_report']['status'],'DECLARED_RECORDS_CONSISTENT');self.assertFalse(value['legacy_report']['outcomes_verified']);self.refused(self.command(6),'LEGACY_ALREADY_IMPORTED')
    def test_legacy_inconsistent_drafts_preserved_for_review(self):
        self.load();command=self.command(6);command['data']['records']['findings'][0]['selected_retest_id']='missing_retest';self.act(command);self.assertEqual(self.current()['legacy_report']['status'],'REVIEW_REQUIRED')

class StorageAndHandoff(Fixture):
    def test_export_requires_boolean_review_and_exact_head(self):
        self.steps();value=self.review();value['checks']['privacy']=1
        with self.assertRaisesRegex(r.WorkbenchError,'EXPORT_REVIEW_REQUIRED'):app.export(r.encode(value))
        value=self.review();value['expected_sha256']='0'*64
        with self.assertRaisesRegex(r.WorkbenchError,'ASSESSMENT_REVISION_CONFLICT'):app.export(r.encode(value))
        self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_export_manifest_bytes_receipts_and_fresh_directory(self):
        self.steps(7);first=app.export(r.encode(self.review()));second=app.export(r.encode(self.review()));self.assertNotEqual(first['directory'],second['directory']);folder=self.root/first['directory'];manifest=json.loads((folder/'manifest.json').read_text());self.assertFalse(manifest['public_release_authorized']);self.assertEqual({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()},set(manifest['files'])|{'manifest.json'})
        for name,pin in manifest['files'].items():raw=(folder/name).read_bytes();self.assertEqual(pin,dict(bytes=len(raw),sha256=r.digest(raw)))
        self.assertEqual((folder/'receipts/sample_original.bin').read_bytes(),b'Fictional inert receipt 1\n');self.assertEqual(json.loads((folder/'legacy-records.json').read_text()),self.command(6)['data']['records'])
    def test_backup_replays_exact_history(self):
        self.steps();saved=app.backup();target=self.root/saved['file'];self.assertEqual(saved['sha256'],r.digest(target.read_bytes()))
        with closing(sqlite3.connect(target)) as con:r.validate_schema(con);self.assertEqual(app._history(con,self.identifier)[-1]['sha256'],self.current()['sha256'])
    def test_append_only_and_unexpected_schema_refused(self):
        self.steps(1)
        with r.connect() as con:
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM revisions')
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.assessments()
    def test_forged_recomputed_hash_still_fails_replay(self):
        self.steps(3);path=self.root/'database/workbench.sqlite3'
        with closing(sqlite3.connect(path)) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='revision_no_update'").fetchone()[0];con.execute('DROP TRIGGER revision_no_update');raw=con.execute('SELECT payload_json FROM revisions WHERE version=4').fetchone()[0];payload=r.decode(raw.encode());payload['document']['findings'][0]['state']='Resolved';new=r.encode(payload);con.execute('UPDATE revisions SET sha256=?,payload_json=? WHERE version=4',(r.digest(new),new.decode()));con.execute(trigger);con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'HISTORY_REPLAY_MISMATCH'):self.current()
    def test_store_sidecar_refused(self):
        (self.root/'database/workbench.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(r.WorkbenchError):app.assessments()
    def test_read_input_and_output_caps(self):
        path=self.root/'inbox/large';path.write_bytes(b'x'*100)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path,50)
        with mock.patch.object(r,'MAX_INPUT',5):
            with self.assertRaises(r.WorkbenchError):r.write_new(self.root/'reports/large',b'x'*6)

class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request_http(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=r.encode(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_token_no_store_and_csp(self):
        status,raw,headers=self.request_http();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn("object-src 'none'",headers['Content-Security-Policy'])
    def test_host_origin_and_session_guards(self):
        self.assertEqual(self.request_http('/api/list')[0],403);self.assertEqual(self.request_http(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request_http('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_fixed_errors_unknown_routes_and_duplicate_queries(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/show?id=bad',headers=headers);self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='ASSESSMENT_NOT_FOUND'));self.assertEqual(self.request_http('/api/show?id=a&id=b',headers=headers)[0],400);self.assertEqual(self.request_http('/api/run','POST',{},headers)[0],404)
    def test_create_and_read_via_actual_http(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/create','POST',self.fixture['create'],headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['version'],1);status,raw,_=self.request_http('/api/show?id=sample_assessment',headers=headers);self.assertEqual(json.loads(raw)['document']['findings'],[])

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
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-assessment.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.assessments()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-assessment.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-assessment.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-assessment.json:stream')
    def test_stale_lock_requires_stopped_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.assessments(),dict(assessments=[]))
    def test_actual_idle_child_termination_and_restart(self):
        self.load();r.close();child=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(child.stdout.readline())['mode'],'LOOPBACK_ASSESSMENT_UI');child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(len(app.assessments()['assessments']),1)

if __name__=='__main__':unittest.main()
