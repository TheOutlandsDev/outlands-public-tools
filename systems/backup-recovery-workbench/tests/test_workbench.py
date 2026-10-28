"""Fictional copy/restore bytes, fault journals, native boundaries and owned crashes."""
from contextlib import closing
import copy
import hashlib
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
from recovery import application as app,contracts as c,filesystem as fs,journal as j,runtime as r,web

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.addCleanup(r.close);self.root=Path(self.temp.name)/'instance';r.configure(self.root,create=True);r.initialize()
    def request(self,kind='snapshot',snapshot_id=None,source='inbox/sample-files-v1',head=None):
        request=dict(source=source,exclusions=['cache'],quiescent=True) if kind=='snapshot' else dict(snapshot_id=snapshot_id)
        return dict(expected_head=head or app.overview()['head'],actor='sample_operator',reason='Fictional test workflow',request=request)
    def snapshot(self,source='inbox/sample-files-v1'):return app.snapshot(r.encode(self.request(source=source)))['job']['result']
    def restore(self,identifier):return app.restore(r.encode(self.request('restore',identifier)))['job']
    def verify(self,identifier):return app.verify(r.encode(self.request('verify',identifier)))['job']
    def policy(self,keep=1,protect=True):return dict(expected_head=app.overview()['head'],policy=dict(keep_last=keep,protect_untested=protect))
    def review(self):return dict(expected_head=app.overview()['head'],actor='sample_reviewer',reason='Fictional private review',policy=dict(keep_last=1,protect_untested=True),checks=dict(quality=True,privacy=True,rights=True,context=True))
    def hold(self,identifier,value):return app.hold(r.encode(dict(expected_head=app.overview()['head'],actor='sample_operator',reason='Fictional hold review',snapshot_id=identifier,hold=value)))
    def source_bytes(self):return {p.relative_to(self.root/'inbox/sample-files-v1').as_posix():p.read_bytes() for p in (self.root/'inbox/sample-files-v1').rglob('*') if p.is_file()}
    def last_job(self):return app.overview()['jobs'][-1]

class Contracts(Fixture):
    def test_json_duplicate_nonfinite_depth_utf8(self):
        for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*70+b'0'+b']'*70,b'\xff'):
            with self.assertRaises(r.WorkbenchError):r.decode(raw)
    def test_portable_names_and_reserved_components(self):
        for value in ('../sample','/sample','a\\b','a:stream','con.txt','AUX','a.','a ','a//b','x'*65,'é.txt'):
            with self.assertRaises(r.WorkbenchError):c.relative(value)
        self.assertEqual(c.relative('.env.example'),'.env.example')
    def test_source_scope_not_arbitrary_workspace_paths(self):
        for value in ('inbox','snapshots/sample','database/workbench.sqlite3','reports/sample','index-backups/sample'):
            with self.assertRaises(r.WorkbenchError):c.selector(value)
    def test_quiescent_assertion_and_unknown_fields_before_any_job(self):
        for change in ('false','number','extra'):
            value=self.request()
            if change=='extra':value['extra']=True
            else:value['request']['quiescent']=False if change=='false' else 1
            with self.assertRaises(r.WorkbenchError):app.snapshot(r.encode(value))
        self.assertEqual(app.overview()['jobs'],[])
    def test_exclusion_case_duplicates_limits_and_bad_types(self):
        for value in (['cache','CACHE'],['../sample'],['x'+str(n) for n in range(17)],'cache'):
            with self.assertRaises(r.WorkbenchError):c.exclusions(value)
    def test_typed_policy_and_counter_contracts(self):
        for value in (True,1.0,'1'):
            with self.assertRaises(r.WorkbenchError):c.integer(value,1,16)
        with self.assertRaises(r.WorkbenchError):c.policy(dict(keep_last=0,protect_untested=True))
        with self.assertRaises(r.WorkbenchError):c.policy(dict(keep_last=1,protect_untested=1))
    def test_control_unicode_and_size_text_refused(self):
        for value in ('x\0y','\ud800','x'*401):
            with self.assertRaises(r.WorkbenchError):c.text(value)
    def test_unregistered_snapshot_and_bad_identifier_no_new_job(self):
        for identifier in ('a'*32,'../sample'):
            with self.assertRaises(r.WorkbenchError):self.restore(identifier)
        self.assertEqual(app.overview()['jobs'],[])

class CopyAndRestore(Fixture):
    def test_independent_file_bytes_hashes_empty_dir_and_exclusions(self):
        original=self.source_bytes();result=self.snapshot();target=self.root/result['target'];manifest=json.loads((target/'manifest.json').read_text(encoding='utf-8'));self.assertEqual(result['file_count'],3);self.assertEqual(result['directory_count'],3);self.assertEqual(result['total_bytes'],39);self.assertEqual(manifest['excluded'],['cache']);self.assertEqual(set(manifest['files']),{'notes/readme.txt','data/sample.csv','empty.txt'});self.assertTrue((target/'files/empty-dir').is_dir());self.assertEqual(self.source_bytes(),original)
        expected={'notes/readme.txt':b'Fictional project.\n','data/sample.csv':b'item,count\nsample,3\n','empty.txt':b''}
        for name,raw in expected.items():self.assertEqual((target/'files'/name).read_bytes(),raw);self.assertEqual(manifest['files'][name],dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    def test_restore_drill_exact_bytes_and_new_targets(self):
        snapshot=self.snapshot();first=self.restore(snapshot['snapshot_id']);second=self.restore(snapshot['snapshot_id']);self.assertNotEqual(first['result']['target'],second['result']['target']);target=self.root/first['result']['target'];self.assertEqual((target/'files/data/sample.csv').read_bytes(),b'item,count\nsample,3\n');self.assertTrue((target/'files/empty-dir').is_dir());self.assertFalse((target/'files/cache').exists());self.assertEqual(first['result']['total_bytes'],39);self.assertEqual(self.last_job()['status'],'completed')
    def test_exclusions_record_requests_even_when_not_matched(self):
        value=self.request();value['request']['exclusions']=['cache','missing'];saved=app.snapshot(r.encode(value))['job']['result'];manifest=app.inspect_snapshot(saved['snapshot_id'])['manifest'];self.assertEqual(manifest['exclusions'],['cache','missing']);self.assertEqual(manifest['excluded'],['cache'])
    def test_empty_source_and_only_excluded_source_are_explicit(self):
        source=self.root/'inbox/sample-empty';source.mkdir();value=self.request(source='inbox/sample-empty');value['request']['exclusions']=[];saved=app.snapshot(r.encode(value))['job']['result'];self.assertEqual(saved['file_count'],0);self.assertEqual(saved['total_bytes'],0);self.restore(saved['snapshot_id'])
    def test_opaque_bytes_never_imported_or_executed(self):
        source=self.root/'inbox/sample-files-v1';raw=b'PK\x03\x04<script>throw Error("fictional")</script>\x00';(source/'opaque.bin').write_bytes(raw);result=self.snapshot();self.assertEqual((self.root/result['target']/'files/opaque.bin').read_bytes(),raw);self.assertEqual(result['file_count'],4)
    def test_excluded_subtree_is_not_read(self):
        original=r.read_bytes
        def guarded(path,*args,**kwargs):
            if 'cache' in Path(path).parts:self.fail('Excluded content was read')
            return original(path,*args,**kwargs)
        with mock.patch.object(r,'read_bytes',side_effect=guarded):self.snapshot()
    def test_stale_head_does_not_start_or_copy(self):
        value=self.request();self.snapshot();before=list((self.root/'snapshots').iterdir())
        with self.assertRaisesRegex(r.WorkbenchError,'JOURNAL_HEAD_CONFLICT'):app.snapshot(r.encode(value))
        self.assertEqual(list((self.root/'snapshots').iterdir()),before);self.assertEqual(len(app.overview()['jobs']),1)
    def test_started_event_is_durable_before_copy(self):
        original=fs.snapshot
        def inspect(identifier,request):
            state,_=j.read();self.assertEqual(state['jobs'][identifier]['status'],'started');self.assertFalse((self.root/'snapshots'/identifier).exists());return original(identifier,request)
        with mock.patch.object(fs,'snapshot',side_effect=inspect):self.snapshot()
    def test_existing_unregistered_destination_never_overwritten(self):
        identifier='a'*32;target=self.root/'snapshots'/identifier;target.mkdir();(target/'retained.txt').write_bytes(b'original')
        with mock.patch.object(app.uuid,'uuid4',return_value=type('Fixed',(),{'hex':identifier})()):
            with self.assertRaises(r.WorkbenchError):self.snapshot()
        self.assertEqual((target/'retained.txt').read_bytes(),b'original');self.assertEqual(self.last_job()['status'],'failed');self.assertEqual(app.overview()['snapshots'],[])
    def test_casefold_exclusion_and_missing_prefix_coverage(self):
        value=self.request();value['request']['exclusions']=['CACHE'];saved=app.snapshot(r.encode(value))['job']['result'];self.assertEqual(saved['excluded_count'],1);self.assertEqual(saved['file_count'],3)
    def test_file_total_directory_and_entry_limits_fail_before_commit(self):
        for attribute,limit in (('MAX_FILES',2),('MAX_DIRS',1),('MAX_ENTRIES',2),('MAX_TOTAL',10),('MAX_FILE',10)):
            with self.subTest(attribute=attribute),mock.patch.object(c,attribute,limit):
                with self.assertRaises(r.WorkbenchError):self.snapshot()
            self.assertEqual(self.last_job()['status'],'failed');self.assertEqual(app.overview()['snapshots'],[])
    def test_manifest_view_does_not_claim_payload_verification(self):
        saved=self.snapshot();view=app.inspect_snapshot(saved['snapshot_id']);self.assertFalse(view['payload_reverified']);self.assertEqual(view['manifest']['total_bytes'],39)

class IntegrityAndFailures(Fixture):
    def test_partial_copy_failure_retains_files_and_hides_native_message(self):
        original=r.write_new;before=self.source_bytes()
        def fail(path,raw):
            if 'snapshots' in Path(path).parts and Path(path).name=='empty.txt':raise OSError('PRIVATE_NATIVE_MESSAGE')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=fail):
            with self.assertRaisesRegex(r.WorkbenchError,'FILESYSTEM_REFUSED'):self.snapshot()
        row=self.last_job();target=self.root/'snapshots'/row['job_id'];self.assertTrue((target/'files/data/sample.csv').is_file());self.assertFalse((target/'COMMITTED.json').exists());self.assertEqual(app.overview()['snapshots'],[]);self.assertEqual(self.source_bytes(),before);self.assertNotIn('PRIVATE_NATIVE_MESSAGE',r.encode(app.history()).decode())
    def test_changed_source_during_copy_is_not_registered(self):
        original=r.write_new
        def mutate(path,raw):
            original(path,raw)
            if 'snapshots' in Path(path).parts and Path(path).name=='sample.csv':(self.root/'inbox/sample-files-v1/notes/readme.txt').write_bytes(b'Changed fictional source.\n')
        with mock.patch.object(r,'write_new',side_effect=mutate):
            with self.assertRaisesRegex(r.WorkbenchError,'SOURCE_CHANGED'):self.snapshot()
        self.assertEqual(self.last_job()['status'],'failed');self.assertEqual(app.overview()['snapshots'],[])
    def test_payload_corruption_blocks_verify_and_restore(self):
        saved=self.snapshot();(self.root/saved['target']/'files/data/sample.csv').write_bytes(b'corrupt fictional bytes')
        for operation in (self.verify,self.restore):
            with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_CONTENT_MISMATCH'):operation(saved['snapshot_id'])
            self.assertEqual(self.last_job()['status'],'failed')
        self.assertEqual(list((self.root/'restores').iterdir()),[])
    def test_extra_file_and_missing_empty_directory_refused(self):
        saved=self.snapshot();root=self.root/saved['target']/'files';(root/'extra.txt').write_bytes(b'fictional')
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_INVENTORY_MISMATCH'):self.verify(saved['snapshot_id'])
        (root/'extra.txt').unlink();(root/'empty-dir').rmdir()
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_INVENTORY_MISMATCH'):self.verify(saved['snapshot_id'])
    def test_manifest_and_commit_marker_pins_fail_closed(self):
        saved=self.snapshot();target=self.root/saved['target'];value=json.loads((target/'manifest.json').read_text(encoding='utf-8'));value['source']='inbox/sample-files-v2';(target/'manifest.json').write_bytes(r.encode(value))
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_MANIFEST_HASH_MISMATCH'):self.verify(saved['snapshot_id'])
        saved=self.snapshot();target=self.root/saved['target'];(target/'COMMITTED.json').write_bytes(b'{}')
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_COMMIT_MISMATCH'):self.restore(saved['snapshot_id'])
    def test_whitespace_manifest_rewrite_is_detected(self):
        saved=self.snapshot();path=self.root/saved['target']/'manifest.json';path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_MANIFEST_HASH_MISMATCH'):self.verify(saved['snapshot_id'])
    def test_restore_failure_retains_partial_and_original_snapshot(self):
        saved=self.snapshot();original=r.write_new
        def fail(path,raw):
            if 'restores' in Path(path).parts and Path(path).name=='empty.txt':raise OSError('fictional')
            return original(path,raw)
        with mock.patch.object(r,'write_new',side_effect=fail):
            with self.assertRaises(r.WorkbenchError):self.restore(saved['snapshot_id'])
        row=self.last_job();target=self.root/'restores'/row['job_id'];self.assertTrue((target/'files/data/sample.csv').exists());self.assertFalse((target/'RESTORED.json').exists());self.verify(saved['snapshot_id']);self.restore(saved['snapshot_id']);self.assertTrue(target.is_dir())
    def test_completion_marker_without_completed_journal_is_not_adopted(self):
        saved=self.snapshot();identifier='b'*32;target=self.root/'snapshots'/identifier;target.mkdir();(target/'COMMITTED.json').write_bytes(b'{}')
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_NOT_REGISTERED'):self.restore(identifier)
        self.assertEqual(len(app.overview()['snapshots']),1);self.assertTrue(target.exists())

class ImportedRecovery(Fixture):
    def prepare_copy(self,fresh=False):
        saved=self.snapshot();source=self.root/saved['target']
        if fresh:
            r.close();self.root=Path(self.temp.name)/'fresh-instance';r.configure(self.root,create=True);r.initialize()
        destination=self.root/'inbox/reviewed-snapshot';shutil.copytree(source,destination)
        return saved,destination
    def restore_copy(self,pin):return app.restore_imported(r.encode(dict(expected_head=app.overview()['head'],actor='sample_recovery',reason='Independently reviewed fictional snapshot pin',request=dict(source='inbox/reviewed-snapshot',manifest_sha256=pin))))
    def test_fresh_index_can_restore_pinned_copy_without_adoption(self):
        saved,source=self.prepare_copy(fresh=True);self.assertEqual(app.overview()['jobs'],[]);result=self.restore_copy(saved['manifest_sha256'])['job'];self.assertEqual(result['kind'],'restore_imported');self.assertEqual((self.root/result['result']['target']/'files/data/sample.csv').read_bytes(),b'item,count\nsample,3\n');self.assertEqual(app.overview()['snapshots'],[]);self.assertTrue((source/'COMMITTED.json').is_file())
    def test_wrong_independent_pin_blocks_copy_and_records_failure(self):
        self.prepare_copy(fresh=True)
        with self.assertRaisesRegex(r.WorkbenchError,'SNAPSHOT_MANIFEST_HASH_MISMATCH'):self.restore_copy('0'*64)
        self.assertEqual(self.last_job()['status'],'failed');self.assertEqual(list((self.root/'restores').iterdir()),[])
    def test_portable_path_contract_blocks_received_manifest_traversal(self):
        saved,source=self.prepare_copy(fresh=True);value=json.loads((source/'manifest.json').read_text(encoding='utf-8'));value['files']={'../escape.txt':dict(bytes=0,sha256=r.digest(b''))};value['total_bytes']=0;raw=r.encode(value);(source/'manifest.json').write_bytes(raw)
        with self.assertRaisesRegex(r.WorkbenchError,'RELATIVE_PATH_INVALID'):self.restore_copy(r.digest(raw))
        self.assertFalse((self.root/'escape.txt').exists());self.assertEqual(app.overview()['snapshots'],[])

class RetentionAndRecovery(Fixture):
    def test_latest_and_untested_are_protected(self):
        first=self.snapshot();second=self.snapshot('inbox/sample-files-v2');plan=app.retention(r.encode(self.policy()));by_id={row['snapshot_id']:row for row in plan['snapshots']};self.assertIn('KEEP_LAST',by_id[second['snapshot_id']]['reasons']);self.assertIn('RESTORE_DRILL_NOT_CURRENTLY_VERIFIED',by_id[first['snapshot_id']]['reasons']);self.assertEqual(plan['candidates'],0);self.assertFalse(plan['deletion_implemented'])
    def test_verified_old_snapshot_with_current_restore_is_candidate(self):
        first=self.snapshot();self.restore(first['snapshot_id']);self.snapshot('inbox/sample-files-v2');plan=app.retention(r.encode(self.policy()));self.assertEqual(plan['candidates'],1);candidate=next(row for row in plan['snapshots'] if row['status']=='candidate');self.assertEqual(candidate['snapshot_id'],first['snapshot_id']);self.assertTrue(candidate['payload_verified']);self.assertTrue(candidate['restore_drill_verified'])
    def test_manual_hold_and_release_are_journaled(self):
        first=self.snapshot();self.restore(first['snapshot_id']);self.snapshot();self.hold(first['snapshot_id'],True);self.assertEqual(app.retention(r.encode(self.policy()))['candidates'],0);self.hold(first['snapshot_id'],False);self.assertEqual(app.retention(r.encode(self.policy()))['candidates'],1);self.assertEqual([row['event']['operation'] for row in app.history()['events']][-2:],['hold_changed','hold_changed'])
    def test_tampered_restore_revokes_current_drill_protection(self):
        first=self.snapshot();restored=self.restore(first['snapshot_id']);self.snapshot();(self.root/restored['result']['target']/'files/data/sample.csv').write_bytes(b'changed');plan=app.retention(r.encode(self.policy()));old=next(row for row in plan['snapshots'] if row['snapshot_id']==first['snapshot_id']);self.assertFalse(old['restore_drill_verified']);self.assertIn('RESTORE_DRILL_NOT_CURRENTLY_VERIFIED',old['reasons'])
    def test_corrupt_snapshot_never_becomes_candidate_even_without_drill_rule(self):
        first=self.snapshot();self.snapshot();(self.root/first['target']/'files/empty.txt').write_bytes(b'corrupt');plan=app.retention(r.encode(self.policy(protect=False)));old=next(row for row in plan['snapshots'] if row['snapshot_id']==first['snapshot_id']);self.assertIn('VERIFICATION_FAILED',old['reasons']);self.assertEqual(old['status'],'protected')
    def test_pending_job_blocks_writes_and_protects_retention(self):
        first=self.snapshot()
        with mock.patch.object(fs,'restore',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.restore(first['snapshot_id'])
        self.assertEqual(app.overview()['unfinished_jobs'],1)
        with self.assertRaisesRegex(r.WorkbenchError,'UNFINISHED_JOB_REVIEW_REQUIRED'):self.snapshot()
        plan=app.retention(r.encode(self.policy(protect=False)));self.assertIn('UNFINISHED_JOB',plan['snapshots'][0]['reasons']);recovered=app.recover(r.encode(dict(actor='sample_operator',reason='Stopped assertion')));self.assertEqual(len(recovered['interrupted_jobs']),1);self.assertFalse(recovered['automatically_replayed']);self.assertEqual(self.last_job()['status'],'interrupted')
    def test_recover_does_not_change_completed_jobs(self):
        self.snapshot();head=app.overview()['head'];result=app.recover(r.encode(dict(actor='sample_operator',reason='Stopped assertion')));self.assertEqual(result['interrupted_jobs'],[]);self.assertEqual(result['head'],head)
    def test_retention_stale_head_refused(self):
        value=self.policy();self.snapshot()
        with self.assertRaisesRegex(r.WorkbenchError,'JOURNAL_HEAD_CONFLICT'):app.retention(r.encode(value))

class JournalAndReports(Fixture):
    def test_initial_head_and_event_chain(self):
        self.assertEqual(app.overview()['head'],c.ZERO);self.snapshot();events=app.history()['events'];self.assertEqual(len(events),2);self.assertEqual(events[1]['parent_sha256'],events[0]['sha256']);self.assertEqual(events[0]['parent_sha256'],c.ZERO)
    def test_append_only_and_unexpected_schema_refused(self):
        self.snapshot()
        with r.connect() as con:
            with self.assertRaises(sqlite3.IntegrityError):con.execute('DELETE FROM events')
        with closing(sqlite3.connect(self.root/'database/workbench.sqlite3')) as con:con.execute('CREATE TABLE unexpected(value TEXT)');con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'STORE_SCHEMA_REFUSED'):app.overview()
    def test_recomputed_hash_with_invalid_typed_result_is_rejected(self):
        self.snapshot();path=self.root/'database/workbench.sqlite3'
        with closing(sqlite3.connect(path)) as con:
            trigger=con.execute("SELECT sql FROM sqlite_schema WHERE name='event_no_update'").fetchone()[0];con.execute('DROP TRIGGER event_no_update');payload=r.decode(con.execute('SELECT payload_json FROM events WHERE sequence=2').fetchone()[0].encode());payload['event']['data']['result']['file_count']=True;raw=r.encode(payload);con.execute('UPDATE events SET sha256=?,payload_json=? WHERE sequence=2',(r.digest(raw),raw.decode()));con.execute(trigger);con.commit()
        with self.assertRaisesRegex(r.WorkbenchError,'INTEGER_INVALID'):app.overview()
    def test_event_limit_reserves_a_terminal_record(self):
        with mock.patch.object(c,'MAX_EVENTS',1):
            with self.assertRaisesRegex(r.WorkbenchError,'JOURNAL_LIMIT'):self.snapshot()
        self.assertEqual(app.overview()['jobs'],[]);self.assertEqual(list((self.root/'snapshots').iterdir()),[])
    def test_job_limit_refused_before_any_copy(self):
        with mock.patch.object(c,'MAX_JOBS',0):
            with self.assertRaisesRegex(r.WorkbenchError,'JOURNAL_LIMIT'):self.snapshot()
        self.assertEqual(app.overview()['sequence'],0)
    def test_private_report_requires_boolean_review_and_fresh_head(self):
        self.snapshot();value=self.review();value['checks']['privacy']=1
        with self.assertRaisesRegex(r.WorkbenchError,'EXPORT_REVIEW_REQUIRED'):app.export(r.encode(value))
        value=self.review();self.snapshot()
        with self.assertRaisesRegex(r.WorkbenchError,'JOURNAL_HEAD_CONFLICT'):app.export(r.encode(value))
        self.assertEqual(list((self.root/'reports').iterdir()),[])
    def test_metadata_report_hashes_and_no_file_payloads(self):
        self.snapshot();first=app.export(r.encode(self.review()));second=app.export(r.encode(self.review()));self.assertNotEqual(first['directory'],second['directory']);folder=self.root/first['directory'];manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'));self.assertFalse(manifest['public_release_authorized']);self.assertFalse(manifest['includes_snapshot_bytes']);self.assertEqual({p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()},set(manifest['files'])|{'manifest.json'})
        for name,pin in manifest['files'].items():raw=(folder/name).read_bytes();self.assertEqual(pin,dict(bytes=len(raw),sha256=r.digest(raw)));self.assertNotIn(b'Fictional project.',raw)
    def test_metadata_index_backup_replays_but_contains_no_snapshot_payloads(self):
        self.snapshot();saved=app.backup_index();path=self.root/saved['file'];self.assertFalse(saved['includes_snapshot_bytes']);self.assertEqual(saved['sha256'],r.digest(path.read_bytes()))
        with closing(sqlite3.connect(path)) as con:r.validate_schema(con);state,_=j.load(con);self.assertEqual(state['head'],app.overview()['head'])
        self.assertNotIn(b'Fictional project.',path.read_bytes())
    def test_sidecar_and_existing_output_refused(self):
        target=self.root/'reports/retained';r.write_new(target,b'original')
        with self.assertRaises(r.WorkbenchError):r.write_new(target,b'replacement')
        self.assertEqual(target.read_bytes(),b'original');(self.root/'database/workbench.sqlite3-wal').write_bytes(b'fictional')
        with self.assertRaises(r.WorkbenchError):app.overview()

class NativeBoundaries(Fixture):
    def make_link(self,action):
        try:action()
        except (OSError,subprocess.SubprocessError):
            if os.environ.get('WORKBENCH_REQUIRE_LINKS')=='1':self.fail('Native link fixture required')
            self.skipTest('Native link fixture unavailable on this filesystem')
    def test_native_hardlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.link(self.root/'inbox/sample-tree.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_database_hardlink_refused(self):
        self.make_link(lambda:os.link(self.root/'database/workbench.sqlite3',self.root/'database/alias'))
        with self.assertRaises(r.WorkbenchError):app.overview()
    def test_native_symlink_input_refused(self):
        target=self.root/'inbox/alias';self.make_link(lambda:os.symlink(self.root/'inbox/sample-tree.json',target))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target)
    def test_native_symlink_parent_refused(self):
        target=self.root/'alias';self.make_link(lambda:os.symlink(self.root/'inbox',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):r.read_bytes(target/'sample-tree.json')
    def test_native_snapshot_source_hardlink_refused(self):
        source=self.root/'inbox/sample-files-v1';self.make_link(lambda:os.link(source/'empty.txt',source/'alias.txt'))
        with self.assertRaises(r.WorkbenchError):self.snapshot()
        self.assertEqual(app.overview()['snapshots'],[])
    def test_native_snapshot_source_directory_link_refused(self):
        source=self.root/'inbox/sample-files-v1';target=source/'alias-directory'
        if os.name=='nt':
            script=self.root/'inbox/junction-fixture.ps1';script.write_text('param([string]$LinkPath,[string]$TargetPath)\n$ErrorActionPreference="Stop"\nNew-Item -ItemType Junction -Path $LinkPath -Target $TargetPath | Out-Null\n',encoding='utf-8')
            self.make_link(lambda:subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(script),str(target),str(source/'notes')],capture_output=True,check=True,timeout=20))
        else:self.make_link(lambda:os.symlink(source/'notes',target,target_is_directory=True))
        with self.assertRaises(r.WorkbenchError):self.snapshot()
        self.assertEqual(app.overview()['snapshots'],[])
    @unittest.skipIf(os.name=='nt','POSIX-only FIFO')
    def test_posix_fifo_source_refused_without_blocking(self):
        path=self.root/'inbox/sample-files-v1/pipe';os.mkfifo(path)
        with self.assertRaises(r.WorkbenchError):self.snapshot()
    @unittest.skipUnless(os.name=='nt','Windows-only stream names')
    def test_windows_stream_selector_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('inbox/sample-tree.json:stream')
    def test_source_repository_and_parent_escape_refused(self):
        with self.assertRaises(r.WorkbenchError):r.local_path('../outside',False)
        r.close()
        with self.assertRaises(r.WorkbenchError):r.configure(APP,create=True)
    def test_actual_child_interruption_retains_partial_and_requires_recovery(self):
        original=self.source_bytes();r.close();script="""import sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from recovery import application as a,filesystem as fs,runtime as r
r.configure(sys.argv[2])
def paused(identifier,request):
 target=r.local_path('snapshots/'+identifier,False);r.mkdir(target);r.mkdir(target/'files');r.write_new(target/'files/partial.txt',b'fictional partial');r.write_new(r.ROOT/'inbox/ready.txt',b'ready');time.sleep(30)
fs.snapshot=paused
a.snapshot(r.encode(dict(expected_head=a.overview()['head'],actor='sample_operator',reason='Fictional interrupted copy',request=dict(source='inbox/sample-files-v1',exclusions=['cache'],quiescent=True))))
""";child=subprocess.Popen([sys.executable,'-B','-c',script,str(APP),str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+10
            while not (self.root/'inbox/ready.txt').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            self.assertTrue((self.root/'inbox/ready.txt').exists());child.kill();child.communicate(timeout=10)
        finally:
            if child.poll() is None:child.kill();child.communicate(timeout=10)
        with self.assertRaisesRegex(r.WorkbenchError,'INSTANCE_BUSY_OR_STALE'):r.configure(self.root)
        r.configure(self.root,confirm_stopped=True);self.assertEqual(app.overview()['unfinished_jobs'],1);identifier=self.last_job()['job_id'];partial=self.root/'snapshots'/identifier/'files/partial.txt';self.assertEqual(partial.read_bytes(),b'fictional partial');app.recover(r.encode(dict(actor='sample_operator',reason='Stopped process assertion')));self.assertEqual(self.last_job()['status'],'interrupted');self.assertTrue(partial.exists());self.assertEqual(self.source_bytes(),original);self.assertEqual(app.overview()['snapshots'],[])

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
    def test_session_host_and_origin_guards(self):
        self.assertEqual(self.request_http('/api/overview')[0],403);self.assertEqual(self.request_http(headers={'Host':'example.invalid'})[0],403);self.assertEqual(self.request_http('/api/backup-index','POST',{},dict(Origin='https://example.invalid',**{'X-Outlands-Token':web.TOKEN}))[0],403)
    def test_unknown_delete_recover_and_execute_routes_refused(self):
        headers={'X-Outlands-Token':web.TOKEN}
        for path in ('/api/delete','/api/recover','/api/execute'):self.assertEqual(self.request_http(path,'POST',{},headers)[0],404)
        self.assertEqual(self.request_http('/api/job?id=a&id=b',headers=headers)[0],400)
    def test_actual_http_snapshot_and_manifest(self):
        headers={'X-Outlands-Token':web.TOKEN};status,raw,_=self.request_http('/api/snapshot','POST',self.request(),headers);self.assertEqual(status,200);value=json.loads(raw);identifier=value['job']['result']['snapshot_id'];status,raw,_=self.request_http('/api/manifest?id='+identifier,headers=headers);self.assertEqual(status,200);self.assertFalse(json.loads(raw)['payload_reverified'])

if __name__=='__main__':unittest.main()
