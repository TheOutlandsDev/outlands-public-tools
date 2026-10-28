"""Fictional project workflows, independent outcomes and native boundary checks."""
import copy
from contextlib import closing
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
from unittest import mock
import zipfile

APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from developer import application as app,contracts as c,jobs,runtime as r,source_validation as checks,web


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.addCleanup(jobs.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize();self.example=r.decode((APP/'examples/sample-project.json').read_bytes())
    def load(self):return app.import_project(r.encode(self.example))
    def project(self):return app.project('sample-project')
    def edit(self,content,path='src/sample.py',operation='save',expected=None):
        return app.edit(r.encode(dict(project_id='sample-project',expected_sha256=expected or self.project()['sha256'],path=path,content=content,operation=operation)))
    def checked(self):
        if not app.projects()['projects']:self.load()
        value=self.project();run=jobs.wait(app.validate(r.encode(dict(project_id='sample-project',expected_sha256=value['sha256'])))['job_id']);return app.artifact(run['artifact_id'])
    def request_review(self,record,status='approved',version=0):return dict(artifact_id=record['artifact_id'],artifact_sha256=record['artifact_sha256'],expected_version=version,status=status,actor='sample_reviewer',note='Fictional static review',checks=dict(quality=True,privacy=True,rights=True,context=True))


class Contracts(Fixture):
    def test_canonical_order_and_content_bytes(self):
        value=c.project(r.encode(self.example));self.assertEqual([f['path'] for f in value['files']],sorted(f['path'] for f in self.example['files']));self.assertEqual(value['files'][-1]['content'],'def total(values):\n    return sum(values)\n')
    def test_duplicate_nonfinite_and_depth_json(self):
        for raw in (b'{"a":1,"a":2}',b'{"n":NaN}',b'{"n":1e999}',b'['*70+b'0'+b']'*70):
            with self.subTest(raw=raw[:30]),self.assertRaises(r.WorkbenchError):r.decode(raw)
    def test_portable_paths_and_private_configuration_refused(self):
        for path in ('../sample.py','/sample.py','a\\sample.py','a:sample.py','.env.json','.git/config.json','CON.py','aux.txt','a./sample.py','a//sample.py','node_modules/sample.js','sample.sqlite3'):
            with self.subTest(path=path),self.assertRaises(r.WorkbenchError):c.path(path)
    def test_case_and_file_directory_collisions_refused(self):
        for names in (('sample.py','SAMPLE.py'),('a.py','a.py/sample.py')):
            value=copy.deepcopy(self.example);value['files']=[dict(path=p,content='') for p in names]
            with self.assertRaises(r.WorkbenchError):c.project(r.encode(value))
    def test_file_count_bytes_and_total_limits(self):
        with self.assertRaises(r.WorkbenchError):c.files([])
        with self.assertRaises(r.WorkbenchError):c.files([dict(path='file'+str(n)+'.txt',content='') for n in range(201)])
        with self.assertRaises(r.WorkbenchError):c.files([dict(path='sample.txt',content='é'*40000)])
        with self.assertRaises(r.WorkbenchError):c.files([dict(path='file'+str(n)+'.txt',content='x'*65536) for n in range(17)])
    def test_text_control_and_unpaired_surrogate_refused(self):
        for text in ('x\0y','\ud800'):
            with self.assertRaises(r.WorkbenchError):c.text(text,100)
    def test_unknown_fields_and_wrong_scalar_types(self):
        value=copy.deepcopy(self.example);value['extra']=True
        with self.assertRaises(r.WorkbenchError):c.project(r.encode(value))
        for value in (True,1.0,'1'):
            with self.assertRaises(r.WorkbenchError):c.integer(value,1,100)


class Validation(Fixture):
    def test_supported_formats_and_unchecked_text(self):
        result=checks.check_project(self.example);self.assertEqual(result['counts'],{'pass':4,'fail':0,'unchecked':1});self.assertFalse(result['all_files_checked']);self.assertTrue(result['passed']);self.assertFalse(result['code_executed'])
    def test_python_is_parsed_without_importing_or_execution(self):
        marker=self.root/'must-not-exist';value=copy.deepcopy(self.example);value['files']=[dict(path='sample.py',content='from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\nraise AssertionError("PROJECT_EXECUTED")\n')];self.assertTrue(checks.check_project(value)['passed']);app.import_project(r.encode(value));record=self.checked();self.assertTrue(record['payload']['result']['passed']);self.assertFalse(marker.exists())
    def test_python_syntax_error_reports_location_without_source(self):
        value=copy.deepcopy(self.example);value['files']=[dict(path='sample.py',content='def sample(:\n    SECRET_EXAMPLE = 1\n')];result=checks.check_project(value);self.assertFalse(result['passed']);self.assertEqual(result['checks'][0]['code'],'PYTHON_SYNTAX_INVALID');self.assertEqual(result['checks'][0]['line'],1);self.assertNotIn('SECRET_EXAMPLE',r.encode(result).decode())
    def test_json_duplicate_nonfinite_and_malformed_fail(self):
        for text in ('{"n":1,"n":2}','{"n":NaN}','{"n":1e999}','{'):
            value={**self.example,'files':[dict(path='sample.json',content=text)]};self.assertEqual(checks.check_project(value)['counts']['fail'],1)
    def test_xml_entities_depth_and_malformed_fail(self):
        for text in ('<!DOCTYPE x [<!ENTITY y "sample">]><x>&y;</x>','<x>'*42+'</x>'*42,'<x>'):
            value={**self.example,'files':[dict(path='sample.xml',content=text)]};self.assertEqual(checks.check_project(value)['counts']['fail'],1)
    def test_sql_preflight_and_nonexecution(self):
        self.assertEqual(checks.validate_content('sample.sql',"SELECT 'DELETE FROM sample' AS label"),'SQL_PREFLIGHT_VALID')
        for text in ('DELETE FROM sample','SELECT 1; SELECT 2','SELECT * INTO sample FROM other'):
            with self.assertRaises(r.WorkbenchError):checks.validate_content('sample.sql',text)
    def test_html_javascript_and_css_are_unchecked_and_not_rendered(self):
        for path in ('sample.html','sample.js','sample.css','sample.md','sample.txt'):self.assertEqual(checks.validate_content(path,'<script>throw Error("sample")</script>'),'NOT_CHECKED')
    def test_actual_owned_worker_returns_pinned_hashes(self):
        record=self.checked();by_path={f['path']:f for f in self.example['files']}
        for row in record['payload']['result']['checks']:self.assertEqual(row['sha256'],r.digest(by_path[row['path']]['content'].encode()))
        self.assertEqual(record['payload']['project_sha256'],self.project()['sha256'])
    def test_time_budget_result_is_not_a_pass(self):
        with mock.patch.object(checks.time,'monotonic',side_effect=[0,3]):result=checks.check_project(self.example)
        self.assertEqual(result['status'],'budget_exceeded');self.assertNotIn('passed',result)


class Revisions(Fixture):
    def test_import_idempotence_and_conflicting_id(self):
        self.assertTrue(self.load()['created']);self.assertFalse(self.load()['created']);value=copy.deepcopy(self.example);value['title']='Different'
        with self.assertRaises(r.WorkbenchError):app.import_project(r.encode(value))
    def test_edit_append_only_and_noop(self):
        self.load();old=self.project();saved=self.edit('value = 2\n');self.assertEqual(saved['version'],2);self.assertEqual(app.project('sample-project',1),old);self.assertFalse(self.edit('value = 2\n')['created']);self.assertEqual(app.history('sample-project')['versions'][1]['parent_sha256'],old['sha256'])
    def test_stale_edit_and_validation_leave_draft_and_history(self):
        self.load();old=self.project();self.edit('value = 2\n');before=app.history('sample-project')
        with self.assertRaises(r.WorkbenchError):self.edit('private_draft = 3\n',expected=old['sha256'])
        with self.assertRaises(r.WorkbenchError):app.validate(r.encode(dict(project_id='sample-project',expected_sha256=old['sha256'])))
        self.assertEqual(app.history('sample-project'),before)
    def test_add_delete_and_last_file_refusal(self):
        self.load();self.edit('sample\n','notes/new.txt');self.assertEqual(len(self.project()['definition']['files']),6);self.edit(None,'notes/new.txt','delete');self.assertEqual(len(self.project()['definition']['files']),5)
        for file in list(self.project()['definition']['files'])[:-1]:self.edit(None,file['path'],'delete')
        with self.assertRaises(r.WorkbenchError):self.edit(None,self.project()['definition']['files'][0]['path'],'delete')
    def test_fork_preserves_saved_contents(self):
        self.load();value=self.project()['definition'];fork={**value,'project_id':'sample-fork'};app.import_project(r.encode(fork));self.assertEqual(app.project('sample-fork')['definition']['files'],value['files'])
    def test_diff_has_independent_added_deleted_modified_outcomes(self):
        self.load();self.edit('value = 2\n');self.edit('new\n','notes/new.txt');self.edit(None,'queries/sample.sql','delete');result=app.compare('sample-project',1,4);self.assertEqual({row['path']:row['status'] for row in result['changes']},{'src/sample.py':'modified','notes/new.txt':'added','queries/sample.sql':'deleted'});self.assertTrue(result['source_hash_comparison_complete']);self.assertIn('+value = 2',next(row['preview'] for row in result['changes'] if row['path']=='src/sample.py'))
    def test_diff_marks_omitted_previews_and_late_line_changes(self):
        self.load();self.edit('first\n'*220,'notes/long.txt');before=self.project()['version'];self.edit('first\n'*219+'changed\n','notes/long.txt');result=app.compare('sample-project',before,before+1);self.assertFalse(result['diff_previews_complete']);self.assertEqual(len(result['changes']),1)
    def test_invalid_version_refused(self):
        self.load()
        for version in (True,0,101):
            with self.assertRaises(r.WorkbenchError):app.project('sample-project',version)


class ReviewsAndExports(Fixture):
    def test_repeated_checks_get_fresh_pending_review(self):
        first=self.checked();app.review(r.encode(self.request_review(first)));second=self.checked();self.assertNotEqual(first['artifact_sha256'],second['artifact_sha256']);self.assertEqual(second['review'],dict(status='pending',row_version=0))
    def test_approval_requires_all_checks_and_boolean_types(self):
        record=self.checked();value=self.request_review(record);value['checks']['privacy']=False
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(value))
        value['checks']['privacy']=1
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(value))
    def test_failed_static_check_cannot_be_approved(self):
        self.load();self.edit('def broken(:\n');record=self.checked()
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(self.request_review(record)))
    def test_optimistic_review_conflict_and_artifact_hash(self):
        record=self.checked();value=self.request_review(record);app.review(r.encode(value))
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(value))
        value['expected_version']=1;value['artifact_sha256']='0'*64
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(value))
    def test_export_gate_and_historical_revision_pinning(self):
        record=self.checked()
        with self.assertRaises(r.WorkbenchError):app.export(record['artifact_id'])
        app.review(r.encode(self.request_review(record)));self.edit('value = 99\n');receipt=app.export(record['artifact_id']);self.assertEqual(receipt['manifest']['project_version'],1);self.assertFalse(receipt['manifest']['public_release_authorized']);self.assertFalse(receipt['manifest']['all_files_checked']);self.assertEqual(app.artifact(record['artifact_id'])['review']['status'],'approved')
    def test_export_members_hashes_source_and_fixed_zip_metadata(self):
        record=self.checked();app.review(r.encode(self.request_review(record)));result=app.export(record['artifact_id']);raw=(self.root/result['directory']/'project-source.zip').read_bytes();self.assertEqual(result['sha256'],r.digest(raw));self.assertEqual(result['bytes'],len(raw))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertEqual(set(archive.namelist()),set(result['manifest']['files'])|{'manifest.json'})
            for info in archive.infolist():self.assertEqual(info.date_time,(2020,1,1,0,0,0));self.assertEqual(info.external_attr>>16,0o100644)
            for name,pin in result['manifest']['files'].items():data=archive.read(name);self.assertEqual(pin,dict(bytes=len(data),sha256=r.digest(data)))
            self.assertEqual(archive.read('source/src/sample.py').decode(),'def total(values):\n    return sum(values)\n')
    def test_public_source_export_does_not_execute_html_or_python(self):
        self.load();self.edit('<script>throw Error("sample")</script>','web/sample.html');record=self.checked();app.review(r.encode(self.request_review(record)));result=app.export(record['artifact_id']);self.assertFalse(result['manifest']['code_executed']);self.assertFalse(result['manifest']['all_files_checked'])
    def test_rejected_review_revokes_later_export(self):
        record=self.checked();app.review(r.encode(self.request_review(record)));app.review(r.encode(self.request_review(record,'rejected',1)))
        with self.assertRaises(r.WorkbenchError):app.export(record['artifact_id'])


class Store(Fixture):
    def test_append_only_trigger_and_schema_tamper(self):
        self.load()
        with self.assertRaises(sqlite3.IntegrityError):
            with r.connect() as con:con.execute('DELETE FROM projects')
        with r.connect() as con:con.execute('CREATE TABLE extra(value TEXT)')
        with self.assertRaises(r.WorkbenchError):app.projects()
    def test_store_limit_rolls_back_revision(self):
        self.load();old=self.project()
        with mock.patch.object(r,'MAX_STORE',1),self.assertRaises(r.WorkbenchError):self.edit('value = 3\n')
        self.assertEqual(self.project(),old)
    def test_backup_fresh_schema_and_content(self):
        self.load();result=app.backup();raw=(self.root/result['file']).read_bytes();self.assertEqual(result['sha256'],r.digest(raw))
        with closing(sqlite3.connect(self.root/result['file'])) as con:r.validate_schema(con);self.assertEqual(con.execute('SELECT COUNT(*) FROM projects').fetchone()[0],1)
    def test_revision_payload_tamper_refused(self):
        self.load();path=self.root/'database/workbench.sqlite3'
        with closing(sqlite3.connect(path)) as con:
            with con:con.execute('DROP TRIGGER project_no_update');con.execute("UPDATE projects SET definition_json='{}'")
        with self.assertRaises(r.WorkbenchError):self.project()


class WorkerLifecycle(Fixture):
    def stalled(self):
        original=subprocess.Popen
        return mock.patch.object(jobs.subprocess,'Popen',side_effect=lambda *args,**kwargs:original([sys.executable,'-I','-S','-B','-c','import time;time.sleep(30)'],stdin=kwargs['stdin'],stdout=kwargs['stdout'],stderr=kwargs['stderr'],cwd=kwargs['cwd']))
    def started(self):self.load();return app.validate(r.encode(dict(project_id='sample-project',expected_sha256=self.project()['sha256'])))['job_id']
    def wait_child(self,identifier):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            with jobs.LOCK:
                control=jobs.JOBS[identifier]['control']
                if control.children:return control.children[0]
            time.sleep(.01)
        self.fail('Owned child did not start')
    def test_parent_wall_deadline_reaps_stalled_owned_child(self):
        with self.stalled():identifier=self.started();child=self.wait_child(identifier);result=jobs.wait(identifier)
        self.assertEqual(result['status'],'budget_exceeded');self.assertIsNotNone(child.poll());self.assertEqual(app.artifact(result['artifact_id'])['payload']['result']['reason'],'PARENT_WALL_BUDGET')
    def test_owned_cancel_reaps_child_and_cannot_approve(self):
        with self.stalled():identifier=self.started();child=self.wait_child(identifier);jobs.cancel(identifier);result=jobs.wait(identifier)
        self.assertEqual(result['status'],'cancelled');self.assertIsNotNone(child.poll())
        with self.assertRaises(r.WorkbenchError):app.review(r.encode(self.request_review(app.artifact(result['artifact_id']))))
    def test_active_shutdown_cancels_and_joins(self):
        with self.stalled():identifier=self.started();child=self.wait_child(identifier);jobs.close()
        self.assertIsNotNone(child.poll());self.assertEqual(jobs.JOBS,{})
    def test_single_active_job_refuses_second(self):
        with self.stalled():identifier=self.started();self.wait_child(identifier)
        try:
            with self.assertRaises(r.WorkbenchError):self.started()
        finally:jobs.cancel(identifier);jobs.wait(identifier)


class BrowserApi(Fixture):
    def setUp(self):
        super().setUp();self.server=web.LocalServer(('127.0.0.1',0),web.Handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
    def request_http(self,path='/',method='GET',value=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            connection.request(method,path,body=r.encode(value) if value is not None else None,headers=headers or {});response=connection.getresponse();return response.status,response.read(),dict(response.getheaders())
        finally:connection.close()
    def test_html_no_store_token_and_no_source_markup(self):
        status,raw,headers=self.request_http();self.assertEqual(status,200);self.assertIn(web.TOKEN.encode(),raw);self.assertNotIn(b'__SESSION_TOKEN__',raw);self.assertEqual(headers['Cache-Control'],'no-store');self.assertIn("object-src 'none'",headers['Content-Security-Policy'])
    def test_read_write_token_and_host_origin_guards(self):
        self.assertEqual(self.request_http('/api/projects')[0],403);self.assertEqual(self.request_http('/api/backup','POST',{})[0],403);self.assertEqual(self.request_http(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request_http('/api/backup','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_fixed_errors_and_duplicate_query(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/artifact?id=bad',headers=headers);self.assertEqual(status,400);self.assertEqual(json.loads(raw),dict(error='ARTIFACT_ID_INVALID'));self.assertEqual(self.request_http('/api/project?id=a&id=b',headers=headers)[0],400)
    def test_real_validation_worker_through_http(self):
        self.load();headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/validate','POST',dict(project_id='sample-project',expected_sha256=self.project()['sha256']),headers);self.assertEqual(status,200);record=app.artifact(jobs.wait(json.loads(raw)['job_id'])['artifact_id']);self.assertEqual(record['payload']['result']['counts'],{'pass':4,'fail':0,'unchecked':1})
    def test_missing_routes_and_invalid_edit_are_safe(self):
        self.load();headers={'X-Outlands-Token':web.TOKEN};self.assertEqual(self.request_http('/api/missing',headers=headers)[0],404);self.assertEqual(self.request_http('/api/edit','POST',{},headers)[0],400);self.assertEqual(app.history('sample-project')['versions'][0]['version'],1)



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
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-project.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias.sqlite3'))
        with self.assertRaises(r.WorkbenchError):app.projects()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-project.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-project.json')
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_refused_without_blocking(self):
        path=self.root/'inbox/sample-fifo';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):r.read_bytes(path)
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-project.json:stream')
    def test_stale_lock_requires_stopped_assertion(self):
        r.close();(self.root/'.session-lock').mkdir()
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.projects(),dict(projects=[]))
    def test_actual_idle_child_termination_and_restart(self):
        self.load();r.close();child=subprocess.Popen([sys.executable,'-B',str(APP/'workbench.py'),'--workspace',str(self.root),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:self.assertEqual(json.loads(child.stdout.readline())['mode'],'LOOPBACK_DEVELOPER_UI');child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaises(r.WorkbenchError):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(len(app.projects()['projects']),1)
