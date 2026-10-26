"""Fictional requests and disposable input/failure fixtures only."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest import mock

MODULE=Path(__file__).resolve().parents[1]/'maintenance.py'
SPEC=importlib.util.spec_from_file_location('maintenance_input_fixture',MODULE)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-maintenance-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.root=self.base/'inputs'
        self.root.mkdir()
        self.path=self.root/'fictional.json'
        self.raw=b'{"fictional":true}'
        self.path.write_bytes(self.raw)

    def rejected(self,value):
        with self.assertRaises((OSError,ValueError,UnicodeError,TypeError,RecursionError)):
            m.load_request(value)

    def cli(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=m.main(list(args))
        self.assertEqual(stderr.getvalue(),'')
        return code,json.loads(stdout.getvalue())

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_MAINTENANCE_REQUIRE_LINKS')=='1':
            raise AssertionError('Required native '+name+' creation failed') from error
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


class PortableContracts(Fixture):
    def test_nested_bom_and_whitespace_json_preserve_input(self):
        raw=b'\xef\xbb\xbf{\r\n"nested":[1,true,null,{"label":"fictional"}]\r\n}'
        self.path.write_bytes(raw)
        self.assertEqual(m.load_request(self.path),{'nested':[1,True,None,{'label':'fictional'}]})
        self.assertEqual(self.path.read_bytes(),raw)

    def test_duplicate_object_keys_are_rejected(self):
        self.path.write_bytes(b'{"x":1,"x":2}')
        self.rejected(self.path)

    def test_json_loader_preserves_scalars_but_planner_refuses_them(self):
        for raw in (b'[]',b'null',b'true',b'1',b'"fictional"'):
            self.path.write_bytes(raw)
            self.assertEqual(m.load_request(self.path),json.loads(raw))
            self.assertEqual(self.cli('plan','--input',str(self.path)),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))

    def test_nonstandard_constants_rejected_but_exponent_behavior_preserved(self):
        for literal in ('NaN','Infinity','-Infinity'):
            self.path.write_text('{"x":'+literal+'}',encoding='utf-8')
            self.rejected(self.path)
        self.path.write_bytes(b'{"x":1e999}')
        self.assertTrue(math.isinf(m.load_request(self.path)['x']))

    def test_invalid_json_and_encoding_errors_omit_values_and_path(self):
        for raw in (b'{FICTIONAL_PRIVATE_DETAIL',b'\xffFICTIONAL_PRIVATE_DETAIL',b''):
            self.path.write_bytes(raw)
            self.rejected(self.path)
            for command in ('plan','readiness'):
                self.assertEqual(self.cli(command,'--input',str(self.path)),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))


    def test_default_limit_accepts_exact_boundary_and_rejects_one_extra_byte(self):
        size=m.INPUT_LIMIT
        raw=b'{"x":"'+b'a'*(size-8)+b'"}'
        self.assertEqual(len(raw),size)
        self.path.write_bytes(raw)
        self.assertEqual(len(m.load_request(self.path)['x']),size-8)
        with self.path.open('ab') as handle:handle.write(b' ')
        self.rejected(self.path)


    def test_early_eof_cannot_accept_truncated_but_valid_json(self):
        with mock.patch.object(os,'read',side_effect=[b'{}',b'']):self.rejected(self.path)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_growth_is_rejected_after_at_most_limit_plus_one_bytes(self):
        self.path.write_bytes(b'{"x":1}')
        original=os.read
        changed,requests,consumed=[],[],[]
        def grow(fd,amount):
            requests.append(amount)
            block=original(fd,amount)
            consumed.append(len(block))
            if block and not changed:
                with self.path.open('ab') as handle:handle.write(b' '*m.INPUT_LIMIT)
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=grow):self.rejected(self.path)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),m.INPUT_LIMIT+1)
        self.assertTrue(all(0<amount<=m.INPUT_LIMIT+1 for amount in requests))

    def test_same_size_mutation_cannot_return_either_object_as_verified(self):
        self.path.write_bytes(b'{"x":1}')
        original=os.read
        changed=[]
        def mutate(fd,amount):
            block=original(fd,amount)
            if block and not changed:
                stamp=self.path.stat().st_mtime_ns
                self.path.write_bytes(b'{"x":2}')
                os.utime(self.path,ns=(stamp,stamp+1_000_000))
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=mutate):self.rejected(self.path)

    def test_short_reads_complete_without_altering_json(self):
        original=os.read
        with mock.patch.object(os,'read',side_effect=lambda fd,amount:original(fd,min(amount,3))):
            self.assertEqual(m.load_request(self.path),{'fictional':True})

    def test_read_failure_closes_descriptors(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            self.rejected(self.path)
        self.path.rename(self.root/'released.json')

    def test_invalid_types_nul_and_parent_traversal_are_refused(self):
        for value in (None,b'fictional.json',[],{},'', '\x00FICTIONAL_PRIVATE_DETAIL',self.root/'..'/'inputs'/self.path.name):
            self.rejected(value)

    def test_directory_is_refused_before_data_read(self):
        with mock.patch.object(os,'read',side_effect=AssertionError('DIRECTORY_READ')):self.rejected(self.root)

    def test_missing_path_does_not_create_any_input(self):
        missing=self.root/'missing-fictional.json'
        self.rejected(missing)
        self.assertFalse(missing.exists())

    def test_hardlinked_source_remains_supported_and_unchanged(self):
        alias=self.root/'source-alias.json'
        self.hardlink(alias,self.path)
        self.assertEqual(m.load_request(alias),{'fictional':True})
        self.assertEqual(alias.read_bytes(),self.raw)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_filename_extension_does_not_import_or_execute_input(self):
        source=self.root/'fictional.py'
        source.write_bytes(b'{"fictional":true}')
        self.assertEqual(m.load_request(source),{'fictional':True})
        source.write_text("raise RuntimeError('FICTIONAL_INPUT_CODE')",encoding='utf-8')
        self.rejected(source)

    def test_library_is_silent_and_writes_no_input_tree_files(self):
        before={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            result=m.load_request(self.path)
            self.rejected(self.root/'missing.json')
        after={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before,after)
        self.assertEqual((stdout.getvalue(),stderr.getvalue()),('',''))

    def request(self,**changes):
        value=dict(action='restart',state='running',players=0,observation_age_seconds=30,
                   maximum_age_seconds=300,cooldown_remaining_seconds=0,
                   previous_attempt='completed',target_verified=True,backup_verified=True)
        value.update(changes)
        self.path.write_text(json.dumps(value),encoding='utf-8')
        return value

    def test_cli_plan_is_only_a_checklist_and_preserves_input_tree(self):
        value=self.request()
        before=self.path.read_bytes()
        with mock.patch.object(subprocess,'run',side_effect=AssertionError('PROCESS_EXECUTED')),mock.patch.object(os,'system',side_effect=AssertionError('SHELL_EXECUTED')):
            code,result=self.cli('plan','--input',str(self.path))
        self.assertEqual(code,0)
        self.assertEqual(result,m.maintenance_plan(value))
        self.assertFalse(result['execution_performed'])
        self.assertEqual(result['status'],'PLAN_READY')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.root.iterdir()),[self.path])

    def test_cli_blocked_plans_are_successful_observations_without_execution(self):
        for changes,status in ((dict(players=1),'PLAYERS_PRESENT'),(dict(previous_attempt='incomplete'),'REVIEW_PREVIOUS_ATTEMPT'),(dict(backup_verified=False),'VERIFIED_BACKUP_REQUIRED')):
            self.request(**changes)
            code,result=self.cli('plan','--input',str(self.path))
            self.assertEqual((code,result['status'],result['execution_performed']),(0,status,False))

    def test_cli_readiness_requires_all_declared_booleans(self):
        value=dict(target_verified=True,new_instance=True,fresh_log_markers=True,probe_succeeded=True)
        for expected in ('OBSERVATIONS_COMPLETE','NOT_ESTABLISHED'):
            self.path.write_text(json.dumps(value),encoding='utf-8')
            code,result=self.cli('readiness','--input',str(self.path))
            self.assertEqual((code,result['status'],result['execution_performed']),(0,expected,False))
            value['probe_succeeded']=False

    def test_calendar_does_not_open_inputs_or_create_a_schedule(self):
        with mock.patch.object(m,'load_request',side_effect=AssertionError('CALENDAR_READ')),mock.patch.object(subprocess,'run',side_effect=AssertionError('CALENDAR_SCHEDULED')):
            code,result=self.cli('calendar','--year','2026','--month','12','--weekday','3','--offset-days','14')
        self.assertEqual(code,0)
        self.assertEqual(result,m.schedule_window(2026,12,3,14))
        self.assertFalse(result['execution_performed'])

    def test_valid_relative_input_path_remains_supported(self):
        relative=os.path.relpath(self.path,Path.cwd())
        if '..' in Path(relative).parts:
            previous=Path.cwd()
            try:
                os.chdir(self.root)
                self.assertEqual(m.load_request(self.path.name),{'fictional':True})
            finally:os.chdir(previous)
        else:self.assertEqual(m.load_request(relative),{'fictional':True})

    def test_nested_duplicate_keys_and_json_depth_fail_with_fixed_cli_error(self):
        for raw in (b'{"x":{"y":1,"y":2}}',b'['*2000+b'0'+b']'*2000):
            self.path.write_bytes(raw)
            self.assertEqual(self.cli('plan','--input',str(self.path)),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))

    def test_oversize_input_refused_before_descriptor_open(self):
        self.path.write_bytes(b' '* (m.INPUT_LIMIT+1))
        with mock.patch.object(os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):self.rejected(self.path)

    def test_unknown_fields_and_boolean_integers_keep_fixed_cli_failure(self):
        for changes in (dict(players=True),dict(extra=True),dict(maximum_age_seconds=0)):
            self.request(**changes)
            self.assertEqual(self.cli('plan','--input',str(self.path)),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))

    def test_native_read_error_is_not_echoed_by_cli(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            self.assertEqual(self.cli('plan','--input',str(self.path)),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))
        self.path.rename(self.root/'released.json')

    def test_cli_invalid_arguments_do_not_echo_supplied_values(self):
        for args in (('FICTIONAL_PRIVATE_DETAIL',),('plan','--input'),('calendar','--year','FICTIONAL_PRIVATE_DETAIL')):
            self.assertEqual(self.cli(*args),(2,dict(status='ERROR',code='PLAN_INPUT_INVALID',execution_performed=False)))


@unittest.skipIf(os.name=='nt','POSIX filesystem fixture')
class PosixInputs(Fixture):
    def test_parent_identity_change_after_read_is_refused(self):
        original=m._safe_posix
        observed=[]
        def changed(path):
            rows=original(path)
            observed.append(True)
            if len(observed)>1:
                first,*rest=rows
                return ((first[0],first[1],first[2]+1,first[3]),*rest)
            return rows
        with mock.patch.object(m,'_safe_posix',side_effect=changed):self.rejected(self.path)

    def test_fifo_is_refused_before_open(self):
        path=self.root/'fictional-fifo'
        os.mkfifo(path)
        with mock.patch.object(os,'open',side_effect=AssertionError('FIFO_OPENED')):self.rejected(path)

    def test_symlink_leaf_and_ancestor_are_refused_before_open(self):
        leaf=self.root/'source-link.json'
        leaf.symlink_to(self.path)
        parent=self.base/'parent-link'
        parent.symlink_to(self.root,target_is_directory=True)
        with mock.patch.object(os,'open',side_effect=AssertionError('LINK_OPENED')):
            self.rejected(leaf)
            self.rejected(parent/self.path.name)

    def test_leaf_replacement_link_is_not_followed(self):
        original=os.open
        outside=self.base/'outside.json'
        outside.write_bytes(b'{"outside":"fictional"}')
        observed=[]
        def replace(path,flags,*args,**kwargs):
            observed.append(flags)
            self.path.rename(self.base/'retained.json')
            self.path.symlink_to(outside)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=replace):self.rejected(self.path)
        self.assertTrue(observed)
        if hasattr(os,'O_NOFOLLOW'):self.assertTrue(observed[0]&os.O_NOFOLLOW)
        self.assertEqual(outside.read_bytes(),b'{"outside":"fictional"}')

    def test_available_open_flags_and_noninheritance_are_applied(self):
        opened,reads=[],[]
        original_open,original_read=os.open,os.read
        def capture(path,flags,*args,**kwargs):
            opened.append(flags)
            return original_open(path,flags,*args,**kwargs)
        def read(fd,amount):
            reads.append(fd)
            self.assertFalse(os.get_inheritable(fd))
            return original_read(fd,amount)
        with mock.patch.object(os,'open',side_effect=capture),mock.patch.object(os,'read',side_effect=read):
            self.assertEqual(m.load_request(self.path),{'fictional':True})
        self.assertTrue(reads)
        for name in ('O_NOFOLLOW','O_NONBLOCK'):
            if hasattr(os,name):self.assertTrue(opened[0]&getattr(os,name))

    def test_socket_path_is_refused_before_open(self):
        path=self.root/'fictional-socket'
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(path))
            with mock.patch.object(os,'open',side_effect=AssertionError('SOCKET_OPENED')):self.rejected(path)

    def test_posix_needs_no_windows_backend_file(self):
        library=self.base/'library'
        library.mkdir()
        copied=library/'maintenance.py'
        copied.write_bytes(MODULE.read_bytes())
        spec=importlib.util.spec_from_file_location('isolated_posix_maintenance',copied)
        isolated=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated)
        self.assertEqual(isolated.load_request(self.path),{'fictional':True})
        self.assertIsNone(isolated._WINDOWS_BACKEND)


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class WindowsInputs(Fixture):
    def test_cli_interruption_and_help_use_fixed_public_messages(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt):
            self.assertEqual(self.cli('plan','--input',str(self.path)),(130,dict(status='ERROR',code='PLAN_INTERRUPTED',execution_performed=False)))
        self.path.rename(self.root/'released.json')
        stdout,stderr=io.StringIO(),io.StringIO()
        with mock.patch.object(m.sys,'argv',['FICTIONAL_PRIVATE_DETAIL']),redirect_stdout(stdout),redirect_stderr(stderr),self.assertRaises(SystemExit) as captured:
            m.main(['--help'])
        self.assertEqual(captured.exception.code,0)
        self.assertIn('maintenance.py',stdout.getvalue())
        self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',stdout.getvalue()+stderr.getvalue())

    def test_invalid_spellings_stop_before_native_access(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:self.rejected(value)

    def test_remote_drive_is_refused_before_native_open(self):
        native=w.Native({'Rejected':m.PlanError,'EntryFailure':m.PlanError})
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(m.PlanError):native.open(Path(self.path.anchor),True)

    def test_binary_noninheritable_descriptor_is_retained_and_closed(self):
        with w.regular(self.path,m.PlanError) as fd:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd,100),self.raw)
            with self.assertRaises(OSError):self.path.rename(self.root/'blocked.json')
        self.path.rename(self.root/'released.json')

    def test_native_crt_identity_mismatch_fails_before_data_read(self):
        original=w.Native.describe
        files=[]
        def mismatch(native,handle,directory):
            identity,name=original(native,handle,directory)
            if not directory:
                files.append(True)
                if len(files)==2:identity=(identity[0],identity[1]+1,*identity[2:])
            return identity,name
        with mock.patch.object(w.Native,'describe',new=mismatch),mock.patch.object(os,'read',side_effect=AssertionError('MISMATCH_READ')):
            self.rejected(self.path)
        self.path.rename(self.root/'released.json')

    def test_symlink_file_is_refused_before_data_read(self):
        alias=self.root/'source-link.json'
        self.symlink(alias,self.path)
        with mock.patch.object(os,'read',side_effect=AssertionError('LINK_READ')):self.rejected(alias)

    def test_symlink_ancestor_is_refused_before_data_read(self):
        alias=self.base/'parent-link'
        self.symlink(alias,self.root,True)
        with mock.patch.object(os,'read',side_effect=AssertionError('LINK_READ')):self.rejected(alias/self.path.name)

    def test_junction_ancestor_is_refused_before_data_read(self):
        alias=self.base/'parent-junction'
        self.junction(alias,self.root)
        with mock.patch.object(os,'read',side_effect=AssertionError('JUNCTION_READ')):self.rejected(alias/self.path.name)

    def test_named_stream_argument_is_refused_before_native_access(self):
        stream=Path(str(self.path)+':fictional')
        stream.write_bytes(b'{"stream":"fictional"}')
        with mock.patch.object(w,'Native',side_effect=AssertionError('STREAM_OPENED')):self.rejected(stream)
        self.assertEqual(stream.read_bytes(),b'{"stream":"fictional"}')

    def test_unnamed_data_load_does_not_read_or_change_named_stream(self):
        stream=Path(str(self.path)+':fictional')
        stream.write_bytes(b'not JSON fictional stream')
        self.assertEqual(m.load_request(self.path),{'fictional':True})
        self.assertEqual(stream.read_bytes(),b'not JSON fictional stream')

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        folder=self.base/'fictional long inputs'
        folder.mkdir()
        source=folder/'fictional.json'
        source.write_bytes(self.raw)
        buffer=ctypes.create_unicode_buffer(32768)
        size=method(str(source),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(source).casefold():self.skipTest('Optional short-name alias unavailable')
        self.rejected(buffer.value)

    def test_interruption_propagates_and_closes_native_input_handles(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.load_request(self.path)
        self.path.rename(self.root/'released.json')


if __name__=='__main__':unittest.main()
