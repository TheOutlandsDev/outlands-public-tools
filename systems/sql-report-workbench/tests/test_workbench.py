"""Fictional SQL/report, independent result, owned-worker and native I/O acceptance."""
from contextlib import closing
import copy
import csv
import hashlib
import http.client
import io
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
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from sql_report import application as app,contracts as c,engine,jobs,preflight,report_xml,runtime as r,snapshots,web


def sample(name):return json.loads((APP/('examples/sample-'+name+'.json')).read_text(encoding='utf-8'))
def xml():return (APP/'examples/sample-report.xml').read_text(encoding='utf-8')


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.addCleanup(jobs.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
    def load(self):return app.import_dataset(r.encode(sample('dataset')))
    def query(self,sql=None,parameters=None):
        definition=sample('query')
        if sql is not None:definition['sql']=sql;definition['parameters']=parameters or {}
        try:expected=app.document('query',definition['query_id'])['sha256']
        except r.WorkbenchError:expected=None
        return app.save_query(r.encode(dict(definition=definition,expected_sha256=expected)))
    def request(self,minimum=0):
        data=self.load();query=self.query();return dict(query_id=query['identifier'],expected_query_sha256=query['sha256'],dataset_id=data['dataset_id'],expected_dataset_sha256=data['dataset_sha256'],bindings=dict(minimum=minimum))
    def run_query(self,minimum=0):return jobs.wait(app.start_query(r.encode(self.request(minimum)))['job_id'])
    def report(self,text=None):return app.save_report(r.encode(dict(report_id='sample-report',title='Fictional report',xml=xml() if text is None else text,expected_sha256=None)))
    def validation(self,text=None):
        data=self.load();report=self.report(text);return jobs.wait(app.start_validation(r.encode(dict(report_id='sample-report',expected_report_sha256=report['sha256'],dataset_id=data['dataset_id'],expected_dataset_sha256=data['dataset_sha256'],bindings=dict(minimum=0))))['job_id'])
    def approve(self,identifier,**changes):
        record=app.artifact(identifier);value=dict(artifact_id=identifier,artifact_sha256=record['artifact_sha256'],expected_version=record['review']['row_version'],status='approved',actor='sample_reviewer',note='',checks=dict(quality=True,privacy=True,rights=True,context=True));value.update(changes);return app.review(r.encode(value))
    def worker_request(self,sql,parameters=None,bindings=None,mode='query'):
        self.load()
        with r.connect() as con:data=app._dataset(con,'sample-data')
        return dict(**snapshots.request(data['definition'],data['snapshot_file'],data['snapshot_sha256']),sql=sql,parameters=parameters or {},bindings=bindings or {},mode=mode)
    def worker(self,sql,parameters=None,bindings=None,mode='query'):return jobs.Control().execute(self.worker_request(sql,parameters,bindings,mode))


class Contracts(unittest.TestCase):
    def test_retained_mask_handles_escaped_quotes_comments(self):
        source="SELECT 'it''s; DELETE fake' AS note /* UPDATE fake */ -- DROP fake\n";preflight._check_query(source);self.assertNotIn('DELETE',preflight._masked_sql(source));self.assertNotIn('UPDATE',preflight._masked_sql(source))
    def test_retained_nested_comment_mask_is_only_preflight(self):
        source='SELECT 1 /* outer /* inner */ tail */';self.assertEqual(preflight._masked_sql(source).strip(),'SELECT 1')
    def test_dml_stacked_queries_and_procedures_refused(self):
        for source in ('DELETE FROM items','SELECT 1; SELECT 2','WITH x AS(SELECT 1) UPDATE items SET quantity=0','PRAGMA database_list','EXEC sample','SELECT 1 INTO fake'):
            with self.assertRaises(r.WorkbenchError):c.sql(source)
    def test_named_parameter_contract_exact(self):
        value=sample('query');self.assertEqual(c.query(r.encode(value))['parameters'],{'minimum':'integer'})
        for change in ({},dict(minimum='integer',extra='text')):
            value['parameters']=change
            with self.assertRaises(r.WorkbenchError):c.query(r.encode(value))
    def test_other_placeholder_styles_refused(self):
        for source in ('SELECT ?','SELECT @value','SELECT $value'):
            with self.assertRaises(r.WorkbenchError):c.sql(source)
    def test_binding_values_not_coerced(self):
        for value in (True,'3',3.0):
            with self.assertRaises(r.WorkbenchError):c.bindings({'minimum':value},{'minimum':'integer'})
        self.assertEqual(c.bindings({'minimum':None},{'minimum':'integer'}),{'minimum':None})
    def test_unknown_dataset_fields_and_rows_refused(self):
        for field,value in (('extra','fictional'),('tables',[])):
            data=sample('dataset');data[field]=value
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
        data=sample('dataset');data['tables'][0]['rows'][0].append('extra')
        with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_nullability_and_numeric_types(self):
        data=sample('dataset');data['tables'][0]['rows'][0][0]=None
        with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
        for value in (True,1.5,'3'):
            data=sample('dataset');data['tables'][0]['rows'][0][0]=value
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_identifiers_and_duplicates_refused(self):
        for name in ('sqlite_master','bad-name','A','x;drop'):
            data=sample('dataset');data['tables'][0]['name']=name
            with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
        data=sample('dataset');data['tables'].append(data['tables'][0])
        with self.assertRaises(r.WorkbenchError):c.dataset(r.encode(data))
    def test_limits_and_invalid_unicode(self):
        for source in ('SELECT 1'+(' ' *16385),'SELECT \ud800'):
            with self.assertRaises(r.WorkbenchError):c.sql(source)
        with self.assertRaises(r.WorkbenchError):c.scalar('x'*1001,'text')
        with self.assertRaises(r.WorkbenchError):c.token('CON.json')
    def test_json_duplicate_nonfinite_depth_size(self):
        for raw in (b'{"a":1,"a":2}',b'NaN',b'1e999',b'['*66+b'0'+b']'*66,b'x'*(r.MAX_INPUT+1),b'\xff'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)


class Reports(unittest.TestCase):
    def test_neutral_report_extracts_declared_fields_and_parameter_links(self):
        report=report_xml.inspect(xml().encode());self.assertEqual(report['parameters'],dict(minimum='integer'));self.assertEqual(report['datasets'][0]['parameter_links'],dict(minimum='minimum'));self.assertEqual([f['column'] for f in report['datasets'][0]['fields']],['group_name','total_quantity']);self.assertFalse(report['rendered'])
    def test_supported_rdl_namespace_is_only_structural_subset(self):
        raw=xml().replace('urn:outlands:offline-report:v1','http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition').encode();self.assertEqual(len(report_xml.inspect(raw)['datasets']),1)
    def test_doctype_entities_and_utf16_refused(self):
        for raw in (b'<!DOCTYPE Report [<!ENTITY data "fake">]>'+xml().encode(),xml().encode('utf-16')):
            with self.assertRaises(r.WorkbenchError):report_xml.inspect(raw)
    def test_external_and_executable_elements_refused(self):
        for element in ('ConnectString','DataSourceReference','Code','CodeModules','EmbeddedImages','Image','Hyperlink','Subreport','DefaultValue'):
            text=xml().replace('<DataSets>',f'<{element}>fictional</{element}><DataSets>')
            with self.assertRaisesRegex(r.WorkbenchError,'REPORT_EXTERNAL_OR_EXECUTABLE_CONTENT'):report_xml.inspect(text.encode())
    def test_unsupported_expression_and_command_types(self):
        for text in (xml().replace('=Parameters!minimum.Value','=1+2'),xml().replace('<CommandType>Text</CommandType>','<CommandType>StoredProcedure</CommandType>'),xml().replace('<DataType>Integer</DataType>','<DataType>DateTime</DataType>')):
            with self.assertRaises(r.WorkbenchError):report_xml.inspect(text.encode())
    def test_mixed_namespace_duplicate_and_unknown_root(self):
        for text in (xml().replace('<Fields>','<Fields xmlns="urn:other">'),xml().replace('</ReportParameters>','<ReportParameter Name="minimum"><DataType>Integer</DataType></ReportParameter></ReportParameters>'),xml().replace('urn:outlands:offline-report:v1','urn:unknown')):
            with self.assertRaises(r.WorkbenchError):report_xml.inspect(text.encode())
    def test_xml_size_depth_and_text_limits(self):
        for raw in (b'x'*(512*1024+1),('<Report xmlns="urn:outlands:offline-report:v1">'+'<x>'*42+'</x>'*42+'</Report>').encode(),xml().replace('SELECT g.group_name','x'*17000+'SELECT g.group_name').encode()):
            with self.assertRaises(r.WorkbenchError):report_xml.inspect(raw)


class Engine(Fixture):
    def test_join_aggregation_matches_independent_group_sum(self):
        result=self.worker(sample('query')['sql'],dict(minimum='integer'),dict(minimum=0));self.assertEqual(result['status'],'completed');data=sample('dataset');groups={row[0]:row[1] for row in data['tables'][0]['rows']};totals={}
        for _,group,quantity,_ in data['tables'][1]['rows']:totals[groups[group]]=totals.get(groups[group],0)+quantity
        self.assertEqual(result['rows'],[[key,totals[key]] for key in sorted(totals)]);self.assertFalse(result['truncated'])
    def test_bound_injection_is_plain_text(self):
        value="sample' OR 1=1 --";result=self.worker('SELECT :value AS echo',dict(value='text'),dict(value=value));self.assertEqual(result['rows'],[[value]])
    def test_function_and_schema_authorization(self):
        for sql in ("SELECT load_extension('fake')",'SELECT * FROM sqlite_master','SELECT * FROM pragma_database_list','SELECT random()'):
            result=self.worker(sql);self.assertEqual(result['status'],'refused');self.assertEqual(result['reason'],'SQL_AUTHORIZATION_REFUSED')
    def test_authorizer_is_independent_of_preflight(self):
        request=self.worker_request('DELETE FROM items')
        with patch.object(c,'sql',return_value=set()):result=engine.execute(request)
        self.assertEqual(result['status'],'refused');self.assertEqual(result['reason'],'SQL_AUTHORIZATION_REFUSED')
    def test_snapshot_unchanged_after_query_and_rejection(self):
        request=self.worker_request('SELECT COUNT(*) AS total FROM items');path=Path(request['snapshot']);before=path.read_bytes();self.assertEqual(jobs.Control().execute(request)['rows'],[[4]]);request['sql']='SELECT * FROM sqlite_schema';self.assertEqual(jobs.Control().execute(request)['status'],'refused');self.assertEqual(path.read_bytes(),before)
    def test_row_truncation_is_explicit(self):
        result=self.worker('SELECT a.item_id FROM items a CROSS JOIN items b CROSS JOIN items c CROSS JOIN items d ORDER BY a.item_id');self.assertEqual(result['status'],'completed');self.assertEqual(len(result['rows']),200);self.assertTrue(result['truncated'])
    def test_recursive_vm_budget(self):
        result=self.worker('WITH RECURSIVE nums(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM nums WHERE x<100000000) SELECT SUM(x) FROM nums');self.assertEqual(result['status'],'budget_exceeded')
    def test_result_blob_and_nonfinite_refused(self):
        for sql in ("SELECT X'4142' AS sample",'SELECT 1e999 AS sample'):
            result=self.worker(sql);self.assertEqual(result['status'],'refused');self.assertIn(result['reason'],('BLOB_RESULT_UNSUPPORTED','NONFINITE_RESULT'))
    def test_inspection_returns_columns_without_rows(self):
        result=self.worker(sample('query')['sql'],dict(minimum='integer'),dict(minimum=0),'inspect');self.assertEqual(result['columns'],['group_name','total_quantity']);self.assertFalse(result['query_executed']);self.assertEqual(result['mode'],'inspect')
    def test_owned_child_cancelled_and_reaped(self):
        request=self.request();definition=sample('query');definition['sql']='WITH RECURSIVE nums(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM nums WHERE x<100000000) SELECT SUM(x) FROM nums';definition['parameters']={};updated=app.save_query(r.encode(dict(definition=definition,expected_sha256=request['expected_query_sha256'])));request['expected_query_sha256']=updated['sha256'];request['bindings']={};started=app.start_query(r.encode(request));identifier=started['job_id'];deadline=time.monotonic()+3;child=None
        while time.monotonic()<deadline:
            with jobs.LOCK:child=jobs.JOBS[identifier]['control'].process
            if child is not None:break
            time.sleep(.001)
        self.assertIsNotNone(child);self.assertIsNone(child.poll());self.assertTrue(jobs.cancel(identifier)['cancel_requested']);result=jobs.wait(identifier);self.assertEqual(result['status'],'cancelled');self.assertIsNotNone(child.poll());self.assertEqual(app.artifact(result['artifact_id'])['payload']['result']['status'],'cancelled')
    def test_single_active_job_and_orderly_shutdown(self):
        request=self.worker_request('SELECT 1');control_entered=threading.Event();release=threading.Event()
        def task(control):control_entered.set();release.wait(2);return control.execute(request)
        identifier=jobs.start('query',task,lambda result:dict(status=result['status'],saved=False))['job_id'];self.assertTrue(control_entered.wait(2))
        try:
            with self.assertRaisesRegex(r.WorkbenchError,'JOB_ALREADY_RUNNING'):jobs.start('query',task,lambda x:x)
        finally:release.set();jobs.wait(identifier)
        jobs.close();self.assertEqual(jobs.JOBS,{})
    def test_parent_wall_deadline_reaps_stalled_owned_child(self):
        request=self.worker_request('SELECT 1');created=[];real_popen=subprocess.Popen
        def stalled(*args,**kwargs):
            child=real_popen([sys.executable,'-I','-S','-c','import time; time.sleep(30)'],**kwargs);created.append(child);return child
        with patch.object(jobs.subprocess,'Popen',side_effect=stalled):result=jobs.Control().execute(request)
        self.assertEqual(result['status'],'budget_exceeded');self.assertEqual(result['reason'],'PARENT_WALL_BUDGET');self.assertIsNotNone(created[0].poll())
    def test_orderly_shutdown_cancels_active_owned_worker(self):
        request=self.request();definition=sample('query');definition['sql']='WITH RECURSIVE nums(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM nums WHERE x<100000000) SELECT SUM(x) FROM nums';definition['parameters']={};updated=app.save_query(r.encode(dict(definition=definition,expected_sha256=request['expected_query_sha256'])));request['expected_query_sha256']=updated['sha256'];request['bindings']={};identifier=app.start_query(r.encode(request))['job_id'];child=None;deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            with jobs.LOCK:child=jobs.JOBS[identifier]['control'].process
            if child is not None:break
            time.sleep(.001)
        self.assertIsNotNone(child);jobs.close();self.assertIsNotNone(child.poll());self.assertEqual(jobs.JOBS,{});identifier=app.artifacts()['artifacts'][0]['artifact_id'];self.assertEqual(app.artifact(identifier)['payload']['result']['status'],'cancelled')


class Application(Fixture):
    def test_full_demo(self):self.assertEqual(app.demo(),dict(mode='FICTIONAL_SQL_REPORT_DEMO',groups=[['alpha',8],['beta',11]],filtered_groups=[['alpha',5],['beta',11]],query_versions=2,revision_groups=[['alpha',9],['beta',12]],report_valid=True,report_datasets=1,artifacts=4,comparison_rows_equal=False,private_export_files=7,backup_validated=True,external_connections_used=False,report_rendered=False))
    def test_immutable_dataset_and_idempotent_import(self):
        first=self.load();self.assertFalse(self.load()['created']);data=sample('dataset');data['title']='Other fictional data'
        with self.assertRaisesRegex(r.WorkbenchError,'DATASET_IMMUTABLE'):app.import_dataset(r.encode(data))
    def test_revision_history_and_stale_save(self):
        first=self.query();definition=sample('query');definition['title']='Revised fictional title';second=app.save_query(r.encode(dict(definition=definition,expected_sha256=first['sha256'])));self.assertEqual(second['version'],2);self.assertEqual(app.document('query','sample-summary',1)['definition']['title'],sample('query')['title'])
        with self.assertRaisesRegex(r.WorkbenchError,'REVISION_CONFLICT'):app.save_query(r.encode(dict(definition=definition,expected_sha256=first['sha256'])))
        self.assertEqual(len(app.history('query','sample-summary')['versions']),2)
    def test_run_pin_conflicts_refuse_before_worker(self):
        request=self.request();request['expected_dataset_sha256']='0'*64
        with self.assertRaisesRegex(r.WorkbenchError,'RUN_INPUT_CONFLICT'):app.start_query(r.encode(request))
        self.assertEqual(app.artifacts(),dict(artifacts=[]))
    def test_report_validation_detects_field_mismatch(self):
        artifact=self.validation(xml().replace('<DataField>total_quantity</DataField>','<DataField>missing_column</DataField>'));record=app.artifact(artifact['artifact_id']);self.assertEqual(record['payload']['result']['status'],'completed');self.assertFalse(record['payload']['result']['valid'])
    def test_report_query_is_unsaved_draft_and_parameters_preserved(self):
        self.report();value=app.report_query('sample-report','summary');self.assertFalse(value['saved']);self.assertEqual(value['definition']['sql'],sample('query')['sql']);self.assertEqual(value['bindings'],dict(minimum=None));self.assertEqual(app.documents('query')['documents'],[])
    def test_file_report_hash_and_boundary(self):
        raw=r.read_bytes(self.root/'inbox/sample-report.xml');self.assertEqual(report_xml.checked_text('inbox/sample-report.xml',r.digest(raw)),raw)
        with self.assertRaisesRegex(r.WorkbenchError,'REPORT_SOURCE_HASH_MISMATCH'):report_xml.checked_text('inbox/sample-report.xml','0'*64)
        with self.assertRaises(r.WorkbenchError):report_xml.checked_text('../outside.xml',r.digest(raw))
    def test_review_checks_versions_and_immutable_artifact_hash(self):
        result=self.run_query();identifier=result['artifact_id']
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_CHECKS_REQUIRED'):self.approve(identifier,checks=dict(quality=True,privacy=False,rights=True,context=True))
        self.approve(identifier)
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_VERSION_CONFLICT'):self.approve(identifier,expected_version=0)
        with self.assertRaisesRegex(r.WorkbenchError,'ARTIFACT_CONFLICT'):self.approve(identifier,artifact_sha256='0'*64)
    def test_new_runs_pending_and_incomplete_cannot_be_approved(self):
        first=self.run_query();self.approve(first['artifact_id']);second=self.run_query();self.assertEqual(app.artifact(second['artifact_id'])['review'],dict(status='pending',row_version=0));request=self.request();definition=sample('query');definition['sql']='SELECT * FROM sqlite_master';definition['parameters']={};query=app.save_query(r.encode(dict(definition=definition,expected_sha256=request['expected_query_sha256'])));request['expected_query_sha256']=query['sha256'];request['bindings']={};failed=jobs.wait(app.start_query(r.encode(request))['job_id'])
        with self.assertRaisesRegex(r.WorkbenchError,'REVIEW_INCOMPLETE_ARTIFACT'):self.approve(failed['artifact_id'])
    def test_export_approval_hashes_and_csv_formula_prefixing(self):
        self.load();query=self.query('SELECT note AS note FROM items ORDER BY item_id');data=app.dataset('sample-data');request=dict(query_id=query['identifier'],expected_query_sha256=query['sha256'],dataset_id='sample-data',expected_dataset_sha256=data['dataset_sha256'],bindings={});result=jobs.wait(app.start_query(r.encode(request))['job_id']);identifier=result['artifact_id']
        with self.assertRaisesRegex(r.WorkbenchError,'APPROVAL_REQUIRED'):app.export(identifier)
        self.approve(identifier);exported=app.export(identifier);directory=self.root/exported['directory'];manifest=exported['manifest'];self.assertFalse(manifest['public_release_authorized']);self.assertEqual({p.name for p in directory.iterdir()},set(manifest['files'])|{'manifest.json'})
        for name,item in manifest['files'].items():
            raw=(directory/name).read_bytes();self.assertEqual(item,dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        rows=list(csv.reader(io.StringIO((directory/'preview.csv').read_text(encoding='utf-8'))));self.assertEqual(rows[-1],["'=SAMPLE()"]);self.assertEqual(json.loads((directory/'result.json').read_text(encoding='utf-8'))['rows'][-1],['=SAMPLE()'])
    def test_csv_header_newline_and_html_escape(self):
        for value in ('=sample',' +sample','\tsample','@sample') :self.assertEqual(app._csv_cell(value),"'"+value)
        self.assertEqual(app._csv_cell(-2),-2);self.assertEqual(app._csv_cell(None),'')
        self.load();query=self.query("SELECT '<img src=x>' AS note");data=app.dataset('sample-data');result=jobs.wait(app.start_query(r.encode(dict(query_id=query['identifier'],expected_query_sha256=query['sha256'],dataset_id='sample-data',expected_dataset_sha256=data['dataset_sha256'],bindings={})))['job_id']);self.approve(result['artifact_id']);exported=app.export(result['artifact_id']);page=(self.root/exported['directory']/'report.html').read_text(encoding='utf-8');self.assertIn('&lt;img src=x&gt;',page);self.assertNotIn('<img src=x>',page)
    def test_comparison_and_truncated_scope(self):
        a=self.run_query(0);b=self.run_query(4);comparison=app.compare(a['artifact_id'],b['artifact_id']);self.assertTrue(comparison['same_query']);self.assertTrue(comparison['comparison_complete']);self.assertFalse(comparison['rows_equal_in_returned_order'])
    def test_snapshot_tampering_and_state_budget(self):
        self.load()
        with r.connect() as con:data=app._dataset(con,'sample-data')
        path=self.root/data['snapshot_file'];path.write_bytes(path.read_bytes()+b'fictional')
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_HASH_MISMATCH'):self.run_query()
    def test_state_budget_rolls_back_and_retains_orphan_snapshot(self):
        with patch.object(r,'MAX_STORE',1),self.assertRaisesRegex(r.WorkbenchError,'STORE_LIMIT'):self.load()
        self.assertEqual(app.datasets(),dict(datasets=[]));self.assertEqual(len(list((self.root/'snapshots').iterdir())),1);self.assertTrue(self.load()['created'])
    def test_schema_append_only_and_backup_scope(self):
        result=self.run_query();self.approve(result['artifact_id']);self.report()
        for table in ('datasets','queries','reports','artifacts','reviews'):
            with self.assertRaises(sqlite3.IntegrityError),r.connect() as con:con.execute('DELETE FROM '+table)
        saved=app.backup();self.assertFalse(saved['snapshots_included']);self.assertEqual(saved['sha256'],r.digest((self.root/saved['file']).read_bytes()))
        with closing(sqlite3.connect(self.root/saved['file'])) as con:r.validate_schema(con)
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('PRAGMA user_version=2');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_VERSION_REFUSED'):app.datasets()


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
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.datasets()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-dataset.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-dataset.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-dataset.json:stream')
    def test_stale_lock_requires_stopped_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.datasets(),dict(datasets=[]))
    def test_actual_idle_child_termination_and_restart(self):
        self.load();r.close();child=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(child.stdout.readline())['mode'],'LOOPBACK_SQL_REPORT_UI');child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(len(app.datasets()['datasets']),1)


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
    def test_read_write_token_and_host_origin_guards(self):
        self.assertEqual(self.request_http('/api/datasets')[0],403);self.assertEqual(self.request_http('/api/backup','POST',{})[0],403);self.assertEqual(self.request_http(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request_http('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_fixed_error_and_duplicate_query(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/artifact?id=bad',headers=headers);self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='ARTIFACT_ID_INVALID'));self.assertEqual(self.request_http('/api/dataset?id=a&id=b',headers=headers)[0],400)
    def test_real_worker_through_http(self):
        request=self.request();status,raw,_=self.request_http('/api/run','POST',request,{'X-Outlands-Token':web.TOKEN});self.assertEqual(status,200);job=json.loads(raw);result=jobs.wait(job['job_id']);self.assertEqual(result['status'],'completed');self.assertEqual(app.artifact(result['artifact_id'])['payload']['result']['rows'],[['alpha',8],['beta',11]])


if __name__=='__main__':unittest.main()
