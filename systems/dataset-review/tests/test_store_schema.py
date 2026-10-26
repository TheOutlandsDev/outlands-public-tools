"""Fresh fictional canonical/invalid stores only; no existing database is read."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('store_schema_fixture',Path(__file__).resolve().parents[1]/'review_store.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-schema-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.store=self.base/'review.sqlite3'
        m.initialize(self.store)

    def raw(self,path,sql):
        con=sqlite3.connect(path)
        try:con.executescript(sql)
        finally:con.close()

    def cli(self,*args,store=None):
        output=io.StringIO()
        with redirect_stdout(output):code=m.main(['--store',str(store or self.store),*args])
        import json
        return code,json.loads(output.getvalue())

    def reject_unchanged(self,path):
        before=path.read_bytes()
        code,result=self.cli('list',store=path)
        self.assertEqual((code,result),(2,{'status':'ERROR','code':'REVIEW_OPERATION_FAILED'}))
        self.assertEqual(path.read_bytes(),before)

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_DATASET_REQUIRE_LINKS')=='1':raise AssertionError('Required native '+name+' creation failed') from error
        self.skipTest('Native '+name+' creation unavailable')

    def symlink(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:self.feature_failure(error,'symlink')

    def hardlink(self,path,target):
        try:os.link(target,path)
        except OSError as error:self.feature_failure(error,'hardlink')

    def junction(self,path,target):
        import subprocess
        result=subprocess.run(['cmd','/d','/c','mklink','/J',str(path),str(target)],capture_output=True,timeout=10)
        if result.returncode:self.feature_failure(RuntimeError('Fictional junction creation failed'),'junction')
        self.assertTrue(path.is_junction())
        self.addCleanup(lambda:os.rmdir(path) if path.is_junction() else None)


class StoreAcceptance(Fixture):
    def test_original_unversioned_format_is_accepted_without_migration(self):
        legacy=self.base/'legacy.sqlite3'
        self.raw(legacy,m.SCHEMA)
        before=legacy.read_bytes()
        self.assertEqual(m.records(legacy),[])
        self.assertEqual(legacy.read_bytes(),before)
        con=sqlite3.connect(legacy)
        try:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertEqual(con.execute('PRAGMA application_id').fetchone()[0],0)
        finally:con.close()

    def test_new_store_retains_canonical_schema_and_zero_markers(self):
        with m.connect(self.store) as con:
            self.assertEqual(con.execute('PRAGMA user_version').fetchone()[0],0)
            self.assertEqual(con.execute('PRAGMA application_id').fetchone()[0],0)
            self.assertEqual(con.execute("SELECT count(*) FROM sqlite_schema WHERE type='table'").fetchone()[0],5)

    def test_extra_table_is_rejected_without_mutation(self):
        self.raw(self.store,'CREATE TABLE fictional_extra(value TEXT);')
        self.reject_unchanged(self.store)

    def test_unexpected_trigger_is_never_run(self):
        self.raw(self.store,'CREATE TRIGGER fictional_trigger AFTER INSERT ON records BEGIN DELETE FROM groups; END;')
        source=self.base/'input.jsonl'
        source.write_bytes(b'{"text":"Fictional record","group":"demo"}\n')
        before=self.store.read_bytes()
        self.assertEqual(self.cli('import','--input',str(source))[0],2)
        self.assertEqual(self.store.read_bytes(),before)

    def test_unexpected_view_is_rejected_without_evaluation(self):
        self.raw(self.store,"CREATE VIEW fictional_view AS SELECT load_extension('fictional');")
        self.reject_unchanged(self.store)

    def test_altered_column_name_and_type_are_rejected(self):
        for index,sql in enumerate((m.SCHEMA.replace('note TEXT','annotation TEXT'),m.SCHEMA.replace('body TEXT','body BLOB'))):
            path=self.base/('changed'+str(index)+'.sqlite3')
            self.raw(path,sql)
            self.reject_unchanged(path)

    def test_constraint_and_default_changes_are_rejected(self):
        for index,sql in enumerate((m.SCHEMA.replace('body TEXT NOT NULL','body TEXT'),m.SCHEMA.replace("DEFAULT 'pending'","DEFAULT 'approved'"),m.SCHEMA.replace(' REFERENCES groups(id)',''),m.SCHEMA.replace('id TEXT PRIMARY KEY','id TEXT',1))):
            path=self.base/('constraint'+str(index)+'.sqlite3')
            self.raw(path,sql)
            self.reject_unchanged(path)

    def test_extra_index_is_rejected(self):
        self.raw(self.store,'CREATE INDEX fictional_index ON records(status);')
        self.reject_unchanged(self.store)

    def test_missing_table_is_rejected(self):
        self.raw(self.store,'DROP TABLE reviews;')
        self.reject_unchanged(self.store)

    def test_non_database_header_is_rejected_before_sqlite_open(self):
        path=self.base/'not-a-store.bin'
        path.write_bytes(b'FICTIONAL_PRIVATE_DETAIL'*8)
        with mock.patch.object(m.sqlite3,'connect',side_effect=AssertionError('NON_DATABASE_OPENED')):self.reject_unchanged(path)

    def test_empty_and_truncated_stores_are_rejected_before_sqlite_open(self):
        for index,raw in enumerate((b'',self.store.read_bytes()[:64])):
            path=self.base/('short'+str(index)+'.sqlite3')
            path.write_bytes(raw)
            with mock.patch.object(m.sqlite3,'connect',side_effect=AssertionError('TRUNCATED_OPENED')):self.reject_unchanged(path)

    def test_foreign_version_and_application_markers_are_rejected(self):
        for index,pragma in enumerate(('user_version','application_id')):
            path=self.base/('marked'+str(index)+'.sqlite3')
            self.raw(path,m.SCHEMA+'\nPRAGMA '+pragma+'=1;')
            self.reject_unchanged(path)

    def test_stored_foreign_key_violation_is_rejected(self):
        self.raw(self.store,"PRAGMA foreign_keys=OFF; INSERT INTO records(id,group_id,body) VALUES('fictional','missing','{}');")
        self.reject_unchanged(self.store)

    def test_sidecar_files_are_refused_and_left_untouched(self):
        for suffix in ('-journal','-wal','-shm'):
            path=Path(str(self.store)+suffix)
            path.write_bytes(b'fictional sidecar')
            with mock.patch.object(m.sqlite3,'connect',side_effect=AssertionError('SIDECAR_STORE_OPENED')):
                self.reject_unchanged(self.store)
            self.assertEqual(path.read_bytes(),b'fictional sidecar')
            path.unlink()

    def test_initialization_never_replaces_existing_bytes(self):
        for index,raw in enumerate((b'',b'fictional existing bytes',self.store.read_bytes())):
            path=self.base/('retained'+str(index)+'.sqlite3')
            path.write_bytes(raw)
            with self.assertRaises(FileExistsError):m.initialize(path)
            self.assertEqual(path.read_bytes(),raw)

    def test_failed_initialization_retains_file_without_partial_schema(self):
        path=self.base/'incomplete.sqlite3'
        with mock.patch.object(m,'SCHEMA','CREATE TABLE fictional_partial(value); INVALID FICTIONAL SQL;'):
            self.assertEqual(self.cli('init',store=path)[0],2)
        self.assertTrue(path.is_file())
        con=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
        try:self.assertEqual(con.execute('SELECT name FROM sqlite_schema').fetchall(),[])
        finally:con.close()
        self.assertEqual(self.cli('list',store=path)[0],2)

    def test_interruption_after_schema_commit_retains_unconfirmed_store(self):
        path=self.base/'unconfirmed.sqlite3'
        with mock.patch.object(m,'_validate_store',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.initialize(path)
        self.assertTrue(path.exists())
        self.assertEqual(m.records(path),[])
        with self.assertRaises(FileExistsError):m.initialize(path)

    def test_readonly_validation_precedes_writable_open(self):
        original=sqlite3.connect
        seen=[]
        def opened(database,*args,**kwargs):
            if str(database).startswith(self.store.as_uri()):seen.append(str(database))
            return original(database,*args,**kwargs)
        with mock.patch.object(m.sqlite3,'connect',side_effect=opened):m.records(self.store)
        self.assertEqual(seen,[self.store.as_uri()+'?mode=ro',self.store.as_uri()+'?mode=rw'])
        self.raw(self.store,'CREATE TABLE unexpected(value);')
        seen.clear()
        with mock.patch.object(m.sqlite3,'connect',side_effect=opened):self.reject_unchanged(self.store)
        self.assertEqual(seen,[self.store.as_uri()+'?mode=ro'])

    def test_connection_safety_settings_are_enabled(self):
        with m.connect(self.store) as con:
            self.assertEqual(con.execute('PRAGMA trusted_schema').fetchone()[0],0)
            self.assertEqual(con.execute('PRAGMA foreign_keys').fetchone()[0],1)
            if hasattr(con,'getconfig') and hasattr(sqlite3,'SQLITE_DBCONFIG_DEFENSIVE'):
                self.assertTrue(con.getconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE))
            with self.assertRaises(sqlite3.Error):con.execute("SELECT load_extension('fictional')")

    def test_application_transactions_still_commit_and_roll_back(self):
        with m.connect(self.store) as con:con.execute("INSERT INTO groups VALUES('committed','train')")
        with self.assertRaises(RuntimeError):
            with m.connect(self.store) as con:
                con.execute("INSERT INTO groups VALUES('rolled-back','train')")
                raise RuntimeError('Fictional rollback')
        with m.connect(self.store) as con:self.assertEqual([row[0] for row in con.execute('SELECT id FROM groups')],['committed'])

    def test_independent_sqlite_backup_is_accepted(self):
        path=self.base/'backup.sqlite3'
        source,destination=sqlite3.connect(self.store),sqlite3.connect(path)
        try:source.backup(destination)
        finally:
            destination.close()
            source.close()
        self.assertEqual(m.records(path),[])

    def test_wal_mode_is_refused_before_creating_sidecars(self):
        con=sqlite3.connect(self.store)
        try:self.assertEqual(con.execute('PRAGMA journal_mode=WAL').fetchone()[0],'wal')
        finally:con.close()
        before={path.name:path.read_bytes() for path in self.base.iterdir() if path.is_file()}
        with mock.patch.object(m.sqlite3,'connect',side_effect=AssertionError('WAL_SQLITE_OPENED')):self.reject_unchanged(self.store)
        self.assertEqual({path.name:path.read_bytes() for path in self.base.iterdir() if path.is_file()},before)

    def test_hardlinked_store_is_refused_without_changes(self):
        path=self.base/'alias.sqlite3'
        self.hardlink(path,self.store)
        self.reject_unchanged(path)
        self.reject_unchanged(self.store)

    def test_validation_budget_interrupts_and_is_removed(self):
        guard=m._store_checker()
        con=sqlite3.connect(':memory:')
        try:
            with mock.patch.object(guard,'PROGRESS_CALLS',0),self.assertRaises(sqlite3.OperationalError):
                with guard.validation_budget(con):con.execute('WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<100000) SELECT sum(x) FROM n').fetchone()
            self.assertEqual(con.execute('SELECT 1').fetchone(),(1,))
        finally:con.close()

    def test_library_interruption_releases_store_descriptors(self):
        with self.assertRaises(KeyboardInterrupt):
            with m.connect(self.store):raise KeyboardInterrupt
        self.store.rename(self.base/'released.sqlite3')


@unittest.skipIf(os.name=='nt','POSIX store fixture')
class PosixStore(Fixture):
    def test_fifo_is_refused_before_file_or_sqlite_open(self):
        path=self.base/'fictional-fifo'
        os.mkfifo(path)
        with mock.patch.object(os,'open',side_effect=AssertionError('FIFO_OPENED')),mock.patch.object(sqlite3,'connect',side_effect=AssertionError('FIFO_SQLITE')):
            self.assertEqual(self.cli('list',store=path)[0],2)

    def test_socket_is_refused_before_sqlite_open(self):
        path=self.base/'fictional-socket'
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(path))
            with mock.patch.object(sqlite3,'connect',side_effect=AssertionError('SOCKET_SQLITE')):self.assertEqual(self.cli('list',store=path)[0],2)

    def test_symlink_store_and_ancestor_are_refused(self):
        alias=self.base/'alias.sqlite3'
        alias.symlink_to(self.store)
        parent=self.base/'parent-link'
        parent.symlink_to(self.base,target_is_directory=True)
        for path in (alias,parent/self.store.name):self.reject_unchanged(path)

    def test_new_store_mode_and_store_open_flags(self):
        path=self.base/'new.sqlite3'
        m.initialize(path)
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        original=os.open
        flags=[]
        def opened(value,mode,*args,**kwargs):
            flags.append(mode)
            return original(value,mode,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=opened):m.records(path)
        for name in ('O_NOFOLLOW','O_NONBLOCK'):
            if hasattr(os,name):self.assertTrue(all(mode&getattr(os,name) for mode in flags))

    def test_sidecar_symlink_is_never_opened_or_deleted(self):
        target=self.base/'fictional-target'
        target.write_bytes(b'fictional retained')
        sidecar=Path(str(self.store)+'-journal')
        sidecar.symlink_to(target)
        with mock.patch.object(sqlite3,'connect',side_effect=AssertionError('SIDECAR_OPENED')):self.reject_unchanged(self.store)
        self.assertTrue(sidecar.is_symlink())
        self.assertEqual(target.read_bytes(),b'fictional retained')


@unittest.skipUnless(os.name=='nt','Native Windows store fixture')
class WindowsStore(Fixture):
    def test_invalid_store_spellings_stop_before_native_access(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('INVALID_STORE_OPENED')):
            for path in values:
                self.assertEqual(self.cli('list',store=path)[0],2)
                self.assertEqual(self.cli('init',store=path)[0],2)

    def test_native_repository_alias_is_refused_for_store_open(self):
        native=w.Native(w._core(m.ReviewError))
        with w.Chain(native,m.PACKAGE) as package:repository_name=package.items[-1][2]
        original=w.Native.open
        def alias(native,path,directory,expected=None,**kwargs):
            handle,identity,final=original(native,path,directory,expected,**kwargs)
            if path==self.base:final=repository_name
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=alias),mock.patch.object(sqlite3,'connect',side_effect=AssertionError('ALIAS_STORE_OPENED')):self.reject_unchanged(self.store)

    def test_symlink_main_file_is_refused(self):
        alias=self.base/'alias.sqlite3'
        self.symlink(alias,self.store)
        self.reject_unchanged(alias)

    def test_symlink_main_ancestor_is_refused(self):
        alias=self.base/'parent-link'
        self.symlink(alias,self.base,True)
        self.reject_unchanged(alias/self.store.name)

    def test_junction_main_ancestor_is_refused(self):
        alias=self.base/'parent-junction'
        self.junction(alias,self.base)
        self.reject_unchanged(alias/self.store.name)

    def test_symlink_sidecar_is_refused_without_target_changes(self):
        sidecar=Path(str(self.store)+'-journal')
        target=self.base/'fictional-target'
        target.write_bytes(b'fictional retained')
        self.symlink(sidecar,target)
        self.reject_unchanged(self.store)
        self.assertEqual(target.read_bytes(),b'fictional retained')

    def test_symlink_initialization_destination_is_never_replaced(self):
        alias=self.base/'alias.sqlite3'
        self.symlink(alias,self.store)
        before=self.store.read_bytes()
        self.assertEqual(self.cli('init',store=alias)[0],2)
        self.assertEqual(self.store.read_bytes(),before)

    def test_junction_initialization_parent_is_never_used(self):
        target=self.base/'outside'
        target.mkdir()
        alias=self.base/'output-junction'
        self.junction(alias,target)
        self.assertEqual(self.cli('init',store=alias/'new.sqlite3')[0],2)
        self.assertEqual(list(target.iterdir()),[])

    def test_junction_sidecar_is_refused_without_target_changes(self):
        target=self.base/'outside'
        target.mkdir()
        sidecar=Path(str(self.store)+'-wal')
        self.junction(sidecar,target)
        self.reject_unchanged(self.store)
        self.assertEqual(list(target.iterdir()),[])

    def test_short_name_store_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        directory=self.base/'fictional long store directory'
        directory.mkdir()
        path=directory/'review.sqlite3'
        m.initialize(path)
        buffer=ctypes.create_unicode_buffer(32768)
        size=method(str(path),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(path).casefold():self.skipTest('Optional short-name alias unavailable')
        self.reject_unchanged(Path(buffer.value))

    def test_main_handle_uses_attributes_and_allows_sqlite_updates(self):
        original=w.Native.open
        observed=[]
        def opened(native,path,directory,expected=None,**kwargs):
            if path==self.store and not directory:observed.append(kwargs.get('attributes_only'))
            return original(native,path,directory,expected,**kwargs)
        with mock.patch.object(w.Native,'open',new=opened):
            with m.connect(self.store) as con:con.execute("INSERT INTO groups VALUES('fictional','train')")
        self.assertEqual(observed,[True])
        self.store.rename(self.base/'released.sqlite3')


if __name__=='__main__':unittest.main()
