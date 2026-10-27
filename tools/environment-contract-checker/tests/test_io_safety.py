"""Invented control JSON, metadata targets and disposable report failures only."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest import mock

MODULE=Path(__file__).resolve().parents[1]/'environment_check.py'
SPEC=importlib.util.spec_from_file_location('environment_io_fixture',MODULE)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-environment-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.controls=self.base/'controls';self.controls.mkdir()
        self.root=self.base/'targets';self.root.mkdir()
        self.programs=self.base/'programs';self.programs.mkdir()
        self.target=self.root/'fictional.txt';self.target.write_bytes(b'FICTIONAL_TARGET_BODY')
        self.program=self.programs/('fictional-tool.cmd' if os.name=='nt' else 'fictional-tool')
        self.program.write_bytes(b'FICTIONAL_PROGRAM_BODY')
        if os.name!='nt':self.program.chmod(0o700)
        self.contract=dict(schema_version=1,requirements=[dict(id='document',kind='file',path=self.target.name),dict(id='tool',kind='program',name='fictional-tool')])
        self.path=self.controls/'contract.json'
        self.raw=json.dumps(self.contract).encode();self.path.write_bytes(self.raw)
        self.output=self.base/'report.json'
        self.result=m.check_contract(self.contract,root=self.root,program_dirs=[self.programs])

    def reject(self,call,*args,**kwargs):
        with self.assertRaises((m.ContractError,OSError,ValueError,TypeError,RecursionError)):call(*args,**kwargs)

    def report(self):m.write_report(self.output,self.result,[self.root,self.programs])

    def cli(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):code=m.main(list(args))
        self.assertEqual(stderr.getvalue(),'')
        result=json.loads(stdout.getvalue())
        self.assertFalse(result['target_contents_read']);self.assertFalse(result['programs_executed'])
        self.assertNotIn(str(self.base),stdout.getvalue())
        self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',stdout.getvalue())
        return code,result

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_ENVIRONMENT_REQUIRE_LINKS')=='1':raise AssertionError('Required native '+name+' creation failed') from error
        self.skipTest('Native '+name+' creation unavailable')

    def symlink(self,path,target,directory=False):
        try:path.symlink_to(target,target_is_directory=directory)
        except OSError as error:self.feature_failure(error,'symlink')

    def hardlink(self,path,target):
        try:os.link(target,path)
        except OSError as error:self.feature_failure(error,'hardlink')

    def junction(self,path,target):
        result=subprocess.run(['cmd','/d','/c','mklink','/J',str(path),str(target)],capture_output=True,timeout=10)
        if result.returncode:self.feature_failure(RuntimeError('Fictional junction failed'),'junction')
        self.assertTrue(path.is_junction())
        self.addCleanup(lambda:os.rmdir(path) if path.is_junction() else None)


class PortableIO(Fixture):
    def test_exact_control_byte_cap_and_one_extra_byte(self):
        raw=b'{"x":"'+b'a'*(m.MAX_INPUT_BYTES-8)+b'"}'
        self.path.write_bytes(raw)
        self.assertEqual(len(m.read_input_json(self.path)['x']),m.MAX_INPUT_BYTES-8)
        with self.path.open('ab') as handle:handle.write(b' ')
        self.reject(m.read_input_json,self.path)

    def test_bom_nested_json_and_unicode_are_preserved(self):
        value=dict(fictional=['\u03bb',True,None,dict(n=1)])
        self.path.write_bytes(b'\xef\xbb\xbf'+json.dumps(value,ensure_ascii=False).encode())
        self.assertEqual(m.read_input_json(self.path),value)

    def test_duplicate_nonstandard_and_scalar_JSON_rules_are_preserved(self):
        for raw in (b'{"x":{"y":1,"y":2}}',b'{"x":NaN}',b'{"x":Infinity}',b'\xff'):
            self.path.write_bytes(raw);self.reject(m.read_input_json,self.path)
        for raw in (b'[]',b'null',b'true',b'1',b'"fictional"'):
            self.path.write_bytes(raw);self.assertEqual(m.read_input_json(self.path),json.loads(raw))
            self.assertEqual(self.cli('--contract',str(self.path))[0],2)

    def test_relative_control_filename_remains_supported(self):
        previous=Path.cwd()
        try:
            os.chdir(self.controls)
            self.assertEqual(m.read_input_json(self.path.name),self.contract)
        finally:os.chdir(previous)

    def test_missing_protected_program_directory_still_allows_report(self):
        missing=self.base/'missing-programs'
        result=m.check_contract(self.contract,root=self.root,program_dirs=[missing])
        m.write_report(self.output,result,[self.root,missing])
        self.assertEqual(json.loads(self.output.read_bytes()),result)
        self.assertFalse(missing.exists())

    def test_target_checks_never_load_or_use_native_control_backend(self):
        with mock.patch.object(m,'_windows',side_effect=AssertionError('TARGET_BACKEND_USED')),mock.patch.object(os,'open',side_effect=AssertionError('TARGET_OPENED')),mock.patch.object(os,'scandir',side_effect=AssertionError('TARGET_ENUMERATED')):
            self.assertEqual(m.check_contract(self.contract,root=self.root,program_dirs=[self.programs]),self.result)

    def test_control_and_report_IO_never_open_or_execute_target_bodies(self):
        original=os.open
        def opened(path,*args,**kwargs):
            self.assertNotIn(Path(path),(self.target,self.program))
            return original(path,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=opened),mock.patch.object(os,'scandir',side_effect=AssertionError('TARGET_ENUMERATED')),mock.patch.object(subprocess,'run',side_effect=AssertionError('PROGRAM_EXECUTED')),mock.patch.object(socket,'socket',side_effect=AssertionError('NETWORK_OPENED')):
            code,result=self.cli('--contract',str(self.path),'--root',str(self.root),'--program-dir',str(self.programs),'--report',str(self.output))
        self.assertEqual(code,0);self.assertEqual(result,self.result)
        self.assertEqual(self.target.read_bytes(),b'FICTIONAL_TARGET_BODY')
        self.assertEqual(self.program.read_bytes(),b'FICTIONAL_PROGRAM_BODY')

    def test_final_boundary_guard_failure_retains_unconfirmed_report(self):
        original=m._protected_snapshot;calls=[]
        def changed(paths):
            snapshot,existing=original(paths);calls.append(True)
            if len(calls)>1:
                first,*rest=snapshot
                snapshot=((first[0],'MISSING',None),*rest)
            return snapshot,existing
        with mock.patch.object(m,'_protected_snapshot',side_effect=changed):self.reject(self.report)
        self.assertTrue(self.output.exists())
        self.assertEqual(json.loads(self.output.read_bytes()),self.result)

    def test_CLI_write_error_omits_native_details_and_releases_output(self):
        with mock.patch.object(os,'write',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            code,result=self.cli('--contract',str(self.path),'--root',str(self.root),'--program-dir',str(self.programs),'--report',str(self.output))
        self.assertEqual((code,result['code']),(2,'INPUT_OR_REPORT_FAILED'))
        self.output.rename(self.base/'released-report.json')

    def test_missing_protected_root_appearing_during_write_prevents_success(self):
        missing=self.base/'missing-programs';original=os.fsync
        def appear(fd):original(fd);missing.mkdir()
        with mock.patch.object(os,'fsync',side_effect=appear):self.reject(m.write_report,self.output,self.result,[self.root,missing])
        self.assertTrue(self.output.exists());self.assertTrue(missing.is_dir())

    def test_control_json_load_preserves_input(self):
        self.assertEqual(m.read_input_json(self.path),self.contract)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_short_reads_are_completed(self):
        original=os.read
        with mock.patch.object(os,'read',side_effect=lambda fd,amount:original(fd,min(3,amount))):
            self.assertEqual(m.read_input_json(self.path),self.contract)

    def test_early_eof_never_verifies_a_truncated_file(self):
        with mock.patch.object(os,'read',side_effect=[b'{}',b'']):self.reject(m.read_input_json,self.path)

    def test_growth_reads_no_more_than_limit_plus_one(self):
        original=os.read;consumed=[];changed=[]
        def grow(fd,amount):
            block=original(fd,amount);consumed.append(len(block))
            if block and not changed:
                with self.path.open('ab') as handle:handle.write(b' '*m.MAX_INPUT_BYTES)
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=grow):self.reject(m.read_input_json,self.path)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),m.MAX_INPUT_BYTES+1)

    def test_same_size_observed_mutation_is_refused(self):
        self.path.write_bytes(b'{"x":1}')
        original=os.read;changed=[]
        def mutate(fd,amount):
            block=original(fd,amount)
            if block and not changed:
                stamp=self.path.stat().st_mtime_ns
                self.path.write_bytes(b'{"x":2}');os.utime(self.path,ns=(stamp,stamp+1000000));changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=mutate):self.reject(m.read_input_json,self.path)

    def test_oversize_is_refused_before_descriptor_open(self):
        self.path.write_bytes(b' '*(m.MAX_INPUT_BYTES+1))
        with mock.patch.object(os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):self.reject(m.read_input_json,self.path)

    def test_read_failure_releases_handles(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(m.read_input_json,self.path)
        self.path.rename(self.controls/'released.py')

    def test_hardlinked_input_is_refused_without_changes(self):
        alias=self.base/'alias.py';self.hardlink(alias,self.path)
        self.reject(m.read_input_json,self.path)
        self.assertEqual(alias.read_bytes(),self.raw)

    def test_new_report_bytes_and_exclusive_creation(self):
        self.report()
        expected=(json.dumps(self.result,indent=2,ensure_ascii=True)+'\n').encode()
        self.assertEqual(self.output.read_bytes(),expected)
        self.reject(self.report)
        self.assertEqual(self.output.read_bytes(),expected)

    def test_partial_writes_complete_and_verify(self):
        original=os.write
        with mock.patch.object(os,'write',side_effect=lambda fd,data:original(fd,data[:3])):self.report()
        self.assertEqual(json.loads(self.output.read_bytes()),self.result)

    def test_zero_write_fails_and_retains_new_unconfirmed_file(self):
        with mock.patch.object(os,'write',return_value=0):self.reject(self.report)
        self.assertTrue(self.output.exists())
        self.assertEqual(self.output.read_bytes(),b'')

    def test_fsync_failure_retains_new_unconfirmed_file(self):
        with mock.patch.object(os,'fsync',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(self.report)
        self.assertTrue(self.output.exists())

    def test_readback_failure_prevents_success_and_retains_report(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(self.report)
        self.assertTrue(self.output.exists())

    def test_reports_are_refused_under_every_protected_root(self):
        for root in (m.REPOSITORY,self.controls,self.programs):
            target=root/'fictional-never-created.json'
            self.reject(m.write_report,target,self.result,[self.controls,self.programs])
            self.assertFalse(target.exists())

    def test_missing_report_parent_is_never_created(self):
        self.output=self.base/'missing'/'report.json'
        self.reject(self.report)
        self.assertFalse(self.output.parent.exists())


    def test_invalid_paths_fail_without_cli_details(self):
        for path in ('\x00FICTIONAL_PRIVATE_DETAIL',str(self.base/'missing')):
            code,result=self.cli('--contract',path)
            self.assertEqual(code,2);self.assertEqual(result['status'],'ERROR')

    def test_bad_arguments_do_not_echo_values(self):
        for args in (('FICTIONAL_PRIVATE_DETAIL',),('--contract',)):
            self.assertEqual(self.cli(*args)[0],2)


@unittest.skipIf(os.name=='nt','POSIX filesystem fixture')
class PosixIO(Fixture):
    def test_fifo_is_refused_before_open(self):
        target=self.base/'fifo';os.mkfifo(target)
        with mock.patch.object(os,'open',side_effect=AssertionError('FIFO_OPENED')):self.reject(m.read_input_json,target)

    def test_socket_is_refused_before_open(self):
        target=self.base/'socket'
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(target))
            with mock.patch.object(os,'open',side_effect=AssertionError('SOCKET_OPENED')):self.reject(m.read_input_json,target)

    def test_symlink_leaf_and_ancestor_are_refused(self):
        alias=self.base/'alias.py';alias.symlink_to(self.path)
        parent=self.base/'parent-link';parent.symlink_to(self.controls,target_is_directory=True)
        self.reject(m.read_input_json,alias);self.reject(m.read_input_json,parent/self.path.name)

    def test_replaced_leaf_is_not_followed(self):
        original=os.open;outside=self.base/'outside';outside.write_bytes(b'fictional retained')
        def replace(path,flags,*args,**kwargs):
            self.path.rename(self.base/'retained.py');self.path.symlink_to(outside)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=replace):self.reject(m.read_input_json,self.path)
        self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_inserted_report_symlink_never_replaces_target(self):
        original=os.open;outside=self.base/'outside';outside.write_bytes(b'fictional retained')
        def replace(path,flags,*args,**kwargs):
            if Path(path)==self.output:self.output.symlink_to(outside)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=replace):self.reject(self.report)
        self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_open_flags_noninheritance_and_report_mode(self):
        original_open,original_read=os.open,os.read;flags=[]
        def opened(path,mode,*args,**kwargs):flags.append(mode);return original_open(path,mode,*args,**kwargs)
        def read(fd,amount):self.assertFalse(os.get_inheritable(fd));return original_read(fd,amount)
        with mock.patch.object(os,'open',side_effect=opened),mock.patch.object(os,'read',side_effect=read):
            m.read_input_json(self.path);self.report()
        for name in ('O_NOFOLLOW','O_NONBLOCK'):
            if hasattr(os,name):self.assertTrue(all(flag&getattr(os,name) for flag in flags))
        self.assertEqual(self.output.stat().st_mode&0o777,0o600)

    def test_parent_identity_change_after_read_is_refused(self):
        original=m._parent_chain;observed=[]
        def changed(path):
            rows=original(path);observed.append(True)
            if len(observed)>1:
                first,*rest=rows;return ((first[0],(first[1][0],first[1][1]+1,*first[1][2:])),*rest)
            return rows
        with mock.patch.object(m,'_parent_chain',side_effect=changed):self.reject(m.read_input_json,self.path)

    def test_posix_works_without_windows_backend_file(self):
        copied=self.base/'environment_check.py';copied.write_bytes(MODULE.read_bytes())
        spec=importlib.util.spec_from_file_location('isolated_posix_environment',copied)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.read_input_json(self.path),self.contract);self.assertIsNone(module._WINDOWS_BACKEND)


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class WindowsIO(Fixture):
    def test_invalid_spellings_stop_before_native_access(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('INVALID_PATH_OPENED')):
            for value in values:self.reject(m.read_input_json,value)

    def test_remote_volume_is_refused_before_native_open(self):
        native=w.Native(w._core(m.ContractError))
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            self.reject(native.open,Path(self.path.anchor),True)

    def test_native_crt_mismatch_is_refused_before_data_read(self):
        original=w.Native.describe;files=[]
        def mismatch(native,handle,directory):
            identity,name=original(native,handle,directory)
            if not directory:
                files.append(True)
                if len(files)==2:identity=(identity[0],identity[1]+1,*identity[2:])
            return identity,name
        with mock.patch.object(w.Native,'describe',new=mismatch),mock.patch.object(os,'read',side_effect=AssertionError('MISMATCH_READ')):self.reject(m.read_input_json,self.path)

    def test_binary_noninheritable_descriptor_is_retained(self):
        with w.regular(self.path,m.ContractError,single_link=True) as fd:
            self.assertFalse(os.get_inheritable(fd));self.assertEqual(os.read(fd,len(self.raw)+1),self.raw)
            with self.assertRaises(OSError):self.path.rename(self.base/'blocked.py')
        self.path.rename(self.base/'released.py')

    def test_symlink_input_leaf_is_refused(self):
        alias=self.base/'source-link';self.symlink(alias,self.path);self.reject(m.read_input_json,alias)

    def test_symlink_input_ancestor_is_refused(self):
        alias=self.base/'parent-link';self.symlink(alias,self.controls,True);self.reject(m.read_input_json,alias/self.path.name)

    def test_junction_candidate_is_refused(self):
        alias=self.base/'candidate-junction';self.junction(alias,self.controls);self.reject(m.read_input_json,alias/self.path.name)


    def test_junction_report_parent_is_refused(self):
        alias=self.base/'report-junction';self.junction(alias,self.programs)
        self.reject(m.write_report,alias/'report.json',self.result,[self.controls,self.programs])
        self.assertFalse((self.programs/'report.json').exists())

    def test_symlink_report_leaf_never_replaces_target(self):
        outside=self.base/'retained';outside.write_bytes(b'fictional retained');self.symlink(self.output,outside)
        self.reject(self.report);self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_hardlinked_report_is_never_overwritten(self):
        outside=self.base/'retained';outside.write_bytes(b'fictional retained');self.hardlink(self.output,outside)
        self.reject(self.report);self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_named_stream_argument_is_refused(self):
        stream=Path(str(self.path)+':fictional');stream.write_bytes(b'fictional stream')
        self.reject(m.read_input_json,stream);self.assertEqual(stream.read_bytes(),b'fictional stream')

    def test_ordinary_file_does_not_read_or_change_named_stream(self):
        stream=Path(str(self.path)+':fictional');stream.write_bytes(b'fictional stream')
        self.assertEqual(m.read_input_json(self.path),self.contract)
        self.assertEqual(stream.read_bytes(),b'fictional stream')

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        folder=self.base/'fictional long directory';folder.mkdir();source=folder/'payload.py';source.write_bytes(self.raw)
        buffer=ctypes.create_unicode_buffer(32768);size=method(str(source),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(source).casefold():self.skipTest('Optional short-name alias unavailable')
        self.reject(m.read_input_json,buffer.value)

    def test_native_report_repository_alias_is_refused_before_creation(self):
        native=w.Native(w._core(m.ContractError))
        with w.Chain(native,m.REPOSITORY) as root:repository=root.items[-1][2]
        original=w.Native.open
        def alias(native,path,directory,expected=None):
            handle,identity,final=original(native,path,directory,expected)
            if path==self.base:final=repository
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=alias):self.reject(self.report)
        self.assertFalse(self.output.exists())


    def test_cli_interruption_and_help_use_fixed_public_text(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt):
            code,result=self.cli('--contract',str(self.path),'--root',str(self.root),'--program-dir',str(self.programs))
        self.assertEqual((code,result['code']),(130,'INPUT_OR_REPORT_INTERRUPTED'))
        self.path.rename(self.base/'released.py')
        stdout=io.StringIO()
        with mock.patch.object(m.sys,'argv',['FICTIONAL_PRIVATE_DETAIL']),redirect_stdout(stdout),self.assertRaises(SystemExit) as captured:m.main(['--help'])
        self.assertEqual(captured.exception.code,0);self.assertIn('environment-contract-checker',stdout.getvalue());self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',stdout.getvalue())


if __name__=='__main__':unittest.main()
