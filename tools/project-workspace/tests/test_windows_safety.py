"""Invented opaque inputs and disposable workspace/failure fixtures only."""
from contextlib import contextmanager, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('workspace_safety_fixture', Path(__file__).resolve().parents[1]/'workspace.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w = m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('OUTLANDS_TEST_TEMP', tempfile.gettempdir())).resolve()
        self.temporary = tempfile.TemporaryDirectory(prefix='fictional-workspace-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base/'parent'
        self.root.mkdir()
        self.source = self.base/'fictional-input.bin'
        self.payload = b'Invented opaque input\r\n\x00\xff\n'
        self.source.write_bytes(self.payload)
        self.destination = self.root/'demo'

    def cli(self, *extra):
        output = io.StringIO()
        with redirect_stdout(output):
            status = m.main(['--root',str(self.root),'--name','demo',*extra])
        return status,json.loads(output.getvalue())

    def feature_failure(self, error, feature):
        if os.environ.get('OUTLANDS_WORKSPACE_REQUIRE_LINKS')=='1':
            raise AssertionError('Required native '+feature+' creation failed') from error
        self.skipTest('Native '+feature+' creation unavailable')

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target,target_is_directory=directory)
        except OSError as error:
            self.feature_failure(error,'symlink')

    def hardlink(self, path, target):
        try:
            os.link(target,path)
        except OSError as error:
            self.feature_failure(error,'hardlink')

    def junction(self, path, target):
        result = subprocess.run(['cmd','/d','/c','mklink','/J',str(path),str(target)],capture_output=True,timeout=10)
        if result.returncode:
            self.feature_failure(RuntimeError('Fictional junction creation failed'),'junction')
        self.assertTrue(path.is_junction())
        self.addCleanup(lambda: os.rmdir(path) if path.is_junction() else None)


class PortableContract(Fixture):
    def test_plan_without_source_creates_nothing(self):
        result = m.create(self.root,'demo')
        self.assertEqual(result,dict(status='PLAN_ONLY',folders=list(m.FOLDERS),source_selected=False))
        self.assertEqual(list(self.root.iterdir()),[])

    def test_selected_source_plan_reads_without_creating_outputs(self):
        result = m.create(self.root,'demo',self.source)
        self.assertEqual(result['status'],'PLAN_ONLY')
        self.assertTrue(result['source_selected'])
        self.assertEqual(list(self.root.iterdir()),[])
        self.assertEqual(self.source.read_bytes(),self.payload)

    def test_empty_and_binary_inputs_are_copied_exactly_with_neutral_records(self):
        for index,payload in enumerate((b'',self.payload,b'{invalid fictional JSON')):
            self.source.write_bytes(payload)
            m.create(self.root,'demo'+str(index),self.source,True)
            destination = self.root/('demo'+str(index))
            for folder in ('original','working'):
                self.assertEqual((destination/folder/'intake.bin').read_bytes(),payload)
            expected = dict(sha256=hashlib.sha256(payload).hexdigest(),size=len(payload))
            self.assertEqual(json.loads((destination/'original/SOURCE.json').read_text()),expected)
            records = (destination/'CONTROL.md').read_text()+(destination/'original/SOURCE.json').read_text()
            self.assertNotIn(str(self.source),records)
            self.assertNotIn(self.source.name,records)
            self.assertEqual((destination/'.gitignore').read_text(),'*\n')
            self.assertEqual(self.source.read_bytes(),payload)

    def test_existing_destination_file_or_directory_is_preserved(self):
        for name,directory in (('existing-file',False),('existing-dir',True)):
            target = self.root/name
            if directory:
                target.mkdir()
                marker = target/'keep.txt'
            else:
                marker = target
            marker.write_bytes(b'fictional retained')
            for commit in (False,True):
                with self.assertRaises((m.WorkspaceError,OSError)):
                    m.create(self.root,name,self.source,commit)
            self.assertEqual(marker.read_bytes(),b'fictional retained')

    def test_missing_or_directory_source_fails_before_creation(self):
        for source in (self.base/'missing',self.root):
            with self.assertRaises((m.WorkspaceError,OSError)):
                m.create(self.root,'demo',source,True)
            self.assertEqual(list(self.root.iterdir()),[])

    def test_names_and_late_existing_destination_are_refused(self):
        for name in ('','CON','con','nul','a/b','../outside','name.with.dot','Upper'):
            with self.assertRaises(m.WorkspaceError):
                m.create(self.root,name,commit=True)
        self.assertEqual(m.create(self.root,'demo')['status'],'PLAN_ONLY')
        self.destination.mkdir()
        (self.destination/'keep.txt').write_bytes(b'retained')
        with self.assertRaises((m.WorkspaceError,OSError)):
            m.create(self.root,'demo',commit=True)
        self.assertEqual((self.destination/'keep.txt').read_bytes(),b'retained')

    def test_console_errors_omit_private_exception_values(self):
        with mock.patch.object(m,'create',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            status,result = self.cli('--create')
        self.assertEqual(status,2)
        self.assertEqual(result,dict(status='ERROR',code='WORKSPACE_INPUT_OR_OUTPUT_ERROR'))
        self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',json.dumps(result))

    @unittest.skipIf(os.name=='nt','Non-Windows native API rejection')
    def test_linux_cannot_initialize_native_api(self):
        with self.assertRaises(m.WorkspaceError):
            w.Native({'Rejected':m.WorkspaceError,'EntryFailure':m.WorkspaceError})

    @unittest.skipIf(os.name=='nt','POSIX link fixture')
    def test_posix_links_are_refused_before_copy(self):
        link = self.base/'source-link'
        link.symlink_to(self.source)
        with self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',link,True)
        root_link = self.base/'parent-link'
        root_link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(m.WorkspaceError):
            m.create(root_link,'demo',commit=True)
        self.assertEqual(list(self.root.iterdir()),[])

    @unittest.skipIf(os.name=='nt','POSIX FIFO fixture')
    def test_posix_fifo_is_refused_before_open(self):
        path = self.base/'fifo'
        os.mkfifo(path)
        with mock.patch.object(Path,'open',side_effect=AssertionError('FIFO_OPENED')),self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',path,True)
        self.assertEqual(list(self.root.iterdir()),[])


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class NativeWindowsWorkspace(Fixture):
    def test_invalid_windows_spellings_stop_before_native_access(self):
        values = ['',r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                  '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                  r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800',b'not text',None]
        with mock.patch.object(w,'Native',side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:
                with self.subTest(value=repr(value)),self.assertRaises(m.WorkspaceError):
                    m.create(value,'demo',commit=True)

    def test_nonlocal_drive_is_refused_before_native_open(self):
        native = w.Native({'Rejected':m.WorkspaceError,'EntryFailure':m.WorkspaceError})
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(m.WorkspaceError):
                native.open(Path(self.root.anchor),True)

    def test_plan_never_calls_output_creation(self):
        with mock.patch.object(w,'fresh_directory',side_effect=AssertionError('PLAN_MKDIR')),mock.patch.object(w,'exclusive_write',side_effect=AssertionError('PLAN_WRITE')):
            self.assertEqual(m.create(self.root,'demo',self.source)['status'],'PLAN_ONLY')
        self.assertFalse(self.destination.exists())

    def test_plan_failure_closes_handles_without_creating_outputs(self):
        with mock.patch.object(m,'source_bytes',side_effect=OSError('FICTIONAL_READ_FAILURE')):
            self.assertEqual(self.cli('--source',str(self.source))[0],2)
        self.assertEqual(list(self.root.iterdir()),[])
        self.root.rename(self.base/'released-parent')

    def test_oversize_source_is_refused_before_descriptor_open(self):
        with mock.patch.object(m,'MAX_SOURCE',2),mock.patch.object(w.os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):
            with self.assertRaises(m.WorkspaceError):
                m.create(self.root,'demo',self.source,True)
        self.assertFalse(self.destination.exists())

    def test_growth_stops_at_limit_plus_one_before_creation(self):
        self.source.write_bytes(b'fictional')
        original = os.read
        requests,changed,consumed = [],[],[]
        def grow(fd,amount):
            requests.append(amount)
            block = original(fd,amount)
            consumed.append(len(block))
            if block and not changed:
                with self.source.open('ab') as handle:
                    handle.write(b'X'*100)
                changed.append(True)
            return block
        with mock.patch.object(m,'MAX_SOURCE',16),mock.patch.object(w.os,'read',side_effect=grow),self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',self.source,True)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),17)
        self.assertTrue(all(0<amount<=17 for amount in requests))
        self.assertFalse(self.destination.exists())

    def test_same_size_mutation_fails_before_creation(self):
        original = os.read
        changed = []
        def mutate(fd,amount):
            block = original(fd,amount)
            if block and not changed:
                stamp = self.source.stat().st_mtime_ns
                self.source.write_bytes(b'X'*len(self.payload))
                os.utime(self.source,ns=(stamp,stamp+1_000_000))
                changed.append(True)
            return block
        with mock.patch.object(w.os,'read',side_effect=mutate),self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',self.source,True)
        self.assertFalse(self.destination.exists())

    def test_replacement_between_lstat_and_open_is_refused(self):
        original = w.read_bounded
        def replace(value,*args,**kwargs):
            self.source.rename(self.base/'retained-original.bin')
            self.source.write_bytes(self.payload)
            return original(value,*args,**kwargs)
        with mock.patch.object(w,'read_bounded',side_effect=replace),self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',self.source,True)
        self.assertFalse(self.destination.exists())
        self.assertEqual((self.base/'retained-original.bin').read_bytes(),self.payload)

    def test_input_descriptor_is_binary_noninheritable_and_held(self):
        with w.regular(self.source,m.WorkspaceError) as fd:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd,100),self.payload)
            with self.assertRaises(OSError):
                self.source.rename(self.base/'blocked.bin')
        self.source.rename(self.base/'closed.bin')

    def test_root_rename_is_blocked_or_detected_even_during_plan(self):
        original = m.source_bytes
        renamed = []
        def probe(value):
            try:
                self.root.rename(self.base/'blocked-parent')
            except OSError:
                pass
            else:
                renamed.append(True)
            return original(value)
        with mock.patch.object(m,'source_bytes',side_effect=probe):
            try:
                result = m.create(self.root,'demo',self.source)
            except m.WorkspaceError:
                self.assertTrue(renamed)
            else:
                self.assertFalse(renamed,'Parent rename was neither blocked nor detected')
                self.assertEqual(result['status'],'PLAN_ONLY')
        (self.base/'blocked-parent' if renamed else self.root).rename(self.base/'closed-parent')

    def test_hardlinked_source_is_read_without_rewriting_either_name(self):
        alias = self.base/'source-alias.bin'
        self.hardlink(alias,self.source)
        m.create(self.root,'demo',alias,True)
        self.assertEqual(alias.read_bytes(),self.payload)
        self.assertEqual(self.source.read_bytes(),self.payload)
        self.assertEqual((self.destination/'original/intake.bin').read_bytes(),self.payload)

    def test_symlink_source_is_refused_without_copying_target(self):
        alias = self.base/'source-link'
        self.symlink(alias,self.source)
        with self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',alias,True)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.source.read_bytes(),self.payload)

    def test_symlink_root_and_destination_are_refused(self):
        alias = self.base/'parent-link'
        self.symlink(alias,self.root,True)
        with self.assertRaises(m.WorkspaceError):
            m.create(alias,'demo',commit=True)
        outside = self.base/'outside'
        outside.mkdir()
        self.symlink(self.destination,outside,True)
        with self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',commit=True)
        self.assertEqual(list(outside.iterdir()),[])

    def test_junction_root_and_source_parent_are_refused(self):
        alias = self.base/'parent-junction'
        self.junction(alias,self.root)
        with self.assertRaises(m.WorkspaceError):
            m.create(alias,'demo',commit=True)
        incoming = self.base/'incoming'
        incoming.mkdir()
        (incoming/'file.bin').write_bytes(self.payload)
        source_alias = self.base/'source-junction'
        self.junction(source_alias,incoming)
        with self.assertRaises(m.WorkspaceError):
            m.create(self.root,'demo',source_alias/'file.bin',True)
        self.assertFalse(self.destination.exists())

    def test_junction_inserted_before_child_creation_is_not_followed(self):
        outside = self.base/'outside'
        outside.mkdir()
        original = w.fresh_directory
        @contextmanager
        def insert(value,error):
            if Path(value).name=='working':
                self.junction(Path(value),outside)
            with original(value,error) as result:
                yield result
        with mock.patch.object(w,'fresh_directory',side_effect=insert):
            self.assertEqual(self.cli('--create')[0],2)
        self.assertEqual(list(outside.iterdir()),[])

    def test_existing_metadata_insertions_are_not_replaced(self):
        original = w.exclusive_write
        for index,filename in enumerate(('.gitignore','SOURCE.json','CONTROL.md')):
            def insert(value,data,error):
                if Path(value).name==filename:
                    Path(value).write_bytes(b'fictional retained')
                return original(value,data,error)
            name = 'case'+str(index)
            with mock.patch.object(w,'exclusive_write',side_effect=insert),self.assertRaises(OSError):
                m.create(self.root,name,self.source,True)
            matches = list((self.root/name).rglob(filename))
            self.assertEqual(len(matches),1)
            self.assertEqual(matches[0].read_bytes(),b'fictional retained')

    def test_hardlinked_output_insertions_preserve_external_bytes(self):
        victim = self.base/'fictional-retained.bin'
        victim.write_bytes(b'fictional retained')
        original = w.exclusive_write
        def insert(value,data,error):
            if Path(value).name=='.gitignore':
                self.hardlink(Path(value),victim)
            return original(value,data,error)
        with mock.patch.object(w,'exclusive_write',side_effect=insert):
            self.assertEqual(self.cli('--create')[0],2)
        self.assertEqual(victim.read_bytes(),b'fictional retained')

    def test_symlink_output_insertions_preserve_external_bytes(self):
        victim = self.base/'fictional-retained.txt'
        victim.write_bytes(b'fictional retained')
        original = w.exclusive_write
        def insert(value,data,error):
            if Path(value).name=='CONTROL.md':
                self.symlink(Path(value),victim)
            return original(value,data,error)
        with mock.patch.object(w,'exclusive_write',side_effect=insert):
            self.assertEqual(self.cli('--create')[0],2)
        self.assertEqual(victim.read_bytes(),b'fictional retained')

    def test_readback_refuses_new_output_hardlink(self):
        original = w.read_bounded
        linked = []
        def insert(value,*args,**kwargs):
            if Path(value).name=='intake.bin' and not linked:
                self.hardlink(self.base/'unexpected-alias.bin',Path(value))
                linked.append(True)
            return original(value,*args,**kwargs)
        with mock.patch.object(w,'read_bounded',side_effect=insert):
            status,result = self.cli('--source',str(self.source),'--create')
        self.assertEqual(status,2)
        self.assertEqual(result['status'],'ERROR')
        self.assertTrue(self.destination.exists())

    def test_existing_child_directory_is_not_reused(self):
        original = w.fresh_directory
        @contextmanager
        def insert(value,error):
            if Path(value).name=='working':
                Path(value).mkdir()
                (Path(value)/'keep.txt').write_bytes(b'fictional retained')
            with original(value,error) as result:
                yield result
        with mock.patch.object(w,'fresh_directory',side_effect=insert):
            self.assertEqual(self.cli('--create')[0],2)
        self.assertEqual((self.destination/'working/keep.txt').read_bytes(),b'fictional retained')

    def test_short_writes_preserve_copies_and_existing_text_format(self):
        original = os.write
        with mock.patch.object(w.os,'write',side_effect=lambda fd,data:original(fd,data[:3])):
            self.assertEqual(self.cli('--source',str(self.source),'--create')[0],0)
        self.assertEqual((self.destination/'working/intake.bin').read_bytes(),self.payload)
        self.assertEqual((self.destination/'.gitignore').read_bytes(),b'*\r\n')
        self.assertEqual((self.destination/'CONTROL.md').read_bytes(),m.CONTROL_TEXT.replace('\n','\r\n').encode('utf-8'))

    def test_zero_write_retains_partial_and_closes_directory_handles(self):
        with mock.patch.object(w.os,'write',return_value=0):
            status,result = self.cli('--create')
        self.assertEqual((status,result['status']),(2,'ERROR'))
        self.assertEqual((self.destination/'.gitignore').read_bytes(),b'')
        self.destination.rename(self.root/'retained-partial')

    def test_late_flush_failure_retains_complete_looking_unconfirmed_tree(self):
        original = os.fsync
        calls = []
        def fail_late(fd):
            calls.append(fd)
            if len(calls)==5:
                raise OSError('FICTIONAL_PRIVATE_DETAIL')
            return original(fd)
        with mock.patch.object(w.os,'fsync',side_effect=fail_late):
            status,result = self.cli('--source',str(self.source),'--create')
        self.assertEqual((status,result['status']),(2,'ERROR'))
        self.assertEqual(len(calls),5)
        self.assertTrue((self.destination/'CONTROL.md').read_text().endswith('Pending.\n'))
        self.assertEqual((self.destination/'working/intake.bin').read_bytes(),self.payload)
        self.assertEqual(self.source.read_bytes(),self.payload)

    def test_readback_mismatch_prevents_success(self):
        original = w.read_bounded
        def mismatch(value,*args,**kwargs):
            data = original(value,*args,**kwargs)
            return b'different fictional bytes' if Path(value).name=='intake.bin' else data
        with mock.patch.object(w,'read_bounded',side_effect=mismatch):
            self.assertEqual(self.cli('--source',str(self.source),'--create')[0],2)
        self.assertEqual(self.source.read_bytes(),self.payload)

    def test_directory_guard_failure_after_all_files_prevents_success(self):
        original_read = w.read_bounded
        original_describe = w.Native.describe
        finished = []
        def read(value,*args,**kwargs):
            data = original_read(value,*args,**kwargs)
            if Path(value).name=='CONTROL.md':
                finished.append(True)
            return data
        def describe(native,handle,directory):
            identity,name = original_describe(native,handle,directory)
            if directory and finished:
                identity = (identity[0],identity[1]+1,*identity[2:])
            return identity,name
        with mock.patch.object(w,'read_bounded',side_effect=read),mock.patch.object(w.Native,'describe',new=describe):
            self.assertEqual(self.cli('--source',str(self.source),'--create')[0],2)
        self.assertTrue(finished)
        self.assertEqual((self.destination/'working/intake.bin').read_bytes(),self.payload)
        self.destination.rename(self.root/'retained-unconfirmed')

    def test_interruption_is_generic_and_closes_created_handles(self):
        with mock.patch.object(w.os,'write',side_effect=KeyboardInterrupt):
            status,result = self.cli('--create')
        self.assertEqual((status,result),(130,dict(status='ERROR',code='WORKSPACE_INTERRUPTED')))
        self.destination.rename(self.root/'retained-interrupted')

    def test_native_failure_after_mkdir_retains_only_new_partial(self):
        original = w.Native.open
        def fail(native,path,directory,expected=None):
            if path==self.destination:
                raise m.WorkspaceError('FICTIONAL_NATIVE_FAILURE')
            return original(native,path,directory,expected)
        with mock.patch.object(w.Native,'open',new=fail):
            self.assertEqual(self.cli('--create')[0],2)
        self.assertTrue(self.destination.is_dir())
        self.assertEqual(list(self.destination.iterdir()),[])
        self.destination.rename(self.root/'retained-new')

    def test_named_input_stream_is_not_an_all_stream_backup(self):
        stream = Path(str(self.source)+':fictional')
        stream.write_bytes(b'fictional omitted stream')
        m.create(self.root,'demo',self.source,True)
        self.assertEqual((self.destination/'original/intake.bin').read_bytes(),self.payload)
        self.assertFalse(Path(str(self.destination/'original/intake.bin')+':fictional').exists())
        self.assertEqual(stream.read_bytes(),b'fictional omitted stream')

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method = ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype = [wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        target = self.base/'fictional long parent'
        target.mkdir()
        buffer = ctypes.create_unicode_buffer(32768)
        size = method(str(target),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(target).casefold():
            self.skipTest('Optional short-name alias unavailable')
        with self.assertRaises(m.WorkspaceError):
            m.create(buffer.value,'demo',commit=True)

    def test_static_help_and_argument_errors_omit_private_values(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(m.main(['--unknown','FICTIONAL_ARGUMENT_DETAIL']),2)
        self.assertNotIn('FICTIONAL_ARGUMENT_DETAIL',output.getvalue())
        output = io.StringIO()
        with mock.patch.object(sys,'argv',['FICTIONAL_PROGRAM_DETAIL']),redirect_stdout(output),self.assertRaises(SystemExit):
            m.main(['--help'])
        self.assertIn('usage: workspace.py',output.getvalue())
        self.assertNotIn('FICTIONAL_PROGRAM_DETAIL',output.getvalue())


if __name__=='__main__':
    unittest.main()
