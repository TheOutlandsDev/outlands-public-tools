"""Fictional histories and independent lifecycle, coverage and boundary oracles."""
import copy
from contextlib import closing
from datetime import timedelta
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
from reliability import application as app,contracts as c,engine,runtime as r,web

def stamp(seconds):return c.stamp(c.timestamp('2030-01-01T00:00:00Z')+timedelta(seconds=seconds))
def sample(seconds,state='healthy',observed=None,note='Fictional observation'):
    services=[] if state is None else [dict(service_id='sample_service',signals=[dict(id='runtime',state=state,observed_at=stamp(seconds if observed is None else observed),note=note)])]
    return dict(id='sample_'+str(seconds),at=stamp(seconds),services=services)

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.fixture=r.decode((APP/'examples/sample-recording.json').read_bytes());self.identifier='sample_reliability'
    def definition(self):
        value=copy.deepcopy(self.fixture['case']);value['maintenance']=[];value['services']=value['services'][:1];return value
    def recording(self,samples,definition=None):return dict(actor='sample_owner',reason='Fictional recording',case=definition or self.definition(),snapshots=samples)
    def load(self):return app.create(r.encode(self.fixture),imported=True)
    def current(self):return app.case(self.identifier)
    def ingest(self,samples,pin=None):return app.act(r.encode(dict(case_id=self.identifier,expected_sha256=pin or self.current()['sha256'],command=dict(operation='ingest',actor='sample_owner',reason='Fictional append',data=dict(snapshots=samples)))))
    def analyse(self,samples,definition=None):return engine.analyse(c.append(c.create(definition or self.definition()),samples))
    def health(self,report):return next(row for row in report['incidents'] if row['kind']=='health')
    def review(self):return dict(case_id=self.identifier,expected_sha256=self.current()['sha256'],actor='sample_reviewer',reason='Fictional private handoff',checks=dict(quality=True,privacy=True,rights=True,context=True))
    def acknowledge(self,row=None,episode=None,escalations=None):
        row=row or self.health(self.current()['report']);actor='sample_reviewer';reason='Fictional acknowledgement';data=dict(incident_id=row['incident_id'],expected_episode=row['episode'] if episode is None else episode,expected_escalations=row['escalations'] if escalations is None else escalations,actor=actor,reason=reason)
        return app.act(r.encode(dict(case_id=self.identifier,expected_sha256=self.current()['sha256'],command=dict(operation='acknowledge',actor=actor,reason=reason,data=data))))

class Contracts(Fixture):
    def test_unknown_fields_wrong_scalars_reserved_ids(self):
        value=self.definition();value['extra']=True
        with self.assertRaises(r.WorkbenchError):c.create(value)
        for item in (True,1.0,'1'):
            with self.assertRaises(r.WorkbenchError):c.integer(item,1,10)
        for item in ('../sample','con','com1','Upper','x'*41):
            with self.assertRaises(r.WorkbenchError):c.token(item)
    def test_json_duplicate_nonfinite_depth_utf8_and_text(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*70+b'0'+b']'*70,b'\xff'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)
        for value in ('x\0y','\ud800','x'*401):
            with self.assertRaises(r.WorkbenchError):c.text(value)
    def test_timestamp_format_dates_and_range(self):
        for value in ('2030-01-01','2030-02-30T00:00:00Z','2030-01-01T00:00:00+00:00','2030-01-01T00:00:00.1Z','1999-01-01T00:00:00Z',True):
            with self.assertRaises(r.WorkbenchError):c.timestamp(value)
        self.assertEqual(stamp(60),'2030-01-01T00:01:00Z')
    def test_service_signal_duplicates_unknowns_and_limits(self):
        for change in ('duplicate_service','duplicate_signal','too_many_signals','unknown_state'):
            value=self.definition()
            if change=='duplicate_service':value['services']*=2
            if change=='duplicate_signal':value['services'][0]['signals']=['runtime','runtime']
            if change=='too_many_signals':value['services'][0]['signals']=['a','b','c','d','e']
            if change=='unknown_state':value['services'][0]['expected_state']='live'
            with self.assertRaises(r.WorkbenchError):c.create(value)
    def test_maintenance_bounds_overlap_and_references(self):
        for change in ('backwards','too_long','overlap','reference'):
            value=copy.deepcopy(self.fixture['case'])
            if change=='backwards':value['maintenance'][0]['end']=stamp(20)
            if change=='too_long':value['maintenance'][0]['end']=stamp(90000)
            if change=='overlap':other=copy.deepcopy(value['maintenance'][0]);other['id']='other_window';value['maintenance'].append(other)
            if change=='reference':value['maintenance'][0]['service_id']='missing'
            with self.assertRaises(r.WorkbenchError):c.create(value)
    def test_snapshot_order_duplicate_and_future_fact(self):
        for values in ([sample(1),sample(0)],[sample(0),sample(0)],[sample(0,observed=1)]):
            with self.assertRaises(r.WorkbenchError):self.analyse(values)
    def test_observation_conflict_and_backwards_time(self):
        for values in ([sample(0,'down'),sample(1,'healthy',0)],[sample(1,'down'),sample(2,'down',0)]):
            with self.assertRaises(r.WorkbenchError):self.analyse(values)
    def test_unknown_service_and_signal_refused(self):
        for kind in ('service','signal'):
            value=sample(0)
            if kind=='service':value['services'][0]['service_id']='unknown_service'
            else:value['services'][0]['signals'][0]['id']='unknown_signal'
            with self.assertRaises(r.WorkbenchError):self.analyse([value])
    def test_recording_span_and_document_limits(self):
        with self.assertRaisesRegex(r.WorkbenchError,'RECORDING_SPAN_LIMIT'):self.analyse([sample(0),sample(32*86400)])
        with mock.patch.object(c,'MAX_DOCUMENT',10):
            with self.assertRaisesRegex(r.WorkbenchError,'DOCUMENT_LIMIT'):self.analyse([sample(0)])
    def test_duplicate_rows_and_signals_refused(self):
        for kind in ('service','signal'):
            value=sample(0)
            if kind=='service':value['services']*=2
            else:value['services'][0]['signals']*=2
            with self.assertRaises(r.WorkbenchError):self.analyse([value])

class Lifecycle(Fixture):
    def test_stable_identity_ignores_note_and_severity_changes(self):
        result=self.analyse([sample(0,'degraded',note='Invented 10'),sample(1,'down',note='Invented 20')]);self.assertEqual(len(result['incidents']),1);row=self.health(result);self.assertEqual(row['occurrences'],2);self.assertEqual(row['severity'],'critical');self.assertEqual(row['escalations'],1)
    def test_repeated_cached_bad_evidence_not_double_counted(self):
        row=self.health(self.analyse([sample(0,'down'),sample(1,'down',0)]));self.assertEqual(row['occurrences'],1);self.assertEqual(row['last_seen'],stamp(1))
    def test_missing_signal_holds_health_and_opens_freshness(self):
        result=self.analyse([sample(0,'down'),sample(1,None),sample(2,None)]);row=self.health(result);self.assertEqual(row['state'],'active');self.assertTrue(row['held']);self.assertEqual(row['clean_count'],0);self.assertEqual(result['counts'],dict(active=2,monitoring=0,resolved=0))
    def test_stale_signal_never_resolves_health(self):
        row=self.health(self.analyse([sample(0,'down'),sample(1),sample(20,observed=1)]));self.assertNotEqual(row['state'],'resolved');self.assertEqual(row['clean_count'],0);self.assertTrue(row['held'])
    def test_distinct_fresh_clean_samples_required(self):
        row=self.health(self.analyse([sample(0,'down'),sample(1),sample(2,observed=1)]));self.assertEqual(row['state'],'monitoring');self.assertEqual(row['clean_count'],1)
        row=self.health(self.analyse([sample(0,'down'),sample(1),sample(2)]));self.assertEqual(row['state'],'resolved');self.assertEqual(row['resolved_at'],stamp(2))
    def test_clean_gap_resets_progress_and_old_cached_evidence(self):
        definition=self.definition();definition['policy'].update(maximum_age_seconds=100,maximum_gap_seconds=5,clean_samples=2)
        row=self.health(self.analyse([sample(0,'down'),sample(1),sample(10,observed=1)],definition));self.assertEqual(row['clean_count'],0);self.assertTrue(row['held']);self.assertNotEqual(row['state'],'resolved')
    def test_pre_missing_clean_fact_cannot_clear_later_uncertainty(self):
        definition=self.definition();definition['policy']['clean_samples']=1
        row=self.health(self.analyse([sample(0,'down'),sample(10,None),sample(11,observed=5)],definition));self.assertEqual(row['state'],'active');self.assertTrue(row['held'])
    def test_fresh_down_can_clear_freshness_without_clearing_health(self):
        result=self.analyse([sample(0,None),sample(1,'down'),sample(2,'down')]);by_kind={row['kind']:row for row in result['incidents']};self.assertEqual(by_kind['freshness']['state'],'resolved');self.assertEqual(by_kind['health']['state'],'active')
    def test_reopening_creates_episode_and_keeps_prior_resolution(self):
        row=self.health(self.analyse([sample(0,'down'),sample(1),sample(2),sample(3,'down')]));self.assertEqual(row['episode'],2);self.assertEqual(row['state'],'active');self.assertEqual(row['occurrences'],2);self.assertEqual(len(row['episodes']),1);self.assertEqual(row['episodes'][0]['resolved_at'],stamp(2))
    def test_maintenance_holds_recovery_and_expires(self):
        definition=self.definition();definition['maintenance']=[dict(id='sample_window',service_id='sample_service',start=stamp(1),end=stamp(3),reason='Fictional window')]
        result=self.analyse([sample(0,'down'),sample(1),sample(2),sample(3,'down')],definition);row=self.health(result);self.assertEqual(row['occurrences'],2);self.assertEqual([v['status'] for v in result['timeline']],['down','maintenance','maintenance','down']);self.assertEqual(row['state'],'active')
    def test_pre_end_maintenance_evidence_cannot_count_as_recovery(self):
        definition=self.definition();definition['maintenance']=[dict(id='sample_window',service_id='sample_service',start=stamp(1),end=stamp(5),reason='Fictional window')]
        result=self.analyse([sample(0,'down'),sample(2),sample(5,observed=2)],definition);row=self.health(result);self.assertEqual(row['clean_count'],0);self.assertTrue(row['held'])
    def test_planned_off_is_not_healthy_and_has_no_runtime_incident(self):
        definition=self.definition();definition['services'][0]['expected_state']='planned_off';result=self.analyse([sample(0,'down'),sample(10,None)],definition);self.assertEqual(result['incidents'],[]);self.assertEqual(result['availability']['services'][0]['seconds']['planned_off'],10);self.assertIsNone(result['availability']['services'][0]['observation_coverage_fraction'])

class Coverage(Fixture):
    def test_independent_demo_bucket_oracle(self):
        result=engine.analyse(c.append(c.create(self.fixture['case']),self.fixture['snapshots']));row=result['availability']['services'][0];self.assertEqual(row['seconds'],dict(healthy=30,degraded=0,down=25,unknown=25,maintenance=20,planned_off=0));self.assertEqual(row['total_seconds'],100);self.assertEqual(row['known_seconds'],55);self.assertEqual(row['eligible_seconds'],80);self.assertAlmostEqual(row['healthy_fraction_of_known_seconds'],30/55);self.assertAlmostEqual(row['observation_coverage_fraction'],55/80);self.assertFalse(result['availability']['tail_extrapolated'])
    def test_expiry_splits_interval_without_last_sample_extrapolation(self):
        row=self.analyse([sample(0),sample(20)])['availability']['services'][0];self.assertEqual(row['seconds']['healthy'],15);self.assertEqual(row['seconds']['unknown'],5);self.assertEqual(row['total_seconds'],20)
    def test_long_gap_is_unknown_even_when_cached_fact_still_fresh(self):
        definition=self.definition();definition['policy'].update(maximum_age_seconds=100,maximum_gap_seconds=5);row=self.analyse([sample(0),sample(20)],definition)['availability']['services'][0];self.assertEqual(row['seconds']['healthy'],5);self.assertEqual(row['seconds']['unknown'],15)
    def test_maintenance_boundaries_split_between_samples(self):
        definition=self.definition();definition['maintenance']=[dict(id='sample_window',service_id='sample_service',start=stamp(3),end=stamp(7),reason='Fictional')];row=self.analyse([sample(0),sample(10)],definition)['availability']['services'][0];self.assertEqual(row['seconds']['maintenance'],4);self.assertEqual(row['seconds']['healthy'],6)
    def test_no_or_one_snapshot_has_no_denominator(self):
        for document in (c.create(self.definition()),c.append(c.create(self.definition()),[sample(0)])):
            row=engine.analyse(document)['availability']['services'][0];self.assertEqual(row['total_seconds'],0);self.assertIsNone(row['healthy_fraction_of_known_seconds']);self.assertIsNone(row['observation_coverage_fraction'])
    def test_fresh_down_proves_down_but_missing_signal_blocks_healthy(self):
        definition=self.definition();definition['services'][0]['signals'].append('application');result=self.analyse([sample(0,'down'),sample(1)],definition);self.assertEqual([r['status'] for r in result['timeline']],['down','unknown'])
    def test_degraded_is_not_counted_as_healthy(self):
        row=self.analyse([sample(0,'degraded'),sample(10)])['availability']['services'][0];self.assertEqual(row['seconds']['degraded'],10);self.assertEqual(row['healthy_fraction_of_known_seconds'],0)
    def test_seconds_conserved_across_every_service(self):
        result=engine.analyse(c.append(c.create(self.fixture['case']),self.fixture['snapshots']))
        for row in result['availability']['services']:self.assertEqual(sum(row['seconds'].values()),100)

class PersistenceAndReview(Fixture):
    def test_import_duplicate_id_and_empty_create(self):
        self.load()
        with self.assertRaisesRegex(r.WorkbenchError,'CASE_EXISTS'):self.load()
        value=dict(actor='sample_owner',reason='Fictional',case=self.definition());value['case']['case_id']='sample_empty';app.create(r.encode(value));self.assertEqual(app.case('sample_empty')['report']['snapshots'],0)
    def test_invalid_batch_is_atomic(self):
        self.load();before=self.current()
        with self.assertRaises(r.WorkbenchError):self.ingest([sample(110),sample(105)])
        self.assertEqual(self.current(),before)
    def test_duplicate_snapshot_never_inflates_occurrences(self):
        self.load();before=self.current()
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_DUPLICATE'):self.ingest([self.fixture['snapshots'][-1]])
        self.assertEqual(self.current(),before)
    def test_stale_case_hash_refused(self):
        self.load();pin=self.current()['sha256'];self.ingest([sample(110)])
        with self.assertRaisesRegex(r.WorkbenchError,'CASE_REVISION_CONFLICT'):self.ingest([sample(120)],pin)
        self.assertEqual(self.current()['version'],2)
    def test_acknowledgement_does_not_change_health(self):
        self.load();before=self.current()['report']['counts'];self.acknowledge();row=self.health(self.current()['report']);self.assertTrue(row['acknowledged']);self.assertEqual(self.current()['report']['counts'],before)
    def test_escalation_invalidates_acknowledgement(self):
        app.create(r.encode(self.recording([sample(0,'degraded')])),imported=True);self.acknowledge();self.ingest([sample(1,'down')]);row=self.health(self.current()['report']);self.assertFalse(row['acknowledged']);self.assertEqual(row['escalations'],1)
        with self.assertRaisesRegex(r.WorkbenchError,'INCIDENT_REVISION_CONFLICT'):self.acknowledge(escalations=0)
    def test_reopening_requires_new_acknowledgement(self):
        app.create(r.encode(self.recording([sample(0,'down')])),imported=True);self.acknowledge();self.ingest([sample(1),sample(2),sample(3,'down')]);self.assertFalse(self.health(self.current()['report'])['acknowledged'])
        with self.assertRaisesRegex(r.WorkbenchError,'INCIDENT_REVISION_CONFLICT'):self.acknowledge(episode=1)
    def test_resolved_acknowledgement_refused(self):
        app.create(r.encode(self.recording([sample(0,'down'),sample(1),sample(2)])),imported=True)
        with self.assertRaisesRegex(r.WorkbenchError,'INCIDENT_ALREADY_RESOLVED'):self.acknowledge()
    def test_historical_state_and_comparison_are_pinned(self):
        app.create(r.encode(self.recording([sample(0,'down')])),imported=True);self.ingest([sample(1),sample(2)]);self.assertEqual(self.health(app.case(self.identifier,1)['report'])['state'],'active');diff=app.compare(self.identifier,1,2);self.assertEqual(diff['changes'][0]['status'],'changed');self.assertEqual(diff['left_availability']['start'],diff['left_availability']['end']);self.assertEqual(diff['right_snapshots'],3)
    def test_history_chain_and_limit(self):
        self.load();self.ingest([sample(110)]);rows=app.history(self.identifier)['versions'];self.assertEqual(rows[1]['parent_sha256'],rows[0]['sha256'])
        with mock.patch.object(c,'MAX_REVISIONS',2):
            with self.assertRaisesRegex(r.WorkbenchError,'HISTORY_LIMIT'):self.ingest([sample(120)])
    def test_review_requires_booleans_and_latest_saved_hash(self):
        self.load();value=self.review();value['checks']['privacy']=1
        with self.assertRaisesRegex(r.WorkbenchError,'EXPORT_REVIEW_REQUIRED'):app.export(r.encode(value))
        value=self.review();self.ingest([sample(110)])
        with self.assertRaisesRegex(r.WorkbenchError,'CASE_REVISION_CONFLICT'):app.export(r.encode(value))
        self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_private_export_manifest_and_recording_roundtrip(self):
        self.load();self.acknowledge();first=app.export(r.encode(self.review()));second=app.export(r.encode(self.review()));self.assertNotEqual(first['directory'],second['directory']);folder=self.root/first['directory'];manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));self.assertFalse(manifest['public_release_authorized']);self.assertEqual({p.name for p in folder.iterdir()},set(manifest['files'])|{'manifest.json'})
        for name,pin in manifest['files'].items():raw=(folder/name).read_bytes();self.assertEqual(pin,dict(bytes=len(raw),sha256=r.digest(raw)))
        recording=r.decode((folder/'recording.json').read_bytes());recording['case']['case_id']='sample_roundtrip';app.create(r.encode(recording),imported=True);original=self.current()['report'];replayed=app.case('sample_roundtrip')['report'];self.assertEqual(replayed['availability'],original['availability']);self.assertEqual(replayed['counts'],original['counts']);self.assertFalse(any(row['acknowledged'] for row in replayed['incidents']))
    def test_csv_formula_newline_and_quoting_defense(self):
        raw=app._csv(('a',),[['=SUM(1)'],[' +cmd'],['@sample'],['\tformula'],['plain,"quoted"']]).decode();self.assertIn("'=SUM(1)",raw);self.assertIn("' +cmd",raw);self.assertIn("'@sample",raw);self.assertIn('"plain,""quoted"""',raw)
    def test_backup_schema_and_replayed_history(self):
        self.load();saved=app.backup();path=self.root/saved['file'];self.assertEqual(saved['sha256'],r.digest(path.read_bytes()))
        with closing(sqlite3.connect(path)) as con:r.validate_schema(con);self.assertEqual(app._history(con,self.identifier)[-1]['sha256'],self.current()['sha256'])
    def test_append_only_and_unexpected_schema_fail_closed(self):
        self.load()
        with r.connect() as con:
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM revisions')
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.cases()
    def test_forged_recomputed_hash_and_boolean_integer_replay_rejected(self):
        definition=self.definition();definition['policy']['clean_samples']=1;app.create(r.encode(self.recording([sample(0,'down')],definition)),imported=True);path=self.root/'database/workbench.sqlite3'
        with closing(sqlite3.connect(path)) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='revision_no_update'").fetchone()[0];con.execute('DROP TRIGGER revision_no_update');payload=r.decode(con.execute('SELECT payload_json FROM revisions').fetchone()[0].encode());payload['document']['policy']['clean_samples']=True;raw=r.encode(payload);con.execute('UPDATE revisions SET sha256=?,payload_json=?',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'HISTORY_REPLAY_MISMATCH'):self.current()
    def test_store_sidecars_and_limits_refused(self):
        (self.root/'database/workbench.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(r.WorkbenchError):app.cases()
    def test_unknown_commands_cannot_execute_or_probe(self):
        self.load()
        for op in ('run','probe','restart','install','delete'):
            with self.assertRaisesRegex(r.WorkbenchError,'CHOICE_INVALID'):app.act(r.encode(dict(case_id=self.identifier,expected_sha256=self.current()['sha256'],command=dict(operation=op,actor='sample',reason='Fictional',data={}))))

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
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/show?id=sample_missing',headers=headers);self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='CASE_NOT_FOUND'));self.assertEqual(self.request_http('/api/show?id=a&id=b',headers=headers)[0],400);self.assertEqual(self.request_http('/api/probe','POST',{},headers)[0],404)
    def test_actual_http_import_and_report(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/import','POST',self.fixture,headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['version'],1);status,raw,_=self.request_http('/api/show?id=sample_reliability',headers=headers);self.assertEqual(json.loads(raw)['report']['availability']['services'][0]['seconds']['unknown'],25)

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
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-recording.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.cases()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-recording.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-recording.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-recording.json:stream')
    def test_stale_lock_requires_stopped_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.cases(),dict(cases=[]))
    def test_actual_idle_child_termination_and_restart(self):
        self.load();r.close();child=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(child.stdout.readline())['mode'],'LOOPBACK_RELIABILITY_UI');child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(len(app.cases()['cases']),1)

if __name__=='__main__':unittest.main()
