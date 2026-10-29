"""Invented package-byte oracles, review boundaries, native I/O and real HTTP."""
from contextlib import closing
import copy
import http.client
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from releases import application as app,artifacts as a,contracts as c,engine,journal as j,runtime as r,web
CHECKS=dict(quality=True,privacy=True,rights=True,context=True)
POLICY=dict(backup_confirmed=True,target_stopped_confirmed=True,readiness_confirmed=True,allow_removals=True,dependency_reviewed=True)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.fixtures=app.example()
    def request(self,value):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional release evidence',request=value))
    def capture(self,version='v1',request=None):return app.capture(self.request(self.fixtures[version] if request is None else request))['job']['result']
    def pair(self):
        first=self.capture();second=self.capture('v2',dict(self.fixtures['v2'],parent_id=first['candidate_id']));return first,second
    def comparison(self,pair=None,policy=None):
        first,second=pair or self.pair();return app.compare(self.request(dict(baseline_id=first['candidate_id'],baseline_sha256=first['candidate_sha256'],candidate_id=second['candidate_id'],candidate_sha256=second['candidate_sha256'],policy=POLICY if policy is None else policy)))['job']['result']
    def plan(self,comparison=None):
        chosen=comparison or self.comparison();return app.make_plan(self.request(dict(comparison_id=chosen['comparison_id'],comparison_sha256=chosen['comparison_sha256'])))['job']['result']
    def review(self,plan,approve=True,checks=None):return app.review(r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional decision',plan_id=plan['plan_id'],plan_sha256=plan['plan_sha256'],approve=approve,checks=CHECKS if checks is None else checks)))
    def export_request(self,plan):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional handoff',plan_id=plan['plan_id'],checks=CHECKS))
    def refused(self,fn,code):
        with self.assertRaisesRegex(r.WorkbenchError,'^'+code+'$'):fn()

class Contracts(Fixture):
    def test_manifest_pin_is_required_independently_of_payload(self):
        request=dict(self.fixtures['v1'],manifest_sha256='f'*64);self.refused(lambda:self.capture(request=request),'TRUSTED_MANIFEST_PIN_MISMATCH');self.assertEqual(app.overview()['sequence'],0)
    def test_strict_schema_and_boolean_integers_are_rejected(self):
        value=copy.deepcopy(self.fixtures['v1']);value['manifest']['inventory'][0]['size']=True;self.refused(lambda:c.request('candidate',value),'PACKAGE_DECLARATION_INVALID');value=self.fixtures['v1'];value['command']='fictional command';self.refused(lambda:c.request('candidate',value),'FIELDS_INVALID');self.refused(lambda:c.policy(dict(POLICY,backup_confirmed=1)),'POLICY_BOOLEAN_INVALID')
    def test_duplicate_nonfinite_and_excessive_depth_json_refused(self):
        self.refused(lambda:r.decode(b'{"x":1,"x":2}'),'JSON_DUPLICATE_KEY');self.refused(lambda:r.decode(b'{"x":NaN}'),'JSON_NUMBER_INVALID');self.refused(lambda:r.decode(b'['*66+b'0'+b']'*66),'JSON_DEPTH_LIMIT')
    def test_manifest_case_file_directory_and_unsafe_names_rejected(self):
        manifest=copy.deepcopy(self.fixtures['v1']['manifest']);manifest['inventory'].append(dict(manifest['inventory'][0],path='BIN/component.txt'));self.refused(lambda:c.inventory(manifest),'PACKAGE_DECLARATION_INVALID')
        for value in ('../sample','/sample','bin/a:stream','bin/CON.txt','bin/.hidden','bin/a\\b'):
            with self.subTest(value=value):self.refused(lambda:c.portable(value),'RELATIVE_PATH_INVALID')
    def test_file_and_total_size_limits(self):
        value=copy.deepcopy(self.fixtures['v1']['manifest']);value['inventory'][0]['size']=c.MAX_FILE+1;self.refused(lambda:c.inventory(value),'INTEGER_INVALID')
        with mock.patch.object(c,'MAX_TOTAL',1):self.refused(lambda:c.inventory(self.fixtures['v1']['manifest']),'PACKAGE_TOTAL_LIMIT')
    def test_lock_text_must_match_manifest_and_grammar(self):
        value=copy.deepcopy(self.fixtures['v1']);value['dependency_lock']['text']=value['dependency_lock']['text'].replace('1.0.0','1.0.1');self.refused(lambda:c.request('candidate',value),'LOCK_MANIFEST_MISMATCH');value['dependency_lock']['text']='invented invalid lock';self.refused(lambda:c.request('candidate',value),'PACKAGE_DECLARATION_INVALID')
    def test_launcher_is_listed_data_not_an_executable_command(self):
        value=copy.deepcopy(self.fixtures['v1']);value['launcher']['executable']='bin/absent.txt';self.refused(lambda:c.request('candidate',value),'LAUNCHER_ENTRY_NOT_LISTED');value=copy.deepcopy(self.fixtures['v1']);value['launcher']['working_directory']='absent';self.refused(lambda:c.request('candidate',value),'LAUNCHER_DIRECTORY_NOT_LISTED');value=copy.deepcopy(self.fixtures['v1']);value['launcher']['arguments']=['bad\nargument'];self.refused(lambda:c.request('candidate',value),'ARGUMENT_CONTROL_REFUSED')
    def test_independent_file_change_and_lock_oracles(self):
        value=app.inspect('comparison',self.comparison()['comparison_id'])['content'];self.assertEqual(value['counts'],dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1));self.assertEqual({row['path']:row['action'] for row in value['files']},{'bin/component.txt':'REPLACE','notes.txt':'ADD','obsolete.txt':'REMOVE','requirements.lock':'REPLACE','settings/sample.json':'UNCHANGED'});self.assertEqual(value['dependency_lock']['counts']['version_text_changed'],1);self.assertEqual(value['dependency_lock']['counts']['unchanged'],1);self.assertFalse(value['dependency_lock']['artifacts_verified']);self.assertFalse(value['dependency_lock']['dependencies_resolved'])
    def test_each_missing_assertion_and_removal_policy_blocks(self):
        pair=self.pair()
        for key in POLICY:
            with self.subTest(key=key):value=self.comparison(pair,dict(POLICY,**{key:False}));self.assertEqual(value['status'],'REVIEW_REQUIRED');self.assertEqual(value['blocker_count'],1)
    def test_all_five_blockers_are_retained(self):
        result=self.comparison(policy={key:False for key in POLICY});self.assertEqual(result['blocker_count'],5);self.assertEqual(result['status'],'REVIEW_REQUIRED')
    def test_same_snapshot_has_no_changes_but_still_needs_assertions(self):
        chosen=self.capture();result=self.comparison((chosen,chosen));self.assertEqual(result['counts'],dict(ADD=0,REMOVE=0,REPLACE=0,UNCHANGED=4));self.assertEqual(result['status'],'READY_FOR_MANUAL_REVIEW')
    def test_case_only_and_file_directory_transitions_stay_blocked(self):
        old=engine.candidate(self.fixtures['v1']);new=copy.deepcopy(old);request=dict(baseline_id='a'*32,baseline_sha256='1'*64,candidate_id='b'*32,candidate_sha256='2'*64,policy=POLICY);new['inventory'][0]['path']='BIN/component.txt';value=engine.compare(old,new,request,self.fixtures['v1'],self.fixtures['v1']);self.assertIn('CASE_ONLY_LAYOUT_CHANGE',value['blockers']);new['inventory'][0]['path']='bin/component.txt/child';value=engine.compare(old,new,request,self.fixtures['v1'],self.fixtures['v1']);self.assertIn('FILE_DIRECTORY_LAYOUT_CHANGE',value['blockers']);new['inventory'][0]['path']='BIN/another.txt';value=engine.compare(old,new,request,self.fixtures['v1'],self.fixtures['v1']);self.assertIn('CASE_ONLY_LAYOUT_CHANGE',value['blockers'])
    def test_no_lock_and_one_missing_lock_have_explicit_coverage(self):
        old=copy.deepcopy(self.fixtures['v1']);old['dependency_lock']=None;new=copy.deepcopy(old);value=engine.compare(engine.candidate(old),engine.candidate(new),dict(baseline_id='a'*32,baseline_sha256='1'*64,candidate_id='b'*32,candidate_sha256='2'*64,policy=POLICY),old,new);self.assertEqual(value['dependency_lock']['status'],'NO_LOCKS_DECLARED');value=engine.compare(engine.candidate(old),engine.candidate(self.fixtures['v1']),dict(baseline_id='a'*32,baseline_sha256='1'*64,candidate_id='b'*32,candidate_sha256='2'*64,policy=dict(POLICY,dependency_reviewed=False)),old,self.fixtures['v1']);self.assertEqual(value['dependency_lock']['status'],'LOCK_DECLARATION_ADDED_OR_REMOVED');self.assertIn('DEPENDENCY_REVIEW_REQUIRED',value['blockers'])
    def test_pure_model_never_opens_sockets_or_executes_payloads(self):
        first=engine.candidate(self.fixtures['v1']);second=engine.candidate(self.fixtures['v2']);request=dict(baseline_id='a'*32,baseline_sha256='1'*64,candidate_id='b'*32,candidate_sha256='2'*64,policy=POLICY)
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('NO_EXECUTION')),mock.patch.object(socket,'getaddrinfo',side_effect=AssertionError('NO_DNS')),mock.patch.object(socket,'create_connection',side_effect=AssertionError('NO_NETWORK')),mock.patch.object(Path,'read_bytes',side_effect=AssertionError('NO_IMPLICIT_READ')):self.assertEqual(engine.compare(first,second,request,self.fixtures['v1'],self.fixtures['v2'])['status'],'READY_FOR_MANUAL_REVIEW')

class Workflows(Fixture):
    def test_capture_preserves_source_and_exact_primary_bytes(self):
        before={p.relative_to(self.root/'inbox').as_posix():p.read_bytes() for p in (self.root/'inbox').rglob('*') if p.is_file()};result=self.capture();descriptor=app.inspect('candidate',result['candidate_id'])['content'];self.assertEqual(descriptor['files'],4)
        for row in descriptor['inventory']:self.assertEqual((self.root/result['target']/'payload'/row['path']).read_bytes(),(self.root/'inbox/package-v1'/row['path']).read_bytes())
        self.assertTrue(all((self.root/'inbox'/name).read_bytes()==raw for name,raw in before.items()))
    def test_original_inbox_changes_do_not_rewrite_frozen_snapshot(self):
        result=self.capture();path=self.root/'inbox/package-v1/bin/component.txt';path.write_bytes(b'new private draft');self.assertEqual(app.inspect('candidate',result['candidate_id'])['content']['files'],4);self.assertNotEqual((self.root/result['target']/'payload/bin/component.txt').read_bytes(),path.read_bytes());self.refused(self.capture,'PAYLOAD_UNSAFE_OR_CHANGED')
    def test_extra_missing_and_empty_source_entries_are_refused(self):
        root=self.root/'inbox/package-v1';(root/'unexpected.txt').write_bytes(b'invented extra');self.refused(self.capture,'PAYLOAD_UNSAFE_OR_CHANGED');(root/'unexpected.txt').unlink();(root/'empty').mkdir();self.refused(self.capture,'PAYLOAD_UNSAFE_OR_CHANGED');(root/'empty').rmdir();(root/'obsolete.txt').unlink();self.refused(self.capture,'PAYLOAD_MANIFEST_MISMATCH');self.assertEqual(app.overview()['candidates'],[])
    def test_change_during_capture_is_retained_as_failed_without_registration(self):
        original=a.preflight.hash_file;calls=0
        def changed(path,**kwargs):
            nonlocal calls
            result=original(path,**kwargs)
            if kwargs.get('collect'):
                calls+=1
                if calls==1:(self.root/'inbox/package-v1/obsolete.txt').write_bytes(b'fictional changed')
            return result
        with mock.patch.object(a.preflight,'hash_file',side_effect=changed):self.refused(self.capture,'PAYLOAD_MANIFEST_MISMATCH')
        job=app.overview()['jobs'][0];self.assertEqual(job['status'],'failed');self.assertTrue((self.root/'candidates'/job['job_id']).is_dir());self.assertEqual(app.overview()['candidates'],[])
    def test_parent_lineage_and_identical_fresh_capture_ids(self):
        first=self.capture();second=self.capture(request=dict(self.fixtures['v1'],parent_id=first['candidate_id']));self.assertEqual(second['parent_id'],first['candidate_id']);self.assertEqual(first['candidate_sha256'],second['candidate_sha256']);self.assertNotEqual(first['candidate_id'],second['candidate_id'])
    def test_stale_head_and_unregistered_parent_are_refused(self):
        value=self.request(self.fixtures['v1']);self.capture();self.refused(lambda:app.capture(value),'JOURNAL_HEAD_CONFLICT');self.refused(lambda:self.capture(request=dict(self.fixtures['v1'],parent_id='f'*32)),'PARENT_NOT_REGISTERED')
    def test_snapshot_tampering_blocks_comparison_and_approval(self):
        pair=self.pair();plan=self.plan(self.comparison(pair));(self.root/pair[1]['target']/'payload/bin/component.txt').write_bytes(b'invented changed bytes');self.refused(lambda:self.review(plan),'PAYLOAD_UNSAFE_OR_CHANGED');self.assertEqual(app.overview()['reviews'],{})
    def test_snapshot_metadata_and_marker_tampering_refused(self):
        result=self.capture();root=self.root/result['target'];(root/'launcher.json').write_bytes(b'{}');self.refused(lambda:app.inspect('candidate',result['candidate_id']),'CANDIDATE_METADATA_MISMATCH');(root/'launcher.json').write_bytes(r.encode(self.fixtures['v1']['launcher']));(root/'READY.json').write_bytes(b'{}');self.refused(lambda:app.inspect('candidate',result['candidate_id']),'ARTIFACT_MARKER_MISMATCH')
    def test_plan_and_comparison_tampering_refused(self):
        comparison=self.comparison();plan=self.plan(comparison);(self.root/plan['target']/'plan.json').write_bytes(b'{}');self.refused(lambda:app.inspect('plan',plan['plan_id']),'ARTIFACT_HASH_MISMATCH');(self.root/comparison['target']/'comparison.json').write_bytes(b'{}');self.refused(lambda:self.plan(comparison),'ARTIFACT_HASH_MISMATCH')
    def test_pending_plan_cannot_export_and_blocked_plan_cannot_approve(self):
        plan=self.plan();self.refused(lambda:app.export(self.export_request(plan)),'CURRENT_PLAN_APPROVAL_REQUIRED');blocked=self.plan(self.comparison(policy={key:False for key in POLICY}));self.refused(lambda:self.review(blocked),'BLOCKED_PLAN_CANNOT_BE_APPROVED')
    def test_review_requires_true_booleans_and_matching_plan_pin(self):
        plan=self.plan();self.refused(lambda:self.review(plan,checks=dict(CHECKS,privacy=False)),'REVIEW_REQUIRED');bad=dict(plan,plan_sha256='f'*64);self.refused(lambda:self.review(bad),'PLAN_NOT_REGISTERED_OR_PIN_MISMATCH');self.refused(lambda:self.review(plan,approve=1),'APPROVE_BOOLEAN_INVALID')
    def test_revocation_blocks_future_exports_and_reapproval_is_explicit(self):
        plan=self.plan();self.review(plan);old=app.export(self.export_request(plan));self.review(plan,False,dict.fromkeys(CHECKS,False));self.refused(lambda:app.export(self.export_request(plan)),'CURRENT_PLAN_APPROVAL_REQUIRED');self.assertTrue((self.root/old['directory']/'manifest.json').exists());self.review(plan);self.assertEqual(app.inspect('plan',plan['plan_id'])['review']['status'],'APPROVED_FOR_PRIVATE_HANDOFF')
    def test_new_comparison_plan_never_inherits_approval(self):
        pair=self.pair();first=self.plan(self.comparison(pair));self.review(first);second=self.plan(self.comparison(pair));self.refused(lambda:app.export(self.export_request(second)),'CURRENT_PLAN_APPROVAL_REQUIRED');self.assertIsNone(app.inspect('plan',second['plan_id'])['review'])
    def test_historical_plan_retains_its_original_pair(self):
        pair=self.pair();plan=self.plan(self.comparison(pair));self.review(plan);third=self.capture();value=app.inspect('plan',plan['plan_id']);self.assertEqual(value['content']['candidate_id'],pair[1]['candidate_id']);self.assertNotEqual(value['content']['candidate_id'],third['candidate_id']);self.assertEqual(app.export(self.export_request(plan))['manifest']['payload_files_included'],False)
    def test_manual_steps_and_rollback_never_claim_execution_or_backup_verification(self):
        plan=self.plan();value=app.inspect('plan',plan['plan_id'])['content'];self.assertEqual(len(value['steps']),5);self.assertEqual({v['status'] for v in value['steps']},{'NOT_PERFORMED'});self.assertEqual(value['rollback']['candidate_only_paths'],['notes.txt']);self.assertFalse(value['rollback']['backup_independently_verified']);self.assertFalse(value['execution_authorized'])
    def test_approved_export_pins_metadata_and_keeps_inputs_private(self):
        plan=self.plan();self.review(plan);out=app.export(self.export_request(plan));root=self.root/out['directory'];manifest=out['manifest'];self.assertEqual(len(list(root.iterdir())),8);self.assertFalse(manifest['payload_files_included']);self.assertFalse(manifest['public_release_authorized']);self.assertTrue(manifest['contains_private_inputs']);self.assertIn(b'inbox/package-v1',(root/'journal.json').read_bytes())
        for name,item in manifest['files'].items():raw=(root/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=r.digest(raw)))
    def test_export_rechecks_fresh_head_review_and_snapshot_payload(self):
        plan=self.plan();self.review(plan);request=self.export_request(plan);self.review(plan);self.refused(lambda:app.export(request),'JOURNAL_HEAD_CONFLICT');value=r.decode(self.export_request(plan));value['checks']['privacy']=False;self.refused(lambda:app.export(r.encode(value)),'REVIEW_REQUIRED');state=app.overview();candidate=state['candidates'][0];(self.root/candidate['target']/'payload/obsolete.txt').write_bytes(b'changed');self.refused(lambda:app.export(self.export_request(plan)),'PAYLOAD_UNSAFE_OR_CHANGED')
    def test_private_index_backup_contains_requests_not_payload_or_artifacts(self):
        self.capture();out=app.backup_index();self.assertTrue(out['contains_private_inputs']);self.assertFalse(out['includes_payload_or_artifact_files']);self.assertEqual(r.digest((self.root/out['file']).read_bytes()),out['sha256'])
        with closing(sqlite3.connect(self.root/out['file'])) as con:self.assertEqual(j.load(con)[0]['sequence'],2)
    def test_schema_and_append_only_guards(self):
        self.capture()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM events')
            con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        self.refused(app.overview,'STORE_SCHEMA_REFUSED')
    def test_store_version_and_hash_forgery_refused(self):
        self.capture()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');con.execute('UPDATE events SET sha256=? WHERE sequence=1',('f'*64,));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_HASH_MISMATCH')
    def test_rehashed_typed_boolean_count_forgery_refused(self):
        self.capture()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');value=r.decode(con.execute('SELECT payload_json FROM events WHERE sequence=2').fetchone()[0].encode());value['event']['data']['result']['files']=True;raw=r.encode(value);con.execute('UPDATE events SET sha256=?,payload_json=? WHERE sequence=2',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_RESULT_INVALID')
    def test_event_cap_reserves_terminal_slot_and_job_cap(self):
        with mock.patch.object(c,'MAX_EVENTS',2):self.capture();self.assertEqual(app.overview()['sequence'],2);self.refused(self.capture,'JOURNAL_LIMIT')
        with mock.patch.object(c,'MAX_JOBS',1):self.refused(self.capture,'JOURNAL_LIMIT')
    def test_keyboard_interruption_blocks_new_jobs_until_stopped_recovery(self):
        with mock.patch.object(a,'write',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.capture()
        self.refused(self.capture,'UNFINISHED_JOB_REVIEW_REQUIRED');out=app.recover(r.encode(dict(actor='sample_recovery',reason='Controlled stopped instance')));self.assertFalse(out['automatically_replayed']);self.assertEqual(app.overview()['jobs'][0]['status'],'interrupted')
    def test_partial_output_and_preexisting_destination_are_retained(self):
        original=r.write_new
        def fail(path,raw):
            if path.name=='READY.json':raise OSError('withheld details')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=fail):self.refused(self.capture,'OPERATION_REFUSED')
        job=app.overview()['jobs'][0];self.assertTrue((self.root/'candidates'/job['job_id']/'payload/bin/component.txt').exists());self.assertEqual(app.overview()['candidates'],[]);identifier='e'*32;folder=self.root/'candidates'/identifier;folder.mkdir();(folder/'sentinel').write_bytes(b'keep')
        with mock.patch.object(app.uuid,'uuid4',return_value=mock.Mock(hex=identifier)):self.refused(self.capture,'FILESYSTEM_REFUSED')
        self.assertEqual((folder/'sentinel').read_bytes(),b'keep')
    def test_source_instance_and_existing_file_output_are_refused(self):
        with self.assertRaises(r.WorkbenchError):r.write_new(self.root/'inbox/capture-v1.json',b'no overwrite')
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP/'private-instance',create=True)
        self.assertFalse((APP/'private-instance').exists())
    def test_stale_session_and_outside_cli_request_are_refused(self):
        r.close();(self.root/'.session-lock').mkdir();self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);r.close();p=subprocess.run([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'capture','--file','../outside.json'],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout),dict(error='SELECTOR_INVALID'));self.assertNotIn(str(self.root),p.stdout)
    def test_actual_child_interruption_retains_partial_without_adoption(self):
        r.close();program='''import sys,threading\nsys.path.insert(0,sys.argv[1])\nfrom releases import application as app,artifacts as a,runtime as r\nr.configure(sys.argv[2])\ndef stopped(state,identifier,kind,request):\n p=r.ROOT/'candidates'/identifier;r.mkdir(p);r.write_new(p/'PARTIAL.txt',b'fictional interrupted capture');r.write_new(r.ROOT/'owned-child-ready',b'ready');threading.Event().wait(120)\na.write=stopped\napp.capture(r.encode(dict(expected_head=app.overview()['head'],actor='sample_child',reason='Controlled interruption',request=app.example()['v1'])))\n''';p=subprocess.Popen([sys.executable,'-B','-W','error','-c',program,str(APP),str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+20
            while not (self.root/'owned-child-ready').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue((self.root/'owned-child-ready').exists());p.kill();p.communicate(timeout=10);self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);self.assertEqual(app.overview()['unfinished_jobs'],1);app.recover(r.encode(dict(actor='sample_recovery',reason='Owned child stopped')));state=app.overview();self.assertEqual(state['jobs'][0]['status'],'interrupted');self.assertEqual(state['candidates'],[]);self.assertTrue((self.root/'candidates'/state['jobs'][0]['job_id']/'PARTIAL.txt').is_file())
        finally:
            if p.poll() is None:p.kill()
            p.communicate(timeout=10)

class NativeBoundaries(Fixture):
    def make_link(self,action):
        try:action()
        except (OSError,subprocess.SubprocessError):
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('NATIVE_FIXTURE_REQUIRED')
            self.skipTest('Native link creation unavailable on this test filesystem')
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias'))
        with self.assertRaises(r.WorkbenchError):app.overview()
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/capture-v1.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/capture-v1.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'capture-v1.json')
    def test_native_candidate_metadata_hardlink_refused(self):
        result=self.capture();self.make_link(lambda:os.link(self.root/result['target']/'candidate.json',self.root/'inbox/metadata-alias'))
        with self.assertRaises(r.WorkbenchError):app.inspect('candidate',result['candidate_id'])
    def test_native_candidate_payload_hardlink_refused(self):
        result=self.capture();self.make_link(lambda:os.link(self.root/result['target']/'payload/bin/component.txt',self.root/'inbox/payload-alias'))
        with self.assertRaises(r.WorkbenchError):app.inspect('candidate',result['candidate_id'])
    def test_native_plan_hardlink_refused(self):
        result=self.plan();self.make_link(lambda:os.link(self.root/result['target']/'plan.json',self.root/'inbox/plan-alias'))
        with self.assertRaises(r.WorkbenchError):app.inspect('plan',result['plan_id'])
    def test_native_junction_or_directory_link_output_parent_refused(self):
        path=self.root/'candidates';path.rmdir();target=self.root/'controlled-target';target.mkdir()
        if os.name=='nt':
            script=self.root/'inbox/junction-fixture.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\n$ErrorActionPreference="Stop"\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null\n',encoding='utf-8');self.make_link(lambda:subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),str(path),str(target)],capture_output=True,check=True));self.addCleanup(lambda:os.rmdir(path))
        else:self.make_link(lambda:os.symlink(target,path,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):self.capture()
        self.assertEqual(list(target.iterdir()),[])
    @unittest.skipUnless(os.name!='nt','POSIX-only FIFO boundary')
    def test_posix_fifo_input_refused_without_blocking(self):
        path=self.root/'inbox/pipe';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream selector boundary')
    def test_windows_stream_selector_refused(self):self.refused(lambda:c.selector('inbox/manifest.json:stream'),'SELECTOR_INVALID')

class HttpBoundaries(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def http(self,path,method='GET',body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:con.request(method,path,body=body,headers=headers or {});res=con.getresponse();return res.status,res.read(),dict(res.getheaders())
        finally:con.close()
    def test_root_security_headers_and_literal_rendering(self):
        status,raw,headers=self.http('/');self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('frame-ancestors',headers['Content-Security-Policy']);self.assertNotIn(b'innerHTML',raw)
    def test_host_origin_token_and_unknown_action_refused(self):
        self.assertEqual(self.http('/api/overview')[0],403);self.assertEqual(self.http('/',headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.http('/api/capture','POST',self.request(self.fixtures['v1']),{'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403);self.assertEqual(self.http('/api/apply','POST',b'{}',{'X-Outlands-Token':web.TOKEN})[0],404)
    def test_actual_http_capture_and_candidate_details(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.http('/api/capture','POST',self.request(self.fixtures['v1']),headers);self.assertEqual(status,200);identifier=json.loads(raw)['job']['result']['candidate_id'];status,raw,_=self.http('/api/inspect?kind=candidate&id='+identifier,headers=headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['content']['files'],4)
    def test_duplicate_keys_and_queries_fixed_errors(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.http('/api/job?id=a&id=b',headers=headers)[0],400);status,raw,_=self.http('/api/capture','POST',b'{"a":1,"a":2}',headers);self.assertEqual(status,400);self.assertNotIn(str(self.root).encode(),raw)
