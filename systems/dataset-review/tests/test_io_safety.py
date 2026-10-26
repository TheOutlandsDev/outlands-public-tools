"""Fictional JSONL, fresh stores and disposable I/O failure fixtures only."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC=importlib.util.spec_from_file_location('dataset_io_fixture',Path(__file__).resolve().parents[1]/'review_store.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-dataset-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.store=self.base/'review.sqlite3'
        self.source=self.base/'input.jsonl'
        self.output=self.base/'export.jsonl'
        self.raw=b'{"text":"Fictional record","group":"demo"}\n'
        self.source.write_bytes(self.raw)
        m.initialize(self.store)

    def cli(self,*args):
        output=io.StringIO()
        with redirect_stdout(output):code=m.main(['--store',str(self.store),*args])
        return code,json.loads(output.getvalue())

    def approved(self):
        m.import_records(self.store,self.source)
        identifier=m.records(self.store)[0]['id']
        m.review(self.store,identifier,'approved','FictionalReviewer','Fictional review only',{key:True for key in m.CHECKS})
        return identifier

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
        result=subprocess.run(['cmd','/d','/c','mklink','/J',str(path),str(target)],capture_output=True,timeout=10)
        if result.returncode:self.feature_failure(RuntimeError('Fictional junction creation failed'),'junction')
        self.assertTrue(path.is_junction())
        self.addCleanup(lambda:os.rmdir(path) if path.is_junction() else None)


class PortableIO(Fixture):
    def test_bom_blank_rows_normalization_and_raw_provenance_remain(self):
        raw=b'\xef\xbb\xbf\n{"text":"  Fictional\\r\\nrecord  ","group":"demo"}\r\n\n'
        self.source.write_bytes(raw)
        result=m.import_records(self.store,self.source)
        self.assertEqual(result['source_sha256'],hashlib.sha256(raw).hexdigest())
        with m.connect(self.store) as con:
            self.assertEqual(con.execute('SELECT source_row FROM provenance').fetchone()[0],2)
            self.assertEqual(json.loads(con.execute('SELECT body FROM records').fetchone()[0]),{'text':'Fictional\nrecord'})
        self.assertEqual(self.source.read_bytes(),raw)

    def test_invalid_tail_and_record_limit_leave_store_unchanged(self):
        before=self.store.read_bytes()
        for raw in (self.raw+b'{fictional',json.dumps({'text':'x'*(64*1024+1),'group':'demo'}).encode()+b'\n'):
            self.source.write_bytes(raw)
            self.assertEqual(self.cli('import','--input',str(self.source))[0],2)
            self.assertEqual(self.store.read_bytes(),before)
        self.assertEqual(m.records(self.store),[])

    def test_growth_stops_at_limit_plus_one_before_store_access(self):
        original=os.read
        changed,consumed=[],[]
        def grow(fd,amount):
            block=original(fd,amount)
            consumed.append(len(block))
            if block and not changed:
                with self.source.open('ab') as handle:handle.write(b' '*200)
                changed.append(True)
            return block
        before=self.store.read_bytes()
        with mock.patch.object(m,'MAX_IMPORT',64),mock.patch.object(os,'read',side_effect=grow),mock.patch.object(m,'connect',side_effect=AssertionError('CHANGED_IMPORT_OPENED_STORE')):
            self.assertEqual(self.cli('import','--input',str(self.source))[0],2)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),65)
        self.assertEqual(self.store.read_bytes(),before)

    def test_same_size_input_mutation_is_not_imported(self):
        original=os.read
        changed=[]
        def mutate(fd,amount):
            block=original(fd,amount)
            if block and not changed:
                stamp=self.source.stat().st_mtime_ns
                self.source.write_bytes(self.raw.replace(b'record',b'RECORD'))
                os.utime(self.source,ns=(stamp,stamp+1_000_000))
                changed.append(True)
            return block
        before=self.store.read_bytes()
        with mock.patch.object(os,'read',side_effect=mutate):self.assertEqual(self.cli('import','--input',str(self.source))[0],2)
        self.assertEqual(self.store.read_bytes(),before)

    def test_early_eof_cannot_import_a_valid_truncated_prefix(self):
        self.source.write_bytes(self.raw+b'\n\n')
        before=self.store.read_bytes()
        with mock.patch.object(os,'read',side_effect=[self.raw,b'']):self.assertEqual(self.cli('import','--input',str(self.source))[0],2)
        self.assertEqual(self.store.read_bytes(),before)

    def test_initial_oversize_directory_and_missing_inputs_do_not_read_data(self):
        with mock.patch.object(m,'MAX_IMPORT',2),mock.patch.object(os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):
            self.assertEqual(self.cli('import','--input',str(self.source))[0],2)
        with mock.patch.object(os,'read',side_effect=AssertionError('NONFILE_READ')):
            for path in (self.base,self.base/'missing.jsonl'):
                self.assertEqual(self.cli('import','--input',str(path))[0],2)
        self.assertEqual(m.records(self.store),[])

    def test_hardlinked_import_is_supported_without_source_changes(self):
        alias=self.base/'alias.jsonl'
        self.hardlink(alias,self.source)
        self.assertEqual(m.import_records(self.store,alias)['added'],1)
        self.assertEqual(alias.read_bytes(),self.raw)
        self.assertEqual(self.source.read_bytes(),self.raw)

    def test_json_row_semantics_and_imported_approval_fields_remain(self):
        self.source.write_bytes(b'{"text":"Fictional","group":"demo","unused":NaN,"status":"approved","checks":{"privacy":true}}\n')
        m.import_records(self.store,self.source)
        self.assertEqual(m.records(self.store)[0]['status'],'pending')
        with m.connect(self.store) as con:self.assertEqual(con.execute('SELECT checks FROM records').fetchone()[0],'{}')

    def test_export_bytes_hash_fields_and_unicode_lf_remain(self):
        self.source.write_text(json.dumps({'text':'Fictional \u03bb record','group':'demo'})+'\n',encoding='utf-8')
        identifier=self.approved()
        result=m.export_records(self.store,self.output)
        expected=(m.canonical(dict(id=identifier,text='Fictional \u03bb record',split='train'))+'\n').encode('utf-8')
        self.assertEqual(self.output.read_bytes(),expected)
        self.assertEqual(result['sha256'],hashlib.sha256(expected).hexdigest())
        self.assertEqual(set(json.loads(expected)),{'id','text','split'})
        self.assertNotIn(b'FictionalReviewer',expected)

    def test_empty_export_creates_verified_new_empty_file(self):
        result=m.export_records(self.store,self.output)
        self.assertEqual((result['records'],self.output.read_bytes()),(0,b''))
        self.assertEqual(result['sha256'],hashlib.sha256(b'').hexdigest())

    def test_existing_export_is_never_replaced(self):
        self.approved()
        self.output.write_bytes(b'fictional retained')
        with self.assertRaises(FileExistsError):m.export_records(self.store,self.output)
        self.assertEqual(self.output.read_bytes(),b'fictional retained')

    def test_repository_and_traversal_outputs_fail_before_store_access(self):
        with mock.patch.object(m,'connect',side_effect=AssertionError('INVALID_OUTPUT_OPENED_STORE')):
            for path in (m.PACKAGE/'fictional-export.jsonl',self.base/'..'/self.base.name/'export.jsonl'):
                self.assertEqual(self.cli('export','--output',str(path))[0],2)
            self.assertEqual(self.cli('import','--input',str(self.base/'..'/self.base.name/'input.jsonl'))[0],2)
        self.assertFalse(self.output.exists())

    def test_short_writes_complete_exact_export(self):
        self.approved()
        original=os.write
        with mock.patch.object(os,'write',side_effect=lambda fd,data:original(fd,data[:3])):
            result=m.export_records(self.store,self.output)
        self.assertEqual(result['sha256'],hashlib.sha256(self.output.read_bytes()).hexdigest())

    def test_zero_and_partial_write_failures_retain_only_new_unconfirmed_files(self):
        self.approved()
        original=os.write
        calls=[]
        def partial(fd,data):
            if calls:raise OSError('FICTIONAL_PRIVATE_DETAIL')
            calls.append(True)
            return original(fd,data[:3])
        for index,effect in enumerate((lambda fd,data:0,partial)):
            path=self.base/('partial'+str(index)+'.jsonl')
            with mock.patch.object(os,'write',side_effect=effect):
                code,report=self.cli('export','--output',str(path))
            self.assertEqual((code,report),(2,dict(status='ERROR',code='REVIEW_OPERATION_FAILED')))
            self.assertEqual(path.stat().st_size,0 if index==0 else 3)
            path.rename(self.base/('retained'+str(index)+'.jsonl'))

    def test_late_flush_failure_retains_complete_looking_unconfirmed_export(self):
        self.approved()
        before=self.store.read_bytes()
        with mock.patch.object(os,'fsync',side_effect=OSError('FICTIONAL_FLUSH_DETAIL')):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertEqual(json.loads(self.output.read_bytes())['text'],'Fictional record')
        self.assertEqual(self.store.read_bytes(),before)
        self.output.rename(self.base/'retained-unconfirmed.jsonl')

    def test_readback_mismatch_prevents_success(self):
        self.approved()
        owner,method=(w,'read_bounded') if os.name=='nt' else (m,'_read_posix')
        with mock.patch.object(owner,method,return_value=b'different fictional bytes'):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertTrue(self.output.is_file())

    def test_export_limit_fails_before_creation(self):
        self.approved()
        with mock.patch.object(m,'MAX_EXPORT',1):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertFalse(self.output.exists())

    def test_import_library_interruption_propagates_and_releases_input(self):
        before=self.store.read_bytes()
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.import_records(self.store,self.source)
        self.assertEqual(self.store.read_bytes(),before)
        self.source.rename(self.base/'released-input.jsonl')

    def test_export_library_interruption_propagates_and_releases_output(self):
        self.approved()
        with mock.patch.object(os,'write',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.export_records(self.store,self.output)
        self.output.rename(self.base/'released-output.jsonl')

    def test_store_connection_is_closed_before_export_write(self):
        self.approved()
        original=m._write_export
        observed=[]
        def probe(path,data):
            con=m.sqlite3.connect(self.store,timeout=0)
            try:
                con.execute('BEGIN EXCLUSIVE')
                con.rollback()
                observed.append(True)
            finally:con.close()
            return original(path,data)
        with mock.patch.object(m,'_write_export',side_effect=probe):m.export_records(self.store,self.output)
        self.assertEqual(observed,[True])

    def test_cli_errors_omit_private_exception_values_and_paths(self):
        self.approved()
        with mock.patch.object(m,'_write_export',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            code,report=self.cli('export','--output',str(self.output))
        self.assertEqual((code,report),(2,dict(status='ERROR',code='REVIEW_OPERATION_FAILED')))
        self.assertNotIn(str(self.output),json.dumps(report))

    def test_successful_export_does_not_change_store_or_import_bytes(self):
        self.approved()
        source,store=self.source.read_bytes(),self.store.read_bytes()
        m.export_records(self.store,self.output)
        self.assertEqual(self.source.read_bytes(),source)
        self.assertEqual(self.store.read_bytes(),store)


@unittest.skipIf(os.name=='nt','POSIX filesystem fixture')
class PosixIO(Fixture):
    def test_fifo_import_is_refused_before_open(self):
        path=self.base/'fictional-fifo'
        os.mkfifo(path)
        with mock.patch.object(os,'open',side_effect=AssertionError('FIFO_OPENED')):
            self.assertEqual(self.cli('import','--input',str(path))[0],2)

    def test_socket_import_is_refused_before_open(self):
        path=self.base/'fictional-socket'
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(path))
            with mock.patch.object(os,'open',side_effect=AssertionError('SOCKET_OPENED')):
                self.assertEqual(self.cli('import','--input',str(path))[0],2)

    def test_source_links_and_export_symlink_are_refused(self):
        alias=self.base/'source-link.jsonl'
        alias.symlink_to(self.source)
        parent=self.base/'parent-link'
        parent.symlink_to(self.base,target_is_directory=True)
        for path in (alias,parent/self.source.name):
            self.assertEqual(self.cli('import','--input',str(path))[0],2)
        self.output.symlink_to(self.source)
        self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertEqual(self.source.read_bytes(),self.raw)

    def test_output_flags_mode_and_descriptor_noninheritance(self):
        self.approved()
        original_open,original_read=os.open,os.read
        flags=[]
        def opened(path,mode,*args,**kwargs):
            flags.append(mode)
            return original_open(path,mode,*args,**kwargs)
        def read(fd,amount):
            self.assertFalse(os.get_inheritable(fd))
            return original_read(fd,amount)
        with mock.patch.object(os,'open',side_effect=opened),mock.patch.object(os,'read',side_effect=read):m.export_records(self.store,self.output)
        self.assertTrue(flags[0]&os.O_EXCL)
        for name in ('O_NOFOLLOW','O_NONBLOCK'):
            if hasattr(os,name):self.assertTrue(all(value&getattr(os,name) for value in flags))
        self.assertEqual(self.output.stat().st_mode&0o777,0o600)

    def test_output_leaf_link_inserted_at_open_never_replaces_target(self):
        self.approved()
        original=os.open
        victim=self.base/'fictional-retained.txt'
        victim.write_bytes(b'fictional retained')
        def insert(path,flags,*args,**kwargs):
            if Path(path)==self.output:self.output.symlink_to(victim)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=insert):self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertEqual(victim.read_bytes(),b'fictional retained')


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class WindowsIO(Fixture):
    def test_invalid_spellings_stop_before_native_access_for_both_boundaries(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:
                self.assertEqual(self.cli('import','--input',value)[0],2)
                self.assertEqual(self.cli('export','--output',value)[0],2)

    def test_nonlocal_volume_is_refused_before_native_open(self):
        native=w.Native({'Rejected':m.ReviewError,'EntryFailure':m.ReviewError})
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(m.ReviewError):native.open(Path(self.base.anchor),True)

    def test_native_repository_alias_overlap_is_refused_before_creation(self):
        native=w.Native(w._core(m.ReviewError))
        with w.Chain(native,m.PACKAGE) as package:repository_name=package.items[-1][2]
        original=w.Native.open
        def alias(native,path,directory,expected=None):
            handle,identity,final=original(native,path,directory,expected)
            if path==self.base:final=repository_name
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=alias),mock.patch.object(os,'open',side_effect=AssertionError('REPOSITORY_OUTPUT_CREATED')):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertFalse(self.output.exists())

    def test_symlink_import_leaf_is_refused_before_data_read(self):
        alias=self.base/'source-link.jsonl'
        self.symlink(alias,self.source)
        with mock.patch.object(os,'read',side_effect=AssertionError('LINK_READ')):
            self.assertEqual(self.cli('import','--input',str(alias))[0],2)

    def test_symlink_import_ancestor_is_refused_before_data_read(self):
        alias=self.base/'parent-link'
        self.symlink(alias,self.base,True)
        with mock.patch.object(os,'read',side_effect=AssertionError('LINK_READ')):
            self.assertEqual(self.cli('import','--input',str(alias/self.source.name))[0],2)

    def test_symlink_export_leaf_never_replaces_target(self):
        self.symlink(self.output,self.source)
        self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertEqual(self.source.read_bytes(),self.raw)

    def test_junction_import_ancestor_is_refused_before_data_read(self):
        alias=self.base/'parent-junction'
        self.junction(alias,self.base)
        with mock.patch.object(os,'read',side_effect=AssertionError('JUNCTION_READ')):
            self.assertEqual(self.cli('import','--input',str(alias/self.source.name))[0],2)

    def test_junction_export_parent_is_refused_without_target_writes(self):
        target=self.base/'outside'
        target.mkdir()
        alias=self.base/'output-junction'
        self.junction(alias,target)
        self.assertEqual(self.cli('export','--output',str(alias/'export.jsonl'))[0],2)
        self.assertEqual(list(target.iterdir()),[])

    def test_existing_hardlinked_export_never_replaces_target(self):
        self.hardlink(self.output,self.source)
        self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertEqual(self.source.read_bytes(),self.raw)

    def test_export_hardlink_added_before_readback_requires_failure(self):
        self.approved()
        original=w.exclusive_write
        def link(path,data,error):
            result=original(path,data,error)
            self.hardlink(self.base/'unexpected-alias.jsonl',Path(path))
            return result
        with mock.patch.object(w,'exclusive_write',side_effect=link):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertTrue(self.output.exists())

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        folder=self.base/'fictional long input directory'
        folder.mkdir()
        source=folder/'input.jsonl'
        source.write_bytes(self.raw)
        buffer=ctypes.create_unicode_buffer(32768)
        size=method(str(source),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(source).casefold():self.skipTest('Optional short-name alias unavailable')
        self.assertEqual(self.cli('import','--input',buffer.value)[0],2)

    def test_cli_interruption_and_help_omit_private_values(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt):code,report=self.cli('import','--input',str(self.source))
        self.assertEqual((code,report),(130,dict(status='ERROR',code='REVIEW_OPERATION_INTERRUPTED')))
        output=io.StringIO()
        with redirect_stdout(output):self.assertEqual(m.main(['--unknown','FICTIONAL_ARGUMENT_DETAIL']),2)
        self.assertNotIn('FICTIONAL_ARGUMENT_DETAIL',output.getvalue())
        output=io.StringIO()
        with mock.patch.object(sys,'argv',['FICTIONAL_PROGRAM_DETAIL']),redirect_stdout(output),self.assertRaises(SystemExit):m.main(['--help'])
        self.assertIn('usage: review_store.py',output.getvalue())
        self.assertNotIn('FICTIONAL_PROGRAM_DETAIL',output.getvalue())

    def test_final_native_directory_guard_failure_prevents_success(self):
        self.approved()
        original_read,original_describe=w.read_bounded,w.Native.describe
        finished=[]
        def read(path,*args,**kwargs):
            data=original_read(path,*args,**kwargs)
            if Path(path)==self.output:finished.append(True)
            return data
        def changed(native,handle,directory):
            identity,name=original_describe(native,handle,directory)
            if directory and finished:identity=(identity[0],identity[1]+1,*identity[2:])
            return identity,name
        with mock.patch.object(w,'read_bounded',side_effect=read),mock.patch.object(w.Native,'describe',new=changed):
            self.assertEqual(self.cli('export','--output',str(self.output))[0],2)
        self.assertTrue(finished)
        self.assertEqual(json.loads(self.output.read_bytes())['text'],'Fictional record')
        self.output.rename(self.base/'retained-unconfirmed.jsonl')


if __name__=='__main__':unittest.main()
