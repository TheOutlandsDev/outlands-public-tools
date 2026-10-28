"""Fictional parser, transaction, provenance, failure, native I/O and HTTP evidence."""
from contextlib import closing
import copy
import http.client
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from migration import application as app,contracts as c,destination as d,engine as e,journal as j,runtime as r,web

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.rule=app.example();self.sources=[dict(path='inbox/orders.csv',format='csv'),dict(path='inbox/supplement.jsonl',format='jsonl')]
    def request(self,request,**extra):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional test evidence',request=request,**extra))
    def preview(self,sources=None,contract=None):return app.plan(self.request(dict(sources=self.sources if sources is None else sources,contract=self.rule if contract is None else contract)))['job']['result']
    def commit(self,plan,**extra):return app.import_plan(self.request(dict(plan_id=plan['plan_id'],plan_sha256=plan['plan_sha256'],accept_rejections=True,checks=dict(quality=True,privacy=True,rights=True,context=True),**extra)))['job']['result']
    def analyze(self,raw,kind='jsonl',rule=None):return e.analyze(dict(sources=[dict(path='inbox/fictional',format=kind)],contract=rule or self.rule),[(dict(path='inbox/fictional',format=kind,bytes=len(raw),sha256=r.digest(raw)),raw)])
    def row(self,**extra):return dict(id='sample-z',quantity=1,amount='1.00',active=True,note=None,**extra)
    def refused(self,fn,code):
        with self.assertRaisesRegex(r.WorkbenchError,'^'+code+'$'):fn()
    def reviewed(self,plan,imported=None):return r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional handoff',plan_id=plan['plan_id'],import_id=None if imported is None else imported['import_id'],checks=dict(quality=True,privacy=True,rights=True,context=True)))

class Parsing(Fixture):
    def test_independent_normalization_and_provenance_counts(self):
        result=e.build(dict(sources=self.sources,contract=self.rule));self.assertEqual(result['summary'],dict(input_rows=7,accepted_rows=3,duplicate_rows=2,rejected_rows=2,conflict_rows=0,conflicting_keys=0));records={item['key']:item for item in result['records']};self.assertEqual(records['sample-a']['data'],dict(id='sample-a',quantity=3,amount='12.5',active=True,note='alpha'));self.assertEqual(len(records['sample-a']['provenance']),2);self.assertEqual(len(records['sample-b']['provenance']),2);self.assertEqual(records['sample-c']['data']['amount'],'0');self.assertEqual({v['code'] for v in result['rejected']},{'INTEGER_VALUE_INVALID','REQUIRED_VALUE_MISSING'})
    def test_source_order_does_not_change_exact_fingerprint(self):self.assertEqual(e.build(dict(sources=self.sources,contract=self.rule)),e.build(dict(sources=self.sources[::-1],contract=self.rule)))
    def test_field_mapping_changes_names_without_evaluation(self):
        rule=copy.deepcopy(self.rule);rule['fields'][1]['source']='count';row=self.row();row['count']=row.pop('quantity');self.assertEqual(self.analyze(r.encode(row),rule=rule)['records'][0]['data']['quantity'],1)
    def test_conflicting_key_holds_all_variants_including_duplicates(self):
        result=e.build(dict(sources=[self.sources[0],dict(path='inbox/conflicts.jsonl',format='jsonl')],contract=self.rule));self.assertEqual(result['summary'],dict(input_rows=5,accepted_rows=1,duplicate_rows=0,rejected_rows=1,conflict_rows=3,conflicting_keys=1));self.assertEqual(len(result['conflicts'][0]['variants']),2)
    def test_unknown_fields_reject_by_default(self):self.assertEqual(self.analyze(r.encode(dict(self.row(),extra='value')))['rejected'][0]['code'],'UNKNOWN_FIELDS')
    def test_ignored_fields_are_counted_explicitly(self):
        rule=dict(self.rule,unknown_fields='ignore');result=self.analyze(r.encode(dict(self.row(),extra='value')),rule=rule);self.assertEqual(result['ignored_fields'],{'extra':1});self.assertNotIn('extra',result['records'][0]['data'])
    def test_duplicate_json_keys_are_rejected_without_raw_value_echo(self):
        result=self.analyze(b'{"id":"first","id":"second"}\n');self.assertEqual(result['rejected'][0]['code'],'JSON_DUPLICATE_KEY');self.assertNotIn('second',json.dumps(result))
    def test_json_nonfinite_values_and_scalar_rows_rejected(self):
        result=self.analyze(b'{"quantity":NaN}\nnull\n[]\n');self.assertEqual([row['code'] for row in result['rejected']],['JSON_NUMBER_INVALID','ROW_OBJECT_REQUIRED','ROW_OBJECT_REQUIRED'])
    def test_json_float_is_not_silently_coerced_to_decimal(self):
        row=self.row();row['amount']=1.25;self.assertEqual(self.analyze(r.encode(row))['rejected'][0]['code'],'DECIMAL_VALUE_INVALID')
    def test_integer_refuses_boolean_and_float(self):
        for value in (True,1.0):
            row=self.row();row['quantity']=value;self.assertEqual(self.analyze(r.encode(row))['rejected'][0]['code'],'INTEGER_INVALID')
    def test_boolean_requires_explicit_tokens(self):
        row=self.row();row['active']='yes';self.assertEqual(self.analyze(r.encode(row))['rejected'][0]['code'],'BOOLEAN_VALUE_INVALID')
    def test_decimal_canonicalization_is_exact_and_bounded(self):
        for value,expected in [('12.5000','12.5'),('-0.00','0'),('999999999999999999.123456','999999999999999999.123456')]:
            row=self.row();row['amount']=value;self.assertEqual(self.analyze(r.encode(row))['records'][0]['data']['amount'],expected)
        for value in ('1e2','01.0','1.1234567','1000000000000000000'):
            row=self.row();row['amount']=value;self.assertEqual(self.analyze(r.encode(row))['summary']['rejected_rows'],1)
    def test_optional_null_and_explicit_empty_policy(self):
        row=self.row();row['note']='';self.assertIsNone(self.analyze(r.encode(row))['records'][0]['data']['note']);self.assertEqual(self.analyze(r.encode(row),rule=dict(self.rule,empty_as_null=False))['records'][0]['data']['note'],'')
    def test_whitespace_policy_is_explicit(self):
        row=self.row();row['id']=' sample-z ';self.assertEqual(self.analyze(r.encode(row))['records'][0]['key'],'sample-z');self.assertEqual(self.analyze(r.encode(row),rule=dict(self.rule,trim_strings=False))['records'][0]['key'],' sample-z ')
    def test_json_unicode_separator_is_not_a_physical_line(self):
        row=self.row();row['note']='left\u2028right';self.assertEqual(self.analyze(json.dumps(row,ensure_ascii=False).encode())['records'][0]['data']['note'],row['note'])
    def test_csv_bom_quoted_multiline_and_line_provenance(self):
        result=self.analyze(b'\xef\xbb\xbfid,quantity,amount,active,note\r\nsample-z,1,1,true,"first\nsecond"\r\n',kind='csv');row=result['records'][0];self.assertEqual(row['data']['note'],'first\nsecond');self.assertEqual((row['provenance'][0]['first_line'],row['provenance'][0]['last_line']),(2,3))
    def test_csv_duplicate_casefold_header_and_width_refused(self):
        self.refused(lambda:self.analyze(b'id,ID\na,b\n','csv'),'CSV_HEADER_INVALID');result=self.analyze(b'id,quantity,amount,active,note\na,1\n','csv');self.assertEqual(result['rejected'][0]['code'],'CSV_ROW_WIDTH_INVALID')
    def test_invalid_csv_and_invalid_encoding_are_fatal(self):
        self.refused(lambda:self.analyze(b'id,quantity,amount,active,note\n"unfinished','csv'),'CSV_PARSE_INVALID');self.refused(lambda:self.analyze(b'\xff'),'SOURCE_ENCODING_INVALID')
    def test_blank_json_line_is_a_visible_rejection(self):
        result=self.analyze(r.encode(self.row())+b'\n\n');self.assertEqual((result['summary']['input_rows'],result['summary']['rejected_rows']),(2,1))
    def test_contract_duplicate_alias_nullable_key_and_unknown_fields_refused(self):
        for change in ('duplicate','nullable','extra'):
            rule=copy.deepcopy(self.rule)
            if change=='duplicate':rule['fields'][1]['target']='ID'
            elif change=='nullable':rule['fields'][0]['nullable']=True
            else:rule['execute']='never'
            with self.assertRaises(r.WorkbenchError):c.contract(rule)
    def test_scalar_control_surrogate_and_size_rejected(self):
        for value in ('bad\x01value','\ud800','x'*257):
            row=self.row();row['note']=value;self.assertEqual(self.analyze(r.encode(row))['summary']['rejected_rows'],1)
    def test_row_and_plan_limits_fail_closed(self):
        with mock.patch.object(c,'MAX_ROWS',1):self.refused(lambda:self.analyze(r.encode(self.row())+b'\n'+r.encode(self.row())),'ROW_LIMIT')
        with mock.patch.object(c,'MAX_PLAN',10):self.refused(lambda:self.analyze(r.encode(self.row())),'PLAN_LIMIT')
    def test_selectors_refuse_traversal_devices_streams_and_case_aliases(self):
        for value in ('../outside','inbox/../outside','inbox/NUL.txt','inbox/data:stream','inbox/end.','inbox//file','/absolute','inbox/dir\\file'):
            with self.assertRaises(r.WorkbenchError):c.selector(value)
        self.refused(lambda:c.request('plan',dict(contract=self.rule,sources=[dict(path='inbox/a',format='csv'),dict(path='inbox/A',format='csv')])),'SOURCE_SELECTION_DUPLICATE')
    def test_json_duplicate_keys_depth_and_nonfinite_request_refused(self):
        for raw in (b'{"a":1,"a":2}',b'['*70+b'0'+b']'*70,b'{"a":Infinity}'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)

class Workflows(Fixture):
    def test_complete_demo_and_source_byte_preservation(self):
        before={p.name:p.read_bytes() for p in (self.root/'inbox').iterdir()};value=app.demo();self.assertEqual((value['plans'],value['imports'],value['journal_events']),(3,1,8));self.assertTrue(value['repeat_import_refused'] and value['conflict_import_refused']);self.assertEqual(value['provenance_rows'],5);self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'inbox').iterdir()})
    def test_fresh_store_independent_sql_oracle(self):
        plan=self.preview();out=self.commit(plan)
        with closing(sqlite3.connect(self.root/out['target']/'data.sqlite3')) as con:
            rows=[json.loads(raw) for raw, in con.execute('SELECT data_json FROM records ORDER BY record_id')];self.assertEqual([row['id'] for row in rows],['sample-a','sample-b','sample-c']);self.assertEqual([row['quantity'] for row in rows],[3,7,0]);self.assertEqual(con.execute('SELECT count(*) FROM provenance').fetchone()[0],5);self.assertEqual(con.execute('SELECT count(*) FROM rejected').fetchone()[0],2)
        self.assertTrue(app.inspect_import(out['import_id'])['destination_verified'])
    def test_review_booleans_and_rejections_require_explicit_acceptance(self):
        plan=self.preview();request=dict(plan_id=plan['plan_id'],plan_sha256=plan['plan_sha256'],accept_rejections=False,checks=dict(quality=True,privacy=True,rights=True,context=True));self.refused(lambda:app.import_plan(self.request(request)),'REJECTED_ROWS_REVIEW_REQUIRED');request['accept_rejections']=True;request['checks']['privacy']=1;self.refused(lambda:app.import_plan(self.request(request)),'REVIEW_REQUIRED');self.assertEqual(len(app.overview()['jobs']),1)
    def test_conflict_and_empty_plans_cannot_create_stores(self):
        plan=self.preview(sources=[self.sources[0],dict(path='inbox/conflicts.jsonl',format='jsonl')]);self.refused(lambda:self.commit(plan),'CONFLICTING_KEYS_REQUIRE_NEW_PLAN');(self.root/'inbox/empty.jsonl').write_bytes(b'');empty=self.preview(sources=[dict(path='inbox/empty.jsonl',format='jsonl')]);self.refused(lambda:self.commit(empty),'NO_ACCEPTED_RECORDS');self.assertEqual(list((self.root/'stores').iterdir()),[])
    def test_repeat_import_refused_even_after_another_preview(self):
        first=self.preview();out=self.commit(first);raw=(self.root/out['target']/'data.sqlite3').read_bytes();second=self.preview();self.refused(lambda:self.commit(second),'EXACT_PLAN_ALREADY_IMPORTED');self.assertEqual((self.root/out['target']/'data.sqlite3').read_bytes(),raw)
    def test_changed_source_refuses_import_and_records_failed_attempt(self):
        plan=self.preview();(self.root/'inbox/orders.csv').write_bytes(b'changed');self.refused(lambda:self.commit(plan),'SOURCE_BYTES_CHANGED');state=app.overview();self.assertEqual(state['jobs'][-1]['status'],'failed');self.assertEqual(state['imports'],[])
    def test_changed_plan_pin_and_marker_refused(self):
        plan=self.preview();path=self.root/plan['target']/'plan.json';path.write_bytes(path.read_bytes()+b' ');self.refused(lambda:self.commit(plan),'PLAN_HASH_MISMATCH');self.assertEqual(app.overview()['imports'],[])
    def test_marker_tampering_visible_in_retained_preview(self):
        plan=self.preview();(self.root/plan['target']/'PLANNED.json').write_bytes(b'{}');self.refused(lambda:app.inspect_plan(plan['plan_id']),'PLAN_MARKER_MISMATCH')
    def test_stale_head_and_wrong_plan_pin_do_not_start_attempts(self):
        raw=self.request(dict(sources=self.sources,contract=self.rule));plan=self.preview();self.refused(lambda:app.plan(raw),'JOURNAL_HEAD_CONFLICT');bad=dict(plan,plan_sha256='1'*64);self.refused(lambda:self.commit(bad),'PLAN_NOT_REGISTERED_OR_PIN_MISMATCH');self.assertEqual(len(app.overview()['jobs']),1)
    def test_two_competing_preview_requests_only_one_accepted(self):
        raw=self.request(dict(sources=self.sources,contract=self.rule));results=[]
        def run():
            try:app.plan(raw);results.append('ok')
            except r.WorkbenchError as error:results.append(str(error))
        threads=[threading.Thread(target=run) for _ in range(2)]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=15);self.assertFalse(thread.is_alive())
        self.assertCountEqual(results,['ok','JOURNAL_HEAD_CONFLICT'])
    def test_partial_destination_failure_retained_without_overwrite(self):
        plan=self.preview()
        def partial(identifier,result):
            path=self.root/'stores'/identifier;r.mkdir(path);r.write_new(path/'partial.txt',b'fictional partial');raise OSError('private failure detail must not escape')
        with mock.patch.object(d,'create',partial):self.refused(lambda:self.commit(plan),'OPERATION_REFUSED')
        job=app.overview()['jobs'][-1];self.assertEqual(job['error'],'OPERATION_REFUSED');self.assertTrue((self.root/'stores'/job['job_id']/'partial.txt').is_file());self.assertEqual(app.overview()['imports'],[]);self.commit(plan);self.assertTrue((self.root/'stores'/job['job_id']/'partial.txt').is_file())
    def test_existing_output_directory_is_never_reused(self):
        identifier='1'*32;directory=self.root/'plans'/identifier;directory.mkdir();(directory/'sentinel').write_bytes(b'keep')
        with mock.patch.object(app.uuid,'uuid4',return_value=mock.Mock(hex=identifier)):self.refused(lambda:self.preview(),'FILESYSTEM_REFUSED')
        self.assertEqual((directory/'sentinel').read_bytes(),b'keep');self.assertFalse((directory/'plan.json').exists())
    def test_physical_ready_marker_without_terminal_event_not_adopted(self):
        plan=self.preview();original=j.append
        def interrupt(event,head):
            if event['operation']=='job_completed':raise KeyboardInterrupt
            return original(event,head)
        with mock.patch.object(j,'append',interrupt):
            with self.assertRaises(KeyboardInterrupt):self.commit(plan)
        state=app.overview();identifier=state['jobs'][-1]['job_id'];self.assertTrue((self.root/'stores'/identifier/'READY.json').is_file());self.refused(lambda:app.inspect_import(identifier),'IMPORT_NOT_REGISTERED');self.refused(lambda:self.preview(),'UNFINISHED_JOB_REVIEW_REQUIRED');value=app.recover(r.encode(dict(actor='sample_recovery',reason='Fictional stopped review')));self.assertEqual(value['interrupted_jobs'],[identifier]);self.assertEqual(app.overview()['imports'],[]);self.assertTrue((self.root/'stores'/identifier/'READY.json').is_file())
    def test_uncertain_completed_response_requires_history_not_retry(self):
        plan=self.preview();original=j.append
        def uncertain(event,head):
            value=original(event,head)
            if event['operation']=='job_completed':raise OSError('response interrupted')
            return value
        with mock.patch.object(j,'append',uncertain):self.refused(lambda:self.commit(plan),'OPERATION_REFUSED')
        self.assertEqual(len(app.overview()['imports']),1);self.refused(lambda:self.commit(plan),'EXACT_PLAN_ALREADY_IMPORTED')
    def test_current_sources_rechecked_after_database_construction(self):
        plan=self.preview();original=e.read_plan;calls=0
        def changed(result,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2:(self.root/'inbox/orders.csv').write_bytes(b'changed after construction')
            return original(result,**kwargs)
        with mock.patch.object(e,'read_plan',changed):self.refused(lambda:self.commit(plan),'SOURCE_BYTES_CHANGED')
        job=app.overview()['jobs'][-1];self.assertTrue((self.root/'stores'/job['job_id']/'data.sqlite3').is_file());self.assertFalse((self.root/'stores'/job['job_id']/'READY.json').exists())
    def test_store_byte_and_marker_tampering_refused(self):
        plan=self.preview();out=self.commit(plan);path=self.root/out['target']/'data.sqlite3';path.write_bytes(path.read_bytes()+b'x');self.refused(lambda:app.inspect_import(out['import_id']),'DESTINATION_HASH_MISMATCH')
    def test_store_ready_marker_is_exact(self):
        plan=self.preview();out=self.commit(plan);(self.root/out['target']/'READY.json').write_bytes(b'{}');self.refused(lambda:app.inspect_import(out['import_id']),'DESTINATION_MARKER_MISMATCH')
    def test_source_not_needed_to_inspect_verified_retained_store(self):
        plan=self.preview();out=self.commit(plan);(self.root/'inbox/orders.csv').write_bytes(b'new input');self.assertEqual(len(app.inspect_import(out['import_id'])['records']),3);self.assertFalse(app.inspect_plan(plan['plan_id'])['current_source_bytes_reverified'])
    def test_index_schema_extra_object_refused_before_replay(self):
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        self.refused(app.overview,'STORE_SCHEMA_REFUSED')
    def test_destination_schema_and_logical_readback_fail_closed(self):
        plan=self.preview();value=e.read_plan(plan)
        with closing(sqlite3.connect(':memory:')) as con:
            con.executescript(d.SCHEMA);self.refused(lambda:d.readback(con,value,plan['plan_sha256']),'DESTINATION_CONTENT_MISMATCH');con.execute('CREATE TABLE unexpected(value TEXT)');self.refused(lambda:d.validate(con),'DESTINATION_SCHEMA_REFUSED')
    def test_append_only_trigger_and_offline_hash_tampering_refused(self):
        self.preview()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            with self.assertRaisesRegex(sqlite3.IntegrityError,'append only'):con.execute('UPDATE events SET sha256=? WHERE sequence=1',('f'*64,))
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');con.execute('UPDATE events SET sha256=? WHERE sequence=1',('f'*64,));con.execute(trigger);con.commit()
        self.refused(app.overview,'JOURNAL_HASH_MISMATCH')
    def test_rehashed_terminal_type_tampering_refused_on_actual_store(self):
        self.preview()
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');payload=r.decode(con.execute('SELECT payload_json FROM events WHERE sequence=2').fetchone()[0].encode());payload['event']['data']['result']['summary']['accepted_rows']=True;raw=r.encode(payload);con.execute('UPDATE events SET sha256=?,payload_json=? WHERE sequence=2',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        self.refused(app.overview,'INTEGER_INVALID')
    def test_distinct_source_revision_creates_another_store_preserving_first(self):
        first=self.commit(self.preview());path=self.root/first['target']/'data.sqlite3';before=path.read_bytes();original=(self.root/'inbox/orders.csv').read_text(encoding='utf-8');(self.root/'inbox/orders.csv').write_text(original.replace('sample-a,3','sample-a,4'),encoding='utf-8');second=self.commit(self.preview());self.assertNotEqual(first['target'],second['target']);self.assertEqual(path.read_bytes(),before);self.assertEqual(app.inspect_import(second['import_id'])['records'][0]['quantity'],4)
    def test_destination_limit_leaves_failed_output_without_ready_marker(self):
        plan=self.preview()
        with mock.patch.object(c,'MAX_OUTPUT_STORE',1):self.refused(lambda:self.commit(plan),'DESTINATION_SIZE_LIMIT')
        job=app.overview()['jobs'][-1];self.assertEqual(job['status'],'failed');self.assertFalse((self.root/'stores'/job['job_id']/'READY.json').exists())
    def test_explicit_source_count_and_size_limits(self):
        with mock.patch.object(c,'MAX_SOURCES',1):self.refused(lambda:self.preview(),'SOURCE_COUNT_LIMIT')
        with mock.patch.object(c,'MAX_SOURCE',1):self.refused(lambda:self.preview(),'FILESYSTEM_REFUSED')
    def test_source_tree_cannot_hold_private_instance(self):
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP/'private-instance',create=True)
        self.assertFalse((APP/'private-instance').exists())
    def test_forged_typed_terminal_event_is_not_replayed(self):
        state,_=j.read();identifier='a'*32;state=j.apply(state,dict(operation='job_started',actor='sample',reason='Fictional',data=dict(job_id=identifier,kind='plan',request=dict(sources=self.sources,contract=self.rule))));value=dict(plan_id=identifier,target='plans/'+identifier,plan_sha256='1'*64,fingerprint='2'*64,summary=dict(input_rows=True,accepted_rows=1,duplicate_rows=0,rejected_rows=0,conflict_rows=0,conflicting_keys=0));self.refused(lambda:j.apply(state,dict(operation='job_completed',actor='sample',reason='Fictional',data=dict(job_id=identifier,result=value))),'INTEGER_INVALID')
    def test_job_cap_preserves_terminal_slot(self):
        with mock.patch.object(c,'MAX_EVENTS',2):self.preview();self.assertEqual(app.overview()['sequence'],2);self.refused(lambda:self.preview(),'JOURNAL_LIMIT')
    def test_reviewed_private_export_has_hashes_and_formula_escaping(self):
        plan=self.preview();out=self.commit(plan);report=app.export(self.reviewed(plan,out));directory=self.root/report['directory'];manifest=report['manifest'];self.assertFalse(manifest['public_release_authorized']);self.assertTrue(manifest['contains_normalized_values']);self.assertIn("'=SUM(1)",(directory/'accepted-display.csv').read_text(encoding='utf-8'));rows=[json.loads(line) for line in (directory/'accepted.jsonl').read_text(encoding='utf-8').splitlines()];self.assertEqual(rows[1]['note'],'=SUM(1)')
        for name,item in manifest['files'].items():raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=r.digest(raw)))
        self.assertEqual(len(list(directory.iterdir())),8)
    def test_export_review_and_import_plan_mismatch_refused(self):
        plan=self.preview();out=self.commit(plan);value=r.decode(self.reviewed(plan,out));value['checks']['privacy']=False;self.refused(lambda:app.export(r.encode(value)),'REVIEW_REQUIRED');second=self.preview();value=r.decode(self.reviewed(second,out));self.refused(lambda:app.export(r.encode(value)),'IMPORT_PLAN_MISMATCH')
    def test_index_backup_replay_and_separate_payload_boundary(self):
        self.preview();out=app.backup_index();self.assertFalse(out['includes_plan_or_store_bytes']);self.assertEqual(r.digest((self.root/out['file']).read_bytes()),out['sha256'])
        with closing(sqlite3.connect(self.root/out['file'])) as con:self.assertEqual(j.load(con)[0]['sequence'],2)
    def test_source_file_and_session_boundaries(self):
        with self.assertRaises(r.WorkbenchError):r.write_new(self.root/'inbox/orders.csv',b'no overwrite')
        r.close();(self.root/'.session-lock').mkdir();self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);self.assertEqual(app.overview()['sequence'],0)
    def test_cli_refuses_outside_request_and_keeps_error_fixed(self):
        r.close();process=subprocess.run([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'plan','--file','../outside.json'],capture_output=True,text=True);self.assertEqual(process.returncode,2);self.assertEqual(json.loads(process.stdout),dict(error='SELECTOR_INVALID'));self.assertNotIn(str(self.root),process.stdout)
    def test_actual_child_interruption_retains_partial_and_requires_recovery(self):
        r.close();program='''import sys,threading\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\nfrom migration import application as app,engine as e,runtime as r\nr.configure(sys.argv[2])\ndef stopped(identifier,request):\n p=r.ROOT/'plans'/identifier;r.mkdir(p);r.write_new(p/'PARTIAL.txt',b'fictional interrupted preview');r.write_new(r.ROOT/'owned-child-ready',b'ready');threading.Event().wait(120)\ne.write_plan=stopped\napp.plan(r.encode(dict(expected_head=app.overview()['head'],actor='sample_child',reason='Controlled interruption',request=dict(sources=[dict(path='inbox/orders.csv',format='csv')],contract=app.example()))))\n''';process=subprocess.Popen([sys.executable,'-B','-W','error','-c',program,str(APP),str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+20
            while not (self.root/'owned-child-ready').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue((self.root/'owned-child-ready').is_file());process.kill();process.communicate(timeout=10);self.refused(lambda:r.configure(self.root),'INSTANCE_BUSY_OR_STALE');r.configure(self.root,confirm_stopped=True);state=app.overview();self.assertEqual(state['unfinished_jobs'],1);self.refused(lambda:self.preview(),'UNFINISHED_JOB_REVIEW_REQUIRED');app.recover(r.encode(dict(actor='sample_recovery',reason='Owned child stopped')));state=app.overview();self.assertEqual(state['jobs'][0]['status'],'interrupted');self.assertEqual(state['plans'],[]);self.assertTrue((self.root/'plans'/state['jobs'][0]['job_id']/'PARTIAL.txt').is_file());self.assertEqual((self.root/'inbox/orders.csv').read_bytes(),(APP/'examples/orders.csv').read_bytes())
        finally:
            if process.poll() is None:process.kill()
            process.communicate(timeout=10)

class NativeBoundaries(Fixture):
    def make_link(self,action):
        try:action()
        except (OSError,subprocess.SubprocessError):
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('NATIVE_FIXTURE_REQUIRED')
            self.skipTest('Native link creation unavailable on this test filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias.csv';self.make_link(lambda:os.link(self.root/'inbox/orders.csv',target))
        with self.assertRaises(r.WorkbenchError):self.preview(sources=[dict(path='inbox/alias.csv',format='csv')])
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias'))
        with self.assertRaises(r.WorkbenchError):app.overview()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias.csv';self.make_link(lambda:os.symlink(self.root/'inbox/orders.csv',target))
        with self.assertRaises(r.WorkbenchError):self.preview(sources=[dict(path='inbox/alias.csv',format='csv')])
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'orders.csv')
    def test_native_junction_or_directory_link_input_refused(self):
        target=self.root/'inbox/alias-directory'
        if os.name=='nt':
            script=self.root/'inbox/junction-fixture.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\n$ErrorActionPreference="Stop"\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null\n',encoding='utf-8');self.make_link(lambda:subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),str(target),str(self.root/'inbox')],capture_output=True,check=True));self.addCleanup(lambda:os.rmdir(target))
        else:self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):self.preview(sources=[dict(path='inbox/alias-directory/orders.csv',format='csv')])
    def test_native_plan_hardlink_refused(self):
        plan=self.preview();self.make_link(lambda:os.link(self.root/plan['target']/'plan.json',self.root/'inbox/plan-alias.json'))
        with self.assertRaises(r.WorkbenchError):app.inspect_plan(plan['plan_id'])
    def test_native_destination_hardlink_refused(self):
        plan=self.preview();out=self.commit(plan);self.make_link(lambda:os.link(self.root/out['target']/'data.sqlite3',self.root/'inbox/store-alias'))
        with self.assertRaises(r.WorkbenchError):app.inspect_import(out['import_id'])
    @unittest.skipUnless(os.name!='nt','POSIX-only FIFO boundary')
    def test_posix_fifo_input_refused_without_blocking(self):
        path=self.root/'inbox/pipe';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):self.preview(sources=[dict(path='inbox/pipe',format='jsonl')])
    @unittest.skipUnless(os.name=='nt','Windows-only stream selector boundary')
    def test_windows_stream_selector_refused(self):self.refused(lambda:self.preview(sources=[dict(path='inbox/orders.csv:stream',format='csv')]),'SELECTOR_INVALID')

class HttpBoundaries(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def http(self,path,method='GET',body=None,headers=None):
        con=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:con.request(method,path,body=body,headers=headers or {});response=con.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:con.close()
    def test_root_security_headers_and_literal_ui_source(self):
        status,raw,headers=self.http('/');self.assertEqual(status,200);self.assertIn(b'Import & Migration Workbench',raw);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn('frame-ancestors',headers['Content-Security-Policy']);self.assertNotIn(b'innerHTML',raw)
    def test_host_token_and_origin_refused(self):
        self.assertEqual(self.http('/api/overview')[0],403);self.assertEqual(self.http('/',headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.http('/api/plan','POST',self.request(dict(sources=self.sources,contract=self.rule)),{'X-Outlands-Token':web.TOKEN,'Origin':'https://example.invalid'})[0],403)
    def test_duplicate_query_and_duplicate_body_keys_refused(self):
        headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.http('/api/job?id=a&id=b',headers=headers)[0],400);self.assertEqual(self.http('/api/plan','POST',b'{"a":1,"a":2}',headers)[0],400)
    def test_actual_http_preview_and_registered_details(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.http('/api/plan','POST',self.request(dict(sources=self.sources,contract=self.rule)),headers);self.assertEqual(status,200);identifier=json.loads(raw)['job']['result']['plan_id'];status,raw,_=self.http('/api/plan?id='+identifier,headers=headers);self.assertEqual(status,200);self.assertEqual(json.loads(raw)['plan']['summary']['accepted_rows'],3)

if __name__=='__main__':unittest.main()
