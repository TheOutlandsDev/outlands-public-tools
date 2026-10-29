"""Fictional supplied contracts, independent result oracles, stores and real HTTP."""
from contextlib import closing
import copy
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
from setupplan import application as app,artifacts as a,contracts as c,journal as j,engine,runtime as r,web

CHECKS=dict(quality=True,privacy=True,rights=True,context=True)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.example=app.example();self.profile=self.example['profile'];self.observations=self.example['observations']
    def request(self,value):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional setup evidence',request=value))
    def save(self,profile=None,parent=None):return app.save_profile(self.request(dict(parent_id=parent,profile=self.profile if profile is None else profile)))['job']['result']
    def evaluate(self,profile=None,observations=None):
        chosen=profile or self.save();return app.evaluate(self.request(dict(profile_id=chosen['profile_id'],profile_sha256=chosen['profile_sha256'],observations=self.observations if observations is None else observations)))['job']['result']
    def plan(self,evaluation=None):
        chosen=evaluation or self.evaluate();return app.make_plan(self.request(dict(evaluation_id=chosen['evaluation_id'],evaluation_sha256=chosen['evaluation_sha256'],checks=CHECKS)))['job']['result']
    def refused(self,fn,code):
        with self.assertRaisesRegex(r.WorkbenchError,'^'+code+'$'):fn()
    def export_request(self,plan):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional handoff',plan_id=plan['plan_id'],checks=CHECKS))

class Contracts(Fixture):
    def result(self):return engine.evaluate(self.profile,self.observations)
    def test_independent_exact_success_oracle(self):
        value=self.result();self.assertEqual(value['summary'],dict(checks=9,blocking_checks=0,optional_unresolved=0,steps=3,blocked_steps=0,unexpected_settings=0));self.assertEqual(value['status'],'DECLARATIONS_SATISFIED');self.assertEqual([v['id'] for v in value['steps']],['prepare','review','handoff']);self.assertEqual({v['status'] for v in value['checks']},{'PASS'});self.assertEqual({v['verification_status'] for v in value['steps']},{'NOT_PERFORMED'})
    def test_missing_required_propagates_all_three_steps(self):
        self.observations['prerequisites']['sample_runtime']='MISSING';value=self.result();self.assertEqual(value['summary']['blocking_checks'],1);self.assertEqual(value['summary']['blocked_steps'],3);self.assertEqual(value['steps'][1]['blocked_steps'],['prepare']);self.assertEqual(value['status'],'REVIEW_REQUIRED')
    def test_unsupplied_required_is_unknown_not_missing(self):
        del self.observations['prerequisites']['sample_runtime'];self.assertEqual(self.result()['checks'][0]['status'],'UNKNOWN')
    def test_unsafe_cannot_be_approved_as_ready(self):
        self.observations['prerequisites']['sample_runtime']='UNSAFE';self.assertEqual(self.result()['status'],'REVIEW_REQUIRED')
    def test_optional_unresolved_warns_but_reference_blocks_step(self):
        self.profile['prerequisites'][0]['required']=False;self.observations['prerequisites']['sample_runtime']='UNKNOWN';value=self.result();self.assertEqual(value['summary']['blocking_checks'],0);self.assertEqual(value['summary']['optional_unresolved'],1);self.assertEqual(value['summary']['blocked_steps'],3)
    def test_boolean_integer_and_order_rules_preserved(self):
        self.observations['settings']['WORKERS']=True;value=self.result();checks={v['id']:v['status'] for v in value['checks']};self.assertEqual(checks['configuration:workers'],'FAIL');self.assertEqual(checks['configuration:worker_budget'],'BLOCKED');self.observations['settings']['WORKERS']=8;self.assertEqual({v['id']:v['status'] for v in self.result()['checks']}['configuration:worker_budget'],'FAIL')
    def test_values_and_unknown_setting_names_not_in_report(self):
        self.observations['settings']['FICTIONAL_PRIVATE_MARKER']='invented-value-only';value=self.result();raw=r.encode(value);self.assertNotIn(b'invented-value-only',raw);self.assertNotIn(b'FICTIONAL_PRIVATE_MARKER',raw);self.assertEqual(value['summary']['unexpected_settings'],1);self.assertEqual(value['status'],'REVIEW_REQUIRED')
    def test_declared_connection_equality_is_not_availability(self):
        self.profile['connections']['bindings'][1]['port']=8765;value=self.result();self.assertEqual(value['summary']['blocking_checks'],2);self.assertEqual(value['steps'][-1]['blocked_checks'],['connection:sample_ui','connection:sample_worker']);self.assertFalse(value['network_probed']);self.assertFalse(value['runtime_verified'])
    def test_connection_transport_and_address_remain_distinct(self):
        self.profile['connections']['bindings'][1].update(port=8765,transport='udp');self.assertEqual(self.result()['summary']['blocking_checks'],0);self.profile['connections']['bindings'][1].update(transport='tcp',address='::1');self.assertEqual(self.result()['summary']['blocking_checks'],0)
    def test_nonloopback_connection_is_refused(self):
        self.profile['connections']['bindings'][0]['address']='example.invalid';self.refused(self.result,'DECLARATION_CONTRACT_INVALID')
    def test_layout_names_are_exact_case_sensitive_assertions(self):
        self.observations['files'][0]='settings/Sample.json';value=self.result();self.assertEqual(value['summary']['blocking_checks'],1);self.assertEqual(value['steps'][0]['blocked_checks'],['layout:settings'])
    def test_layout_and_selector_reject_traversal_reserved_stream_and_absolute(self):
        for value in ('../sample','/sample','C:/sample','settings/a:stream','settings/CON.txt','settings/a.','settings/a\\b','settings/.hidden'):
            with self.subTest(value=value):self.refused(lambda:c.portable(value),'RELATIVE_PATH_INVALID')
        self.refused(lambda:c.selector('inbox/../sample'),'SELECTOR_INVALID')
    def test_cycles_unknown_references_and_duplicate_ids_refused(self):
        self.profile['steps'][0]['depends_on']=['handoff'];self.refused(self.result,'STEP_CYCLE_REFUSED');self.profile=app.example()['profile'];self.profile['steps'][0]['checks']=['configuration:absent'];self.refused(self.result,'CHECK_REFERENCE_INVALID');self.profile=app.example()['profile'];self.profile['steps'][0]['depends_on']=['absent'];self.refused(self.result,'STEP_DEPENDENCY_INVALID')
    def test_topological_order_independent_of_declaration_order(self):
        self.profile['steps'].reverse();self.assertEqual([v['id'] for v in self.result()['steps']],['prepare','review','handoff'])
    def test_sibling_topology_preserves_supplied_order(self):
        self.profile['steps'][1]['depends_on']=[];self.profile['steps'][0],self.profile['steps'][1]=self.profile['steps'][1],self.profile['steps'][0];self.assertEqual([v['id'] for v in self.result()['steps']],['review','prepare','handoff'])
    def test_unknown_observation_and_duplicate_case_names_refused(self):
        self.observations['prerequisites']['other']='PRESENT';self.refused(self.result,'PREREQUISITE_UNDECLARED');self.observations=app.example()['observations'];self.observations['files'].append('SETTINGS/sample.json');self.refused(self.result,'NAME_DUPLICATE')
    def test_exact_fields_reject_command_definitions_and_wrong_required_type(self):
        self.profile['steps'][0]['command']='fictional-command';self.refused(self.result,'FIELDS_INVALID');del self.profile['steps'][0]['command'];self.profile['prerequisites'][0]['required']=1;self.refused(self.result,'REQUIRED_BOOLEAN_INVALID')
    def test_bounded_text_lists_profile_and_deep_json(self):
        self.profile['steps']*=33;self.refused(self.result,'LIST_LIMIT');self.refused(lambda:r.decode(b'['*66+b'0'+b']'*66),'JSON_DEPTH_LIMIT');self.refused(lambda:c.text('\ud800'),'TEXT_ENCODING_INVALID')
    def test_duplicate_nonfinite_and_boolean_review_refused(self):
        self.refused(lambda:r.decode(b'{"x":1,"x":2}'),'JSON_DUPLICATE_KEY');self.refused(lambda:r.decode(b'{"x":NaN}'),'JSON_NUMBER_INVALID');self.refused(lambda:c.checks(dict(CHECKS,privacy=1)),'REVIEW_REQUIRED')
    def test_engine_never_calls_host_io_process_or_network(self):
        import socket
        with mock.patch.object(subprocess,'Popen',side_effect=AssertionError('NO_EXECUTION')),mock.patch.object(socket,'getaddrinfo',side_effect=AssertionError('NO_DNS')),mock.patch.object(socket,'create_connection',side_effect=AssertionError('NO_NETWORK')),mock.patch.object(Path,'stat',side_effect=AssertionError('NO_HOST_METADATA')),mock.patch.object(Path,'read_bytes',side_effect=AssertionError('NO_HOST_CONTENT')):self.assertEqual(self.result()['status'],'DECLARATIONS_SATISFIED')
    def test_unreferenced_optional_setting_missing_warns_but_supplied_invalid_blocks(self):
        self.profile['configuration']['fields'].append(dict(id='optional_note',key='OPTIONAL_NOTE',type='string',required=False,choices=['fictional_choice']))
        missing=self.result();self.assertEqual(missing['status'],'DECLARATIONS_SATISFIED');self.assertEqual(missing['summary']['optional_unresolved'],1)
        self.observations['settings']['OPTIONAL_NOTE']='invalid_fictional_choice';invalid=self.result();self.assertEqual(invalid['status'],'REVIEW_REQUIRED');self.assertEqual(invalid['summary']['blocking_checks'],1);self.assertEqual(invalid['summary']['optional_unresolved'],0);self.assertEqual(invalid['summary']['blocked_steps'],0)

class Workflows(Fixture):
    def test_profile_lineage_and_comparison_are_immutable(self):
        first=self.save();self.profile['steps'][0]['label']='Fictional changed label';second=self.save(parent=first['profile_id']);value=app.compare('profile',first['profile_id'],second['profile_id']);self.assertEqual(value['changes']['steps']['changed'],['prepare']);self.assertEqual(app.inspect('profile',first['profile_id'])['content']['steps'][0]['label'],'Review prerequisites and settings name')
    def test_evaluations_compare_check_ids_without_values(self):
        profile=self.save();first=self.evaluate(profile);self.observations['settings']['WORKERS']=8;second=self.evaluate(profile);value=app.compare('evaluation',first['evaluation_id'],second['evaluation_id']);self.assertEqual(value['changes']['checks']['changed'],['configuration:worker_budget']);self.assertNotIn('observations',value)
    def test_plan_keeps_blockers_and_is_never_execution_permission(self):
        self.observations['prerequisites']['sample_runtime']='MISSING';plan=self.plan();value=app.inspect('plan',plan['plan_id'])['content'];self.assertEqual(value['status'],'REVIEW_REQUIRED');self.assertEqual(value['summary']['blocked_steps'],3);self.assertFalse(value['execution_authorized']);self.assertFalse(value['public_release_authorized'])
    def test_historical_evaluation_can_be_reviewed_after_new_profile(self):
        first=self.evaluate();self.profile['label']='Fictional changed revision';self.save();plan=self.plan(first);self.assertEqual(plan['evaluation_id'],first['evaluation_id'])
    def test_missing_review_and_stale_hash_refused_before_job(self):
        chosen=self.evaluate();before=app.overview()['sequence'];request=dict(evaluation_id=chosen['evaluation_id'],evaluation_sha256='f'*64,checks=CHECKS);self.refused(lambda:app.make_plan(self.request(request)),'EVALUATION_NOT_REGISTERED_OR_PIN_MISMATCH');request['evaluation_sha256']=chosen['evaluation_sha256'];request['checks']=dict(CHECKS,privacy=False);self.refused(lambda:app.make_plan(self.request(request)),'REVIEW_REQUIRED');self.assertEqual(app.overview()['sequence'],before)
    def test_stale_head_and_unregistered_parent_do_not_write(self):
        request=self.request(dict(parent_id=None,profile=self.profile));self.save();self.refused(lambda:app.save_profile(request),'JOURNAL_HEAD_CONFLICT');self.refused(lambda:self.save(parent='a'*32),'PARENT_NOT_REGISTERED');self.assertEqual(len(app.overview()['profiles']),1)
    def test_artifact_and_marker_tampering_refused(self):
        profile=self.save();path=self.root/profile['target'];(path/'READY.json').write_bytes(b'{}');self.refused(lambda:app.inspect('profile',profile['profile_id']),'ARTIFACT_MARKER_MISMATCH');(path/'READY.json').write_bytes(r.encode(profile));(path/'profile.json').write_bytes(b'{}');self.refused(lambda:self.evaluate(profile),'ARTIFACT_HASH_MISMATCH');self.assertEqual(app.overview()['jobs'][-1]['status'],'failed')
    def test_upstream_evaluation_tampering_blocks_plan_and_export(self):
        evaluation=self.evaluate();plan=self.plan(evaluation);(self.root/evaluation['target']/'evaluation.json').write_bytes(b'{}');self.refused(lambda:app.inspect('plan',plan['plan_id']),'ARTIFACT_HASH_MISMATCH');self.refused(lambda:app.export(self.export_request(plan)),'ARTIFACT_HASH_MISMATCH')
    def test_fresh_outputs_do_not_replace_even_with_reused_identifier(self):
        identifier='e'*32;path=self.root/'profiles'/identifier;path.mkdir();(path/'sentinel').write_bytes(b'keep')
        with mock.patch.object(app.uuid,'uuid4',return_value=mock.Mock(hex=identifier)):self.refused(self.save,'FILESYSTEM_REFUSED')
        self.assertEqual((path/'sentinel').read_bytes(),b'keep');self.assertEqual(app.overview()['profiles'],[])
    def test_partial_failure_retained_and_not_registered(self):
        original=r.write_new
        def partial(path,raw):
            if path.name=='READY.json':raise OSError('withheld fictional detail')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=partial):self.refused(self.save,'OPERATION_REFUSED')
        job=app.overview()['jobs'][0];self.assertEqual(job['status'],'failed');self.assertTrue((self.root/'profiles'/job['job_id']/'profile.json').exists());self.assertEqual(app.overview()['profiles'],[])
    def test_keyboard_interruption_requires_manual_recovery_without_replay(self):
        with mock.patch.object(a,'write',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.save()
        self.refused(self.save,'UNFINISHED_JOB_REVIEW_REQUIRED');out=app.recover(r.encode(dict(actor='sample_recovery',reason='Controlled stopped instance')));self.assertFalse(out['automatically_replayed']);self.assertEqual(app.overview()['jobs'][0]['status'],'interrupted');self.save()
    def test_index_schema_append_only_and_version_checks(self):
        self.save()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM events')
            con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        self.refused(app.overview,'STORE_SCHEMA_REFUSED')
    def test_store_user_version_refused(self):
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('PRAGMA user_version=7')
        self.refused(app.overview,'STORE_VERSION_REFUSED')
    def test_hash_tampering_refused(self):
        self.save()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');con.execute('UPDATE events SET sha256=? WHERE sequence=1',('f'*64,));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_HASH_MISMATCH')
    def test_rehashed_typed_result_boolean_forgery_refused(self):
        self.evaluate()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');value=r.decode(con.execute('SELECT payload_json FROM events WHERE sequence=4').fetchone()[0].encode());value['event']['data']['result']['summary']['blocking_checks']=False;raw=r.encode(value);con.execute('UPDATE events SET sha256=?,payload_json=? WHERE sequence=4',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_RESULT_INVALID')
    def test_event_and_job_limits(self):
        with mock.patch.object(c,'MAX_EVENTS',2):self.save();self.assertEqual(app.overview()['sequence'],2);self.refused(self.save,'JOURNAL_LIMIT')
        with mock.patch.object(c,'MAX_JOBS',1):self.refused(self.save,'JOURNAL_LIMIT')
    def test_private_export_manifest_and_input_boundary(self):
        plan=self.plan();out=app.export(self.export_request(plan));directory=self.root/out['directory'];manifest=out['manifest'];self.assertEqual(len(list(directory.iterdir())),6);self.assertTrue(manifest['contains_private_inputs']);self.assertFalse(manifest['execution_authorized']);self.assertFalse(manifest['public_release_authorized']);self.assertIn(b'WORKERS',(directory/'journal.json').read_bytes());self.assertNotIn(b'WORKERS',(directory/'evaluation.json').read_bytes())
        for name,item in manifest['files'].items():raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=r.digest(raw)))
    def test_private_export_requires_fresh_head_and_review(self):
        plan=self.plan();request=self.export_request(plan);self.save();self.refused(lambda:app.export(request),'JOURNAL_HEAD_CONFLICT');value=r.decode(self.export_request(plan));value['checks']['privacy']=False;self.refused(lambda:app.export(r.encode(value)),'REVIEW_REQUIRED')
    def test_index_backup_verified_but_omits_artifacts(self):
        self.evaluate();backup=app.backup_index();self.assertTrue(backup['contains_private_inputs']);self.assertFalse(backup['includes_artifact_files']);self.assertEqual(r.digest((self.root/backup['file']).read_bytes()),backup['sha256'])
        with closing(sqlite3.connect(self.root/backup['file'])) as con:self.assertEqual(j.load(con)[0]['sequence'],4)
    def test_source_instance_and_existing_file_refused(self):
        with self.assertRaises(r.WorkbenchError):r.write_new(self.root/'inbox/profile.json',b'no overwrite')
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP/'private-instance',create=True)
        self.assertFalse((APP/'private-instance').exists())
    def test_stale_session_and_outside_cli_selector(self):
        r.close();(self.root/'.session-lock').mkdir();self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);r.close();p=subprocess.run([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'save-profile','--file','../outside.json'],capture_output=True,text=True);self.assertEqual(p.returncode,2);self.assertEqual(json.loads(p.stdout),dict(error='SELECTOR_INVALID'));self.assertNotIn(str(self.root),p.stdout)
    def test_actual_child_interruption_retains_partial_and_requires_recovery(self):
        r.close();program='''import sys,threading\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom setupplan import application as app,artifacts as a,runtime as r\nr.configure(sys.argv[2])\ndef stopped(state,identifier,kind,request):\n p=r.ROOT/'profiles'/identifier;r.mkdir(p);r.write_new(p/'PARTIAL.txt',b'fictional interrupted revision');r.write_new(r.ROOT/'owned-child-ready',b'ready');threading.Event().wait(120)\na.write=stopped\napp.save_profile(r.encode(dict(expected_head=app.overview()['head'],actor='sample_child',reason='Controlled interruption',request=dict(parent_id=None,profile=app.example()['profile']))))\n''';p=subprocess.Popen([sys.executable,'-B','-W','error','-c',program,str(APP),str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+20
            while not (self.root/'owned-child-ready').exists() and p.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue((self.root/'owned-child-ready').exists());p.kill();p.communicate(timeout=10);self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);self.assertEqual(app.overview()['unfinished_jobs'],1);app.recover(r.encode(dict(actor='sample_recovery',reason='Owned child stopped')));state=app.overview();self.assertEqual(state['jobs'][0]['status'],'interrupted');self.assertEqual(state['profiles'],[]);self.assertTrue((self.root/'profiles'/state['jobs'][0]['job_id']/'PARTIAL.txt').is_file())
        finally:
            if p.poll() is None:p.kill()
            p.communicate(timeout=10)

class HttpBoundaries(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def http(self,path,method='GET',body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:con.request(method,path,body=body,headers=headers or {});res=con.getresponse();return res.status,res.read(),dict(res.getheaders())
        finally:con.close()
    def test_root_security_headers_and_no_html_injection_api(self):
        status,raw,headers=self.http('/');self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('frame-ancestors',headers['Content-Security-Policy']);self.assertNotIn(b'innerHTML',raw)
    def test_host_token_and_origin_refused(self):
        self.assertEqual(self.http('/api/overview')[0],403);self.assertEqual(self.http('/',headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.http('/api/profile','POST',self.request(dict(parent_id=None,profile=self.profile)),{'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403)
    def test_duplicate_query_and_body_keys_refused(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.http('/api/job?id=a&id=b',headers=headers)[0],400);self.assertEqual(self.http('/api/profile','POST',b'{"a":1,"a":2}',headers)[0],400)
    def test_actual_http_profile_and_evaluation_details(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.http('/api/profile','POST',self.request(dict(parent_id=None,profile=self.profile)),headers);self.assertEqual(status,200);identifier=json.loads(raw)['job']['result']['profile_id'];status,raw,_=self.http('/api/inspect?kind=profile&id='+identifier,headers=headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['content'],self.profile)
    def test_bad_body_and_no_unknown_endpoint_execution(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.http('/api/install','POST',b'{}',headers)[0],404);status,raw,_=self.http('/api/profile','POST',b'{}',headers);self.assertEqual(status,400);self.assertNotIn(str(self.root).encode(),raw)

class NativeBoundaries(Fixture):
    def make_link(self,action):
        try:action()
        except (OSError,subprocess.SubprocessError):
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('NATIVE_FIXTURE_REQUIRED')
            self.skipTest('Native link creation unavailable on this test filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias.json';self.make_link(lambda:os.link(self.root/'inbox/profile.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias'))
        with self.assertRaises(r.WorkbenchError):app.overview()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias.json';self.make_link(lambda:os.symlink(self.root/'inbox/profile.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'profile.json')
    def test_native_profile_hardlink_refused(self):
        profile=self.save();self.make_link(lambda:os.link(self.root/profile['target']/'profile.json',self.root/'inbox/profile-alias.json'))
        with self.assertRaises(r.WorkbenchError):app.inspect('profile',profile['profile_id'])
    def test_native_plan_hardlink_refused(self):
        built=self.plan();self.make_link(lambda:os.link(self.root/built['target']/'plan.json',self.root/'inbox/document-alias'))
        with self.assertRaises(r.WorkbenchError):app.inspect('plan',built['plan_id'])
    def test_native_junction_or_directory_link_output_parent_refused(self):
        path=self.root/'plans';path.rmdir();target=self.root/'controlled-target';target.mkdir()
        if os.name=='nt':
            script=self.root/'inbox/junction-fixture.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\n$ErrorActionPreference="Stop"\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null\n',encoding='utf-8');self.make_link(lambda:subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),str(path),str(target)],capture_output=True,check=True));self.addCleanup(lambda:os.rmdir(path))
        else:self.make_link(lambda:os.symlink(target,path,target_is_directory=True))
        preview=self.evaluate()
        with self.assertRaises(r.WorkbenchError):self.plan(preview)
        self.assertEqual(list(target.iterdir()),[])
    @unittest.skipUnless(os.name!='nt','POSIX-only FIFO boundary')
    def test_posix_fifo_input_refused_without_blocking(self):
        path=self.root/'inbox/pipe';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream selector boundary')
    def test_windows_stream_selector_refused(self):self.refused(lambda:c.selector('inbox/profile.json:stream'),'SELECTOR_INVALID')

