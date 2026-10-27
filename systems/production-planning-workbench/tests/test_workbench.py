"""Fictional complete application, independent arithmetic and native I/O tests."""
from contextlib import closing
import copy
from datetime import date
from decimal import Decimal
import hashlib
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
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from planning import application as app,project,runtime,web
from planning.engines import allocation,demand,identity,operator,readiness


def sample():return json.loads((APP/'examples/sample-project.json').read_text(encoding='utf-8'))
def raw(value):return runtime.encode(value)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temporary.cleanup);self.addCleanup(runtime.close)
        self.root=Path(self.temporary.name)/'instance';runtime.configure(self.root,create=True);runtime.initialize()
    def load(self):return app.import_file('inbox/sample-project.json')
    def put(self,name,value):
        path=self.root/'inbox'/name;runtime.write_new(path,raw(value));return path
    def change(self,command,expected=0,note=None,exception=None):
        p=app.plan('sample-workshop');change=dict(command=command,expected_version=expected)
        if note is not None:change['note']=note
        if exception is not None:change['exception_code']=exception
        return app.apply_action(raw(dict(project_id=p['project_id'],revision_sha256=p['revision_sha256'],action_id=p['actions'][0]['action_id'],actor='sample_reviewer',change=change)))


class Application(Fixture):
    def test_complete_demo(self):
        self.assertEqual(app.demo(),dict(mode='FICTIONAL_PLANNING_WORKBENCH_DEMO',products=2,initial_remaining_demand=160,initial_dock_allocated=25,initial_covered=85,initial_uncovered=50,initial_proposed_lots=3,action_status='ACKNOWLEDGED',private_report_files=4,revisions=2,final_uncovered=60,backup_validated=True,external_system_writes=False,lot_ids_reserved=False,shipment_execution_authorized=False))
    def test_independent_allocation_oracle(self):
        self.load();p=app.plan('sample-workshop');a,b=p['products']
        self.assertEqual([(r['order_id'],r['covered_quantity'],r['uncovered_quantity']) for r in a['allocation']['orders']],[('sample-order-001',55,0),('sample-order-002',5,45)])
        self.assertEqual([(r['lot_id'],r['quantity']) for r in a['allocation']['orders'][0]['allocations']],[('SMPAAAAB',40),('SMPAAAAC',15)])
        self.assertEqual(a['lot_proposal']['proposed_lot_ids'],('SMPAAAAE','SMPAAAAF'))
        self.assertEqual(a['lot_proposal']['allowance_demand'],50)
        self.assertEqual(b['allocation']['conservation']['covered'],25)
        self.assertEqual(b['lot_proposal']['recommended_lot_count'],1)
    def test_total_conservation_with_dock_stock(self):
        self.load()
        for p in app.plan('sample-workshop')['products']:
            c=p['allocation']['conservation'];self.assertEqual(p['remaining_demand'],p['dock_allocated_quantity']+c['covered']+c['uncovered']);self.assertEqual(c['wip_input'],c['wip_allocated']+c['wip_remaining'])
    def test_repeated_plan_does_not_change_history(self):
        self.load();before=app.history('sample-workshop');self.assertEqual(app.plan('sample-workshop'),app.plan('sample-workshop'));self.assertEqual(before,app.history('sample-workshop'))
    def test_identical_save_is_idempotent(self):
        first=self.load();result=app.save(raw(sample()),first['revision_sha256']);self.assertFalse(result['created']);self.assertEqual(result['sequence'],1)
    def test_missing_expected_revision_refused(self):
        self.load()
        with self.assertRaisesRegex(runtime.WorkbenchError,'REVISION_CONFLICT'):app.save(raw(sample()))
    def test_stale_revision_refused(self):
        first=self.load();app.revise_order('sample-workshop','inbox/sample-order-revision.json',first['revision_sha256'])
        with self.assertRaisesRegex(runtime.WorkbenchError,'REVISION_CONFLICT'):app.save(raw(sample()),first['revision_sha256'])
    def test_order_history_cannot_be_rewritten(self):
        first=self.load();value=sample();value['order_history'][0]['ordered_quantity']=71
        with self.assertRaisesRegex(runtime.WorkbenchError,'ORDER_HISTORY_APPEND_ONLY'):app.save(raw(value),first['revision_sha256'])
    def test_history_records_parent_chain(self):
        first=self.load();second=app.revise_order('sample-workshop','inbox/sample-order-revision.json',first['revision_sha256']);rows=app.history('sample-workshop')['revisions']
        self.assertEqual(len(rows),2);self.assertEqual(rows[1]['parent_sha256'],first['revision_sha256']);self.assertEqual(rows[1]['revision_sha256'],second['revision_sha256'])
    def test_report_hashes_and_no_source_paths(self):
        self.load();result=app.export('sample-workshop')
        self.assertNotIn(str(self.root),json.dumps(result))
        for name,item in result['manifest']['files'].items():
            data=(self.root/result['directory']/name).read_bytes();self.assertEqual(item,dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    def test_csv_formula_escaping(self):
        for value in ('=1+1',' +SUM(A1)','\t-3','@sample'):
            self.assertIn(b"'",app._csv([dict(value=value)],('value',)))
    def test_reports_never_replace(self):
        self.load();a=app.export('sample-workshop');b=app.export('sample-workshop');self.assertNotEqual(a['directory'],b['directory']);self.assertTrue((self.root/a['directory']/'plan.json').is_file())
    def test_backup_validates_and_is_independent(self):
        self.load();b=app.backup();path=self.root/b['file']
        with closing(sqlite3.connect(path)) as con:runtime.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM revisions').fetchone()[0],1)
        self.assertEqual(b['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
    def test_acknowledge_and_stale_operator_version(self):
        self.load();self.assertEqual(self.change('ACKNOWLEDGE')['state']['status'],'ACKNOWLEDGED')
        with self.assertRaisesRegex(runtime.WorkbenchError,'ACTION_VERSION_CONFLICT'):self.change('ACKNOWLEDGE')
    def test_exception_note_preserves_exception_code(self):
        self.load();self.change('FLAG_EXCEPTION',note='Fictional inspection',exception='SAMPLE_CHECK');state=self.change('ADD_NOTE',1,note='More fictional evidence')['state'];self.assertEqual(state['status'],'EXCEPTION');self.assertEqual(state['exception_code'],'SAMPLE_CHECK')
        self.assertEqual(self.change('RESOLVE_EXCEPTION',2,note='Fictional resolution')['state']['status'],'RESOLVED')
    def test_resolve_requires_exception(self):
        self.load()
        with self.assertRaises(operator.OperatorWorkflowConflict):self.change('RESOLVE_EXCEPTION',note='Fictional resolution')
    def test_blank_actor_refused(self):
        self.load();p=app.plan('sample-workshop')
        value=dict(project_id=p['project_id'],revision_sha256=p['revision_sha256'],action_id=p['actions'][0]['action_id'],actor=' ',change=dict(command='ACKNOWLEDGE',expected_version=0))
        with self.assertRaises(runtime.WorkbenchError):app.apply_action(raw(value))
    def test_new_revision_does_not_reuse_review(self):
        first=self.load();self.change('ACKNOWLEDGE');app.revise_order('sample-workshop','inbox/sample-order-revision.json',first['revision_sha256']);self.assertTrue(all(r['workflow']['row_version']==0 for r in app.plan('sample-workshop')['actions']))
    def test_stale_action_revision_refused(self):
        first=self.load();p=app.plan('sample-workshop');app.revise_order('sample-workshop','inbox/sample-order-revision.json',first['revision_sha256'])
        with self.assertRaisesRegex(runtime.WorkbenchError,'REVISION_CONFLICT'):app.apply_action(raw(dict(project_id=p['project_id'],revision_sha256=p['revision_sha256'],action_id=p['actions'][0]['action_id'],actor='sample_reviewer',change=dict(command='ACKNOWLEDGE',expected_version=0))))
    def test_append_only_database_triggers(self):
        self.load()
        for sql in ('UPDATE revisions SET created_utc=created_utc','DELETE FROM revisions'):
            with self.assertRaises(sqlite3.IntegrityError),runtime.connect() as con:con.execute(sql)
    def test_schema_addition_refused(self):
        with closing(sqlite3.connect(self.root/'database/planning.sqlite3')) as con:con.execute('CREATE TABLE unexpected(x)');con.commit()
        with self.assertRaisesRegex(runtime.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.projects()
    def test_database_version_refused(self):
        with closing(sqlite3.connect(self.root/'database/planning.sqlite3')) as con:con.execute('PRAGMA user_version=9')
        with self.assertRaisesRegex(runtime.WorkbenchError,'STORE_VERSION_REFUSED'):app.projects()
    def test_database_sidecars_refused(self):
        (self.root/'database/planning.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_no_implicit_network_access_in_demo(self):
        with patch('socket.socket',side_effect=AssertionError('Unexpected network access')):self.assertFalse(app.demo()['external_system_writes'])
    def test_empty_workspace_has_no_actual_records(self):self.assertEqual(app.projects(),dict(projects=[]))


class Contracts(unittest.TestCase):
    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(runtime.WorkbenchError,'JSON_DUPLICATE_KEY'):runtime.decode(b'{"x":1,"x":2}')
    def test_nonfinite_numbers(self):
        for data in (b'NaN',b'Infinity',b'1e999'):
            with self.subTest(data=data),self.assertRaises(runtime.WorkbenchError):runtime.decode(data)
    def test_depth_bound(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.decode(b'['*66+b'0'+b']'*66)
    def test_utf8_and_input_bound(self):
        for data in (bytes([255]),b'x'*(runtime.MAX_INPUT+1)):
            with self.assertRaises(runtime.WorkbenchError):runtime.decode(data)
    def test_strict_integer_types(self):
        for quantity in (True,'70',70.0):
            value=sample();value['order_history'][0]['ordered_quantity']=quantity
            with self.subTest(quantity=quantity),self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_unknown_fields_refused(self):
        value=sample();value['planning_configuration']['products'][0]['unexpected']='x'
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_unknown_product_refused(self):
        value=sample();value['order_history'][0]['part_number']='UNKNOWN'
        with self.assertRaises(demand.AutomaticLotStartError):project.calculate(project.parse(raw(value)))
    def test_duplicate_policy_product_refused(self):
        value=sample();value['lot_policies'][1]=value['lot_policies'][0]
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_conflicting_policy_sizes_refused(self):
        value=sample();value['lot_policies'][0]['lot_size']=26
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_unmapped_wip_operation_refused(self):
        value=sample();value['wip'][0]['operation']='unmapped'
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_unknown_wip_product_refused(self):
        value=sample();value['wip'][0]['part_number']='UNKNOWN'
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_duplicate_wip_ids_refused(self):
        value=sample();value['wip'].append(value['wip'][0])
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_future_configuration_refused(self):
        value=sample();value['planning_configuration']['effective_date']='2040-01-01'
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_shipment_cannot_exceed_order_quantity(self):
        value=sample();value['order_history'][0]['accepted_ship_quantity']=71
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_conflicting_same_order_version_refused(self):
        value=sample();value['order_history'].append(dict(value['order_history'][0],ordered_quantity=71))
        with self.assertRaises(demand.AutomaticLotStartConflict):project.calculate(project.parse(raw(value)))
    def test_order_replay_does_not_duplicate_events(self):
        value=sample();value['order_history'].append(value['order_history'][0]);result=project.calculate(project.parse(raw(value)));self.assertEqual(len(result['demand_events']),3)
    def test_older_order_version_refused(self):
        value=sample();order=value['order_history'][0];value['order_history'].extend([dict(order,row_version=2,ordered_quantity=71),order])
        with self.assertRaises(demand.AutomaticLotStartConflict):project.calculate(project.parse(raw(value)))
    def test_stale_handoff_refused(self):
        value=sample();value['handoffs'][0]['order_version']=2
        with self.assertRaisesRegex(runtime.WorkbenchError,'STALE_HANDOFF'):project.calculate(project.parse(raw(value)))
    def test_only_stage_seven_can_supply_dock(self):
        value=sample();value['handoffs'][0]['lots'][0]['lot_id']='SMPAAAAB'
        with self.assertRaisesRegex(runtime.WorkbenchError,'HANDOFF_LOT_INVALID'):project.calculate(project.parse(raw(value)))
    def test_dock_stock_cannot_be_double_allocated(self):
        value=sample();value['handoffs'].append(dict(order_id='sample-order-002',order_version=1,dock_date='2030-01-09',lots=[dict(lot_id='SMPAAAAD',quantity=1,cleared=True)]))
        with self.assertRaisesRegex(runtime.WorkbenchError,'HANDOFF_OVERALLOCATION'):project.calculate(project.parse(raw(value)))
    def test_unobserved_lot_identity_seed_refused(self):
        with self.assertRaises(identity.LotStartPolicyError):identity.propose_standard_lot_ids(lot_prefix='SMPA',observed_lot_ids=['OTHERAAAA'],count=1)
    def test_lot_sequence_carry_and_exhaustion(self):
        self.assertEqual(identity.propose_standard_lot_ids(lot_prefix='SMP',observed_lot_ids=['SMPAAAZ'],count=1),('SMPAABA',))
        with self.assertRaises(identity.LotStartPolicyError):identity.propose_standard_lot_ids(lot_prefix='SMP',observed_lot_ids=['SMPZZZZ'],count=1)
    def test_decimal_half_up_and_lot_ceiling_are_distinct(self):
        self.assertEqual(allocation._recommended_start(5,Decimal('1.10')),6)
        self.assertEqual(allocation._recommended_start(1,Decimal('1.01')),1)
        policy=dict(configured_products=[dict(modality='ALP',part_number='SAMPLE-A',lot_prefix='SMPA',start_factor='1.01',lot_size=1)],fail_closed_products=[])
        self.assertEqual(identity.recommend_lot_start(modality='ALP',uncovered_demand=1,observed_lot_ids=['SMPAAAAA'],policy=policy).allowance_demand,2)
    def test_priority_past_due_precedes_other_risks(self):
        rules=project.parse(raw(sample())).planning_configuration.products[0].priority_rules
        result=allocation._priority_result(planning_date=date(2030,1,10),due_date=date(2030,1,9),days_remaining=300,future_due_dates=(),rules=rules)
        self.assertEqual((result[0],result[2]),(1,'Past due'))
    def test_stage_seven_never_allocated_by_engine(self):
        value=sample();value['handoffs']=[];value['wip']=[r for r in value['wip'] if r['kanban']==7];result=project.calculate(project.parse(raw(value)));self.assertEqual(sum(p['allocation']['conservation']['covered'] for p in result['products']),0)
    def test_no_open_orders_is_valid(self):
        value=sample();value['handoffs']=[]
        for order in value['order_history']:order['cancelled']=True
        result=project.calculate(project.parse(raw(value)));self.assertEqual(sum(p['remaining_demand'] for p in result['products']),0);self.assertEqual(result['actions'],[])
    def test_readiness_decision_tree(self):
        cases=[(0,None,[],'AWAITING_DOCK'),(0,'2030-01-10',[],'LOT_EVIDENCE_REQUIRED'),(0,'2030-01-10',[dict(quantity=10,cleared=False)],'DOCKED_AWAITING_PRODUCTION_CLEARANCE'),(0,'2030-01-10',[dict(quantity=5,cleared=True)],'PARTIALLY_READY_FOR_LOGISTICS'),(0,'2030-01-10',[dict(quantity=10,cleared=True)],'READY_FOR_LOGISTICS'),(10,None,[],'SHIPPING_EVIDENCE_RECORDED')]
        for shipped,dock,lots,state in cases:
            result=readiness.project_readiness(quantity=10,shipped_quantity=shipped,dock_date=dock,lots=lots);self.assertEqual(result['readiness_state'],state);self.assertFalse(result['independently_verified']);self.assertFalse(result['shipment_authorized'])
    def test_priority_horizon_fits_the_declared_output_range(self):
        value=sample();value['planning_configuration']['products'][0]['priority_rules']['future_shipment_rank_limit']=7
        with self.assertRaises(runtime.WorkbenchError):project.parse(raw(value))
    def test_gross_lot_rounding_aggregates_before_rounding(self):
        selected=project.parse(raw(sample()));book=demand.AutomaticLotStartLedger(selected.demand_configuration)
        for index in range(2):
            book.ingest(demand.OSOrderState(order_id='sample-small-'+str(index),row_version=1,source_revision_sha256='a'*64,part_number='SAMPLE-A',ordered_quantity=10,accepted_ship_quantity=0,requested_ship_date=date(2030,1,20)))
        self.assertEqual(book.events[-1].current_recommended_lots,1);self.assertEqual(book.events[-1].recommendation_delta,0)
    def test_demand_lifecycle_and_metadata_only_revision(self):
        selected=project.parse(raw(sample()));book=demand.AutomaticLotStartLedger(selected.demand_configuration);base=selected.order_history[0]
        book.ingest(base)
        for version,changes,event_type in ((2,dict(ordered_quantity=80),'INCREASE'),(3,dict(ordered_quantity=80,accepted_ship_quantity=5),'SHIPMENT'),(4,dict(ordered_quantity=60,accepted_ship_quantity=5),'DECREASE'),(5,dict(ordered_quantity=60,accepted_ship_quantity=5,cancelled=True),'CANCEL')):
            state=base.model_copy(update=dict(row_version=version,**changes));self.assertEqual(book.ingest(state).event.event_type,event_type)
        state=base.model_copy(update=dict(row_version=6,ordered_quantity=60,accepted_ship_quantity=5,cancelled=True,requested_ship_date=date(2030,2,1)))
        result=book.ingest(state);self.assertTrue(result.state_changed_without_demand_change);self.assertIsNone(result.event);self.assertEqual(book.modality_remaining_demand('ALP'),0)


class Filesystem(Fixture):
    def test_source_cannot_be_workspace(self):
        runtime.close()
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(APP,create=True)
    def test_parent_escape_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('../outside',False)
    def test_existing_file_never_replaced(self):
        path=self.put('sample.json',{'x':1})
        with self.assertRaises(runtime.WorkbenchError):runtime.write_new(path,b'changed')
        self.assertEqual(path.read_bytes(),raw({'x':1}))
    def test_existing_instance_never_reinitialized(self):
        runtime.close()
        with self.assertRaises(runtime.WorkbenchError):runtime.configure(self.root,create=True)
    def test_native_hardlink_file_refused(self):
        source=self.root/'inbox/sample-project.json';target=self.root/'inbox/alias.json'
        self.make_link(lambda:os.link(source,target))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/planning.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(runtime.WorkbenchError):app.projects()
    def test_native_symlink_file_refused(self):
        target=self.root/'inbox/alias.json';self.make_link(lambda:os.symlink(self.root/'inbox/sample-project.json',target))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target/'sample-project.json')
    def make_link(self,action):
        try:action()
        except OSError:
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixtures required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        target=self.root/'inbox/sample-fifo';os.mkfifo(target)
        with self.assertRaises(runtime.WorkbenchError):runtime.read_bytes(target)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(runtime.WorkbenchError):runtime.local_path('inbox/sample-project.json:stream')
    def test_stale_empty_lock_requires_assertion(self):
        runtime.close();(self.root/'.session-lock').mkdir()
        with self.assertRaisesRegex(runtime.WorkbenchError,'INSTANCE_BUSY_OR_STALE'):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True);self.assertEqual(app.projects(),dict(projects=[]))
    def test_nonempty_lock_is_never_removed(self):
        runtime.close();(self.root/'.session-lock').mkdir();(self.root/'.session-lock/owned').write_bytes(b'fictional')
        with self.assertRaisesRegex(runtime.WorkbenchError,'LOCK_REFUSED'):runtime.configure(self.root,confirm_stopped=True)
    def test_actual_child_termination_and_restart(self):
        self.load();runtime.close()
        process=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertEqual(json.loads(process.stdout.readline())['mode'],'LOOPBACK_PLANNING_UI');process.kill();process.communicate(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.communicate(timeout=10)
        with self.assertRaisesRegex(runtime.WorkbenchError,'INSTANCE_BUSY_OR_STALE'):runtime.configure(self.root)
        runtime.configure(self.root,confirm_stopped=True);self.assertEqual(app.plan('sample-workshop')['sequence'],1)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request(self,path='/',method='GET',value=None,headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            client.request(method,path,body=raw(value) if value is not None else None,headers=headers or {});response=client.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:client.close()
    def test_html_and_no_cache(self):
        code,body,headers=self.request();self.assertEqual(code,200);self.assertIn(web.TOKEN.encode(),body);self.assertNotIn(b'__SESSION_TOKEN__',body);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('frame-ancestors',headers['Content-Security-Policy'])
    def test_api_reads_require_token(self):
        self.assertEqual(self.request('/api/projects')[0],403);self.assertEqual(self.request('/api/projects',headers={'X-Outlands-Token':web.TOKEN})[0],200)
    def test_host_rebinding_refused(self):self.assertEqual(self.request(headers={'Host':'example.invalid'})[0],403)
    def test_cross_origin_write_refused(self):self.assertEqual(self.request('/api/backup','POST',{},headers={'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403)
    def test_writes_require_token(self):self.assertEqual(self.request('/api/backup','POST',{})[0],403)
    def test_import_and_plan_through_http(self):
        headers={'X-Outlands-Token':web.TOKEN};code,body,_=self.request('/api/save','POST',dict(project=sample(),expected=None),headers);self.assertEqual(code,200);self.assertEqual(json.loads(body)['sequence'],1)
        code,body,_=self.request('/api/plan?project=sample-workshop',headers=headers);self.assertEqual(code,200);self.assertEqual(json.loads(body)['products'][0]['remaining_demand'],120)
    def test_fixed_error_response(self):
        code,body,_=self.request('/api/project?project=missing',headers={'X-Outlands-Token':web.TOKEN});self.assertEqual(code,400);self.assertEqual(json.loads(body),dict(error='OPERATION_REFUSED'))
    def test_unexpected_post_fields_refused(self):self.assertEqual(self.request('/api/backup','POST',dict(unexpected='invented-private-text'),{'X-Outlands-Token':web.TOKEN})[0],400)


if __name__=='__main__':unittest.main()
