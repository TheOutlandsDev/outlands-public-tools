"""Fictional application, independent arithmetic, rejection and native I/O checks."""
from contextlib import closing
import copy
from fractions import Fraction
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from operations_analytics import application as app,contracts as c,runtime,planning_report,web
from operations_analytics.engines import capacity,process,inventory,dispatch,events


def sample():return json.loads((APP/'examples/sample-scenario.json').read_text(encoding='utf-8'))
def encoded(value):return runtime.encode(value)
def evaluate(value):return app.calculate(c.scenario(encoded(value)))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(runtime.close)
        self.root=Path(self.temp.name)/'instance';runtime.configure(self.root,create=True);runtime.initialize()
    def load(self):return app.import_file('inbox/sample-scenario.json')
    def put(self,name,value):
        path=self.root/'inbox'/name;runtime.write_new(path,encoded(value));return path
    def make_planning(self):
        root=self.root/'inbox/planning-report';runtime.mkdir(root)
        value=dict(mode='LOCAL_ADVISORY_PLAN',project_id='sample-planning',revision_sha256='a'*64,products=[dict(remaining_demand=30,dock_allocated_quantity=2,allocation=dict(conservation=dict(covered=16,uncovered=12)))],external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False)
        data={'plan.json':encoded(value),'orders.csv':b'order,quantity\nsample,30\n','allocations.csv':b'lot,quantity\nsample,16\n','readiness.csv':b'order,ready\nsample,2\n'}
        manifest=dict(format='outlands-planning-report-v1',project_id=value['project_id'],revision_sha256=value['revision_sha256'],external_system_writes=False,files={k:dict(bytes=len(v),sha256=hashlib.sha256(v).hexdigest()) for k,v in data.items()})
        for name,raw in data.items():runtime.write_new(root/name,raw)
        runtime.write_new(root/'manifest.json',encoded(manifest));return root


class Domain(unittest.TestCase):
    def test_known_arithmetic(self):
        r=evaluate(sample());self.assertEqual(r['capacity'][0]['whole_unit_capacity'],201);self.assertEqual(r['capacity'][0]['minimum_people_under_assumptions'],3);self.assertEqual(r['process'][0]['oee_fraction'],0.5625);self.assertEqual(r['process'][0]['p90_minutes_linear_interpolation'],7.1);self.assertEqual(r['inventory'][0]['proposed_order_units'],18)
    def test_capacity_fraction_oracle(self):
        rng=random.Random(17)
        for _ in range(100):
            row=sample()['capacity'][0];row.update(people=rng.randint(0,20),demand_units=rng.randint(0,5000),minutes_per_unit=rng.randint(1,30),productive_fraction=rng.choice([0.25,0.5,0.75,1]))
            productive=Fraction(row['shift_minutes']-row['break_minutes']-row['unavailable_minutes_per_person'])*Fraction(str(row['productive_fraction']))
            actual=capacity.calculate(row);self.assertEqual(actual['whole_unit_capacity'],math.floor(row['people']*productive/row['minutes_per_unit']));self.assertEqual(actual['minimum_people_under_assumptions'],math.ceil(row['demand_units']*row['minutes_per_unit']/productive))
    def test_capacity_zero_productive_time(self):
        row=sample()['capacity'][0];row['productive_fraction']=0;result=capacity.calculate(row);self.assertIsNone(result['minimum_people_under_assumptions']);self.assertEqual(result['whole_unit_capacity'],0);row['demand_units']=0;self.assertEqual(capacity.calculate(row)['minimum_people_under_assumptions'],0)
    def test_capacity_invalid_shift_partition(self):
        row=sample()['capacity'][0];row['break_minutes']=480
        with self.assertRaisesRegex(runtime.WorkbenchError,'SHIFT_PARTITION_INVALID'):capacity.calculate(row)
    def test_capacity_result_limit(self):
        row=sample()['capacity'][0];row.update(minutes_per_unit=0.000001,people=100000)
        with self.assertRaisesRegex(runtime.WorkbenchError,'RESULT_LIMIT'):capacity.calculate(row)
    def test_process_decomposition(self):
        r=process.calculate(sample()['process'][0]);self.assertAlmostEqual(r['availability_fraction']*r['performance_fraction']*r['quality_fraction'],r['oee_fraction'])
    def test_process_zero_denominators(self):
        row=sample()['process'][0];row.update(planned_minutes=0,running_minutes=0,downtime_minutes=0,total_units=0,good_units=0,cycle_samples_minutes=[]);result=process.calculate(row)
        for key in ('availability_fraction','performance_fraction','quality_fraction','oee_fraction','median_minutes','p90_minutes_linear_interpolation'):self.assertIsNone(result[key])
    def test_process_exact_time_partition(self):
        row=sample()['process'][0];row['running_minutes']=359.999999
        with self.assertRaisesRegex(runtime.WorkbenchError,'PROCESS_TIME_PARTITION_INVALID'):process.calculate(row)
    def test_process_above_one_refused(self):
        row=sample()['process'][0];row['ideal_minutes_per_unit']=3
        with self.assertRaises(runtime.WorkbenchError):process.calculate(row)
    def test_cycle_percentile_single_sample(self):
        row=sample()['process'][0];row['cycle_samples_minutes']=[3.5];result=process.calculate(row);self.assertEqual(result['median_minutes'],3.5);self.assertEqual(result['p90_minutes_linear_interpolation'],3.5)
    def test_cycle_samples_positive(self):
        row=sample()['process'][0];row['cycle_samples_minutes']=[0]
        with self.assertRaises(runtime.WorkbenchError):process.calculate(row)
    def test_inventory_exact_reorder_boundary(self):
        row=sample()['inventory'][0];row.update(on_hand=16,allocated=2);result=inventory.calculate(row,sample()['snapshot_utc']);self.assertTrue(result['reorder_triggered']);self.assertEqual(result['proposed_order_units'],12)
    def test_inventory_above_reorder_point(self):
        row=sample()['inventory'][0];row['on_hand']=17;self.assertFalse(inventory.calculate(row,sample()['snapshot_utc'])['reorder_triggered'])
    def test_inventory_future_receipt(self):
        row=sample()['inventory'][0];row['received_at']='2040-01-01T00:00:00+00:00'
        with self.assertRaises(runtime.WorkbenchError):inventory.calculate(row,sample()['snapshot_utc'])
    def test_inventory_overallocated(self):
        row=sample()['inventory'][0];row['allocated']=13
        with self.assertRaises(runtime.WorkbenchError):inventory.calculate(row,sample()['snapshot_utc'])
    def test_dispatch_blocked_and_explained(self):
        result=evaluate(sample())['dispatch'];self.assertEqual([r['id'] for r in result['ranked']],['ready-a','ready-b']);self.assertEqual(result['ranked'][0]['priority_score'],0.6);self.assertEqual(len(result['blocked']),2);self.assertFalse(result['trained_model'])
    def test_dispatch_ties_stable(self):
        value=sample();value['dispatch']['candidates']=[dict(value['dispatch']['candidates'][0],id='second'),dict(value['dispatch']['candidates'][0],id='first')];self.assertEqual([r['id'] for r in evaluate(value)['dispatch']['ranked']],['first','second'])
    def test_dispatch_weights_must_sum_exactly(self):
        value=sample();value['dispatch']['policy']['age_weight']=0.5
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_boolean_decisions_are_strict(self):
        value=sample();value['dispatch']['candidates'][0]['ready']=1
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_half_open_subsecond_window(self):
        value=sample();value['window']=dict(start='2030-01-12T08:00:00.500000+00:00',end='2030-01-12T08:00:00.700000+00:00');value['completions']=[dict(source='sample',event_id='e'+str(i),family='alpha',units=1,occurred_at='2030-01-12T08:00:00.'+fraction+'+00:00') for i,fraction in enumerate(('499999','500000','699999','700000'))];self.assertEqual(evaluate(value)['snapshot']['completed_units'],2)
    def test_timezone_normalization(self):self.assertEqual(c.utc('2030-01-12T10:00:00+02:00'),'2030-01-12T08:00:00.000000+00:00')
    def test_naive_timestamp_refused(self):
        with self.assertRaises(runtime.WorkbenchError):c.instant('2030-01-12T08:00:00')
    def test_future_events_refused(self):
        value=sample();value['completions'][0]['occurred_at']='2040-01-01T00:00:00+00:00'
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_hold_age(self):self.assertEqual(evaluate(sample())['snapshot']['holds'][0]['hold_age_hours'],27)
    def test_hold_time_cannot_precede_entry(self):
        value=sample();value['active_lots'][2]['held_since']='2030-01-10T00:00:00+00:00'
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_unknown_fields_refused(self):
        value=sample();value['capacity'][0]['unexpected']='x'
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_duplicate_case_ids_refused(self):
        value=sample();value['capacity'].append(value['capacity'][0])
        with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_quantities_reject_bool_and_strings(self):
        for quantity in (True,'3',3.0):
            value=sample();value['capacity'][0]['people']=quantity
            with self.assertRaises(runtime.WorkbenchError):evaluate(value)
    def test_numeric_precision_bound(self):
        with self.assertRaises(runtime.WorkbenchError):c.number(0.0000001)
    def test_huge_integer_is_fixed_error(self):
        with self.assertRaises(runtime.WorkbenchError):c.number(10**1000)
    def test_empty_areas_valid(self):
        value=sample()
        for key in ('capacity','process','inventory','active_lots','completions'):value[key]=[]
        value['dispatch']['candidates']=[];self.assertEqual(evaluate(value)['snapshot']['completed_units'],0)
    def test_duplicate_keys_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.decode(b'{"x":1,"x":2}')
    def test_nonfinite_numbers_refused(self):
        for raw in (b'NaN',b'Infinity',b'1e999'):
            with self.assertRaises(runtime.WorkbenchError):runtime.decode(raw)
    def test_depth_and_size_limits(self):
        for raw in (b'['*66+b'0'+b']'*66,b'x'*(runtime.MAX_INPUT+1)):
            with self.assertRaises(runtime.WorkbenchError):runtime.decode(raw)


class Application(Fixture):
    def test_full_demo(self):
        self.assertEqual(app.demo(),dict(mode='FICTIONAL_OPERATIONS_ANALYTICS_DEMO',capacity=201,minimum_people=3,oee=0.5625,p90=7.1,reorder_units=18,eligible_dispatch=2,blocked_dispatch=2,initial_completions=25,final_completions=33,revision=2,replay_created_revision=False,private_report_files=7,backup_validated=True,external_system_writes=False,mail_sent=False))
    def test_demo_needs_no_network(self):
        with patch('socket.socket',side_effect=AssertionError('Unexpected network request')):self.assertFalse(app.demo()['external_system_writes'])
    def test_idempotent_save_and_ingest(self):
        first=self.load();self.assertFalse(app.save(encoded(sample()),first['revision_sha256'])['created']);second=app.ingest('sample-operations','inbox/sample-events.json',first['revision_sha256']);self.assertFalse(app.ingest('sample-operations','inbox/sample-events.json',second['revision_sha256'])['created'])
    def test_event_conflict_rolls_back_whole_save(self):
        first=self.load();value=sample();value['completions'].append(dict(value['completions'][0],event_id='event-aaa'));value['completions'][1]['units']=99
        with self.assertRaisesRegex(runtime.WorkbenchError,'EVENT_IDENTITY_CONFLICT'):app.save(encoded(value),first['revision_sha256'])
        with runtime.connect() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM completion_events').fetchone()[0],3)
        self.assertEqual(len(app.history('sample-operations')['revisions']),1)
    def test_store_budget_failure_rolls_back_events_and_revision(self):
        with patch.object(runtime,'MAX_STORE',0),self.assertRaisesRegex(runtime.WorkbenchError,'STORE_LIMIT'):self.load()
        with runtime.connect() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],0)
            self.assertEqual(con.execute('SELECT COUNT(*) FROM completion_events').fetchone()[0],0)
    def test_invalid_ingest_never_commits(self):
        first=self.load();self.put('invalid-events.json',[dict(sample()['completions'][0],event_id='new-valid'),{'bad':'row'}])
        with self.assertRaises(runtime.WorkbenchError):app.ingest('sample-operations','inbox/invalid-events.json',first['revision_sha256'])
        with runtime.connect() as con:self.assertEqual(con.execute('SELECT COUNT(*) FROM completion_events').fetchone()[0],3)
    def test_stale_save_refused(self):
        first=self.load();app.ingest('sample-operations','inbox/sample-events.json',first['revision_sha256'])
        with self.assertRaisesRegex(runtime.WorkbenchError,'REVISION_CONFLICT'):app.save(encoded(sample()),first['revision_sha256'])
    def test_historical_results_stable(self):
        first=self.load();before=app.plan('sample-operations',1);app.ingest('sample-operations','inbox/sample-events.json',first['revision_sha256']);self.assertEqual(app.plan('sample-operations',1),before)
    def test_compare_numeric_delta(self):
        first=self.load();value=sample();value['capacity'][0]['people']=4;app.save(encoded(value),first['revision_sha256']);result=app.compare('sample-operations',1,2)
        row=next(r for r in result['changes'] if r['domain']=='capacity' and r['metric']=='whole_unit_capacity');self.assertEqual(row['delta'],67)
    def test_compare_undefined_is_not_zero(self):
        first=self.load();value=sample();value['capacity'][0]['productive_fraction']=0;app.save(encoded(value),first['revision_sha256']);row=next(r for r in app.compare('sample-operations',1,2)['changes'] if r['metric']=='minimum_people_under_assumptions');self.assertIsNone(row['delta']);self.assertIsNone(row['after'])
    def test_compare_added_cases_and_eligibility(self):
        first=self.load();value=sample();value['capacity'].append(dict(value['capacity'][0],id='second'));value['dispatch']['candidates'][0]['on_hold']=True;app.save(encoded(value),first['revision_sha256']);result=app.compare('sample-operations',1,2);self.assertIn(dict(domain='capacity',id='second'),result['added_cases']);self.assertEqual(len(result['eligibility_changes']),1)
    def test_review_version_conflict(self):
        first=self.load();value=dict(project_id='sample-operations',revision_sha256=first['revision_sha256'],domain='capacity',case_id='base',expected_version=0,status='reviewed',actor='sample_reviewer',note='Fictional review');app.review(encoded(value))
        with self.assertRaisesRegex(runtime.WorkbenchError,'REVIEW_VERSION_CONFLICT'):app.review(encoded(value))
    def test_new_revision_does_not_inherit_reviews(self):
        first=self.load();app.review(encoded(dict(project_id='sample-operations',revision_sha256=first['revision_sha256'],domain='capacity',case_id='base',expected_version=0,status='reviewed',actor='sample_reviewer',note='Fictional review')));app.ingest('sample-operations','inbox/sample-events.json',first['revision_sha256']);self.assertEqual(app.plan('sample-operations')['reviews'],[])
    def test_report_hashes(self):
        self.load();result=app.export('sample-operations')
        for name,item in result['manifest']['files'].items():
            raw=(self.root/result['directory']/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        self.assertFalse(result['manifest']['mail_sent'])
    def test_csv_escapes_formula_prefixes(self):self.assertIn(b"'=1+1",app._csv([dict(value='=1+1')]))
    def test_reports_use_distinct_directories(self):
        self.load();self.assertNotEqual(app.export('sample-operations')['directory'],app.export('sample-operations')['directory'])
    def test_backup_validates_and_matches_hash(self):
        self.load();result=app.backup();path=self.root/result['file']
        with closing(sqlite3.connect(path)) as con:runtime.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),result['sha256'])
    def test_append_only_triggers(self):
        self.load()
        for sql in ('DELETE FROM revisions','UPDATE completion_events SET payload_sha256=payload_sha256'):
            with self.assertRaises(sqlite3.IntegrityError),runtime.connect() as con:con.execute(sql)
    def test_store_schema_refused(self):
        with closing(sqlite3.connect(self.root/'database/analytics.sqlite3')) as con:con.execute('CREATE TABLE unexpected(x)');con.commit()
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_store_version_refused(self):
        with closing(sqlite3.connect(self.root/'database/analytics.sqlite3')) as con:con.execute('PRAGMA user_version=4')
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_journal_sidecar_refused(self):
        (self.root/'database/analytics.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_planning_import_verified_and_no_eligibility_mapping(self):
        first=self.load();root=self.make_planning();before=app.plan('sample-operations')['dispatch'];app.attach_planning('sample-operations',root,first['revision_sha256']);result=app.plan('sample-operations');self.assertEqual(result['planning_reference']['uncovered_quantity'],12);self.assertFalse(result['planning_reference']['independently_verified']);self.assertEqual(result['dispatch'],before)
    def test_planning_hash_tamper_refused(self):
        root=self.make_planning();(root/'orders.csv').write_bytes(b'tampered')
        with self.assertRaisesRegex(runtime.WorkbenchError,'PLANNING_REPORT_BYTES_CHANGED'):planning_report.read(root)
    def test_planning_inventory_extra_refused(self):
        root=self.make_planning();(root/'extra.txt').write_bytes(b'invented')
        with self.assertRaises(runtime.WorkbenchError):planning_report.read(root)
    def test_planning_conservation_refused(self):
        value=dict(format='outlands-planning-reference-v1',project_id='sample-planning',revision_sha256='a'*64,manifest_sha256='b'*64,remaining_demand=5,dock_allocated_quantity=1,covered_quantity=1,uncovered_quantity=1,independently_verified=False)
        with self.assertRaises(runtime.WorkbenchError):planning_report.reference(value)


class Filesystem(Fixture):
    def test_source_cannot_be_instance(self):
        runtime.close()
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(APP,create=True)
    def test_parent_escape_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('../outside',False)
    def test_existing_output_never_replaced(self):
        path=self.put('first.json',{'sample':1})
        with self.assertRaises(runtime.WorkbenchError):runtime.write_new(path,b'new')
        self.assertEqual(path.read_bytes(),encoded({'sample':1}))
    def make_link(self,action):
        try:action()
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixture required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-scenario.json',target))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/analytics.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-scenario.json',target))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target/'sample-scenario.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        target=self.root/'inbox/sample-fifo';os.mkfifo(target)
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('inbox/sample-scenario.json:stream')
    def test_stale_lock_requires_assertion(self):
        runtime.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True);self.assertEqual(app.projects(),dict(projects=[]))
    def test_nonempty_stale_lock_refused(self):
        runtime.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/owned').write_bytes(b'fictional')
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(self.root,confirm_stopped=True)
    def test_actual_child_termination_and_restart(self):
        self.load();runtime.close();process=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(process.stdout.readline())['mode'],'LOOPBACK_ANALYTICS_UI');process.kill();process.communicate(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=10)
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True);self.assertEqual(app.plan('sample-operations')['snapshot']['completed_units'],25)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=encoded(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_and_no_cache(self):
        status,raw,headers=self.request();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertNotIn(b'__SESSION_TOKEN__',raw);self.assertEqual(headers['Cache-Control'],'no-store')
    def test_api_read_token_required(self):self.assertEqual(self.request('/api/projects')[0],403)
    def test_host_header_refused(self):self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
    def test_cross_origin_write_refused(self):self.assertEqual(self.request('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_write_token_required(self):self.assertEqual(self.request('/api/backup','POST',{})[0],403)
    def test_real_save_and_plan_http(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.request('/api/save','POST',dict(scenario=sample(),expected=None),headers)[0],200);status,raw,_=self.request('/api/plan?project=sample-operations',headers=headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['capacity'][0]['whole_unit_capacity'],201)
    def test_fixed_error_has_no_private_path(self):
        status,raw,_=self.request('/api/project?project=missing',headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='OPERATION_REFUSED'))
    def test_unknown_post_fields_refused(self):self.assertEqual(self.request('/api/backup','POST',{'extra':'invented-private-text'},{'X-Outlands-Token':web.TOKEN})[0],400)


if __name__=='__main__':unittest.main()
