"""Invented JSON, redaction values and disposable read-failure fixtures only."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
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

MODULE=Path(__file__).resolve().parents[1]/'helpers.py'
SPEC=importlib.util.spec_from_file_location('helpers_input_fixture',MODULE)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-helpers-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.root=self.base/'inputs'
        self.root.mkdir()
        self.path=self.root/'fictional.json'
        self.raw=b'{"fictional":true}'
        self.path.write_bytes(self.raw)

    def rejected(self,value,**kwargs):
        with self.assertRaises(m.HelperError) as captured:m.load_json_object(value,**kwargs)
        self.assertEqual(str(captured.exception),'JSON_OBJECT_LOAD_FAILED')
        self.assertTrue(captured.exception.__suppress_context__)
        return captured.exception

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_HELPERS_REQUIRE_LINKS')=='1':
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
        self.assertEqual(m.load_json_object(self.path),{'nested':[1,True,None,{'label':'fictional'}]})
        self.assertEqual(self.path.read_bytes(),raw)

    def test_duplicate_object_keys_keep_last_value(self):
        self.path.write_bytes(b'{"x":1,"x":2}')
        self.assertEqual(m.load_json_object(self.path),{'x':2})

    def test_top_level_nonobjects_still_fail(self):
        for raw in (b'[]',b'null',b'true',b'1',b'"fictional"'):
            self.path.write_bytes(raw)
            self.rejected(self.path)

    def test_nonstandard_constants_rejected_but_exponent_behavior_preserved(self):
        for literal in ('NaN','Infinity','-Infinity'):
            self.path.write_text('{"x":'+literal+'}',encoding='utf-8')
            self.rejected(self.path)
        self.path.write_bytes(b'{"x":1e999}')
        self.assertTrue(math.isinf(m.load_json_object(self.path)['x']))

    def test_invalid_json_and_encoding_errors_omit_values_and_path(self):
        for raw in (b'{FICTIONAL_PRIVATE_DETAIL',b'\xffFICTIONAL_PRIVATE_DETAIL',b''):
            self.path.write_bytes(raw)
            error=self.rejected(self.path)
            self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',str(error))
            self.assertNotIn(str(self.path),str(error))

    def test_invalid_limits_keep_original_error_before_any_read(self):
        with mock.patch.object(m,'_read_bytes',side_effect=AssertionError('INVALID_LIMIT_READ')):
            for limit in (True,False,0,-1,1.5,None,16*1024*1024+1):
                with self.assertRaises(m.HelperError) as captured:m.load_json_object(self.path,max_bytes=limit)
                self.assertEqual(str(captured.exception),'INVALID_LIMIT')

    def test_exact_byte_limit_and_initial_oversize_before_descriptor_open(self):
        self.path.write_bytes(b'{}')
        self.assertEqual(m.load_json_object(self.path,max_bytes=2),{})
        with mock.patch.object(os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):
            self.rejected(self.path,max_bytes=1)

    def test_default_limit_accepts_exact_boundary_and_rejects_one_extra_byte(self):
        size=1024*1024
        raw=b'{"x":"'+b'a'*(size-8)+b'"}'
        self.assertEqual(len(raw),size)
        self.path.write_bytes(raw)
        self.assertEqual(len(m.load_json_object(self.path)['x']),size-8)
        with self.path.open('ab') as handle:handle.write(b' ')
        self.rejected(self.path)

    def test_maximum_override_accepts_exact_cap(self):
        size=16*1024*1024
        raw=b'{"x":"'+b'a'*(size-8)+b'"}'
        self.path.write_bytes(raw)
        self.assertEqual(len(m.load_json_object(self.path,max_bytes=size)['x']),size-8)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).digest(),hashlib.sha256(raw).digest())

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
                with self.path.open('ab') as handle:handle.write(b' '*100)
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=grow):self.rejected(self.path,max_bytes=16)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),17)
        self.assertTrue(all(0<amount<=17 for amount in requests))

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
            self.assertEqual(m.load_json_object(self.path),{'fictional':True})

    def test_read_failure_is_fixed_and_descriptors_are_closed(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            self.rejected(self.path)
        self.path.rename(self.root/'released.json')

    def test_invalid_types_nul_and_parent_traversal_are_fixed_errors(self):
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
        self.assertEqual(m.load_json_object(alias),{'fictional':True})
        self.assertEqual(alias.read_bytes(),self.raw)
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_filename_extension_does_not_import_or_execute_input(self):
        source=self.root/'fictional.py'
        source.write_bytes(b'{"fictional":true}')
        self.assertEqual(m.load_json_object(source),{'fictional':True})
        source.write_text("raise RuntimeError('FICTIONAL_INPUT_CODE')",encoding='utf-8')
        self.rejected(source)

    def test_library_is_silent_and_writes_no_input_tree_files(self):
        before={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            result=m.load_json_object(self.path)
            m.redact_structure(result)
            self.rejected(self.root/'missing.json')
        after={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before,after)
        self.assertEqual((stdout.getvalue(),stderr.getvalue()),('',''))

    def test_redaction_key_normalization_and_separate_copy_remain(self):
        source={'items':[{key.upper().replace('_','-'):'fictional-value' for key in m.SENSITIVE_KEYS}], 'keep':[{'label':'fictional'}]}
        before=json.dumps(source,sort_keys=True)
        output=m.redact_structure(source)
        self.assertTrue(all(value=='<redacted>' for value in output['items'][0].values()))
        output['keep'][0]['label']='changed fiction'
        self.assertEqual(json.dumps(source,sort_keys=True),before)

    def test_redaction_depth_cycles_types_and_key_checks_remain(self):
        for limit in (0,129,True,None):
            with self.assertRaises(m.HelperError) as captured:m.redact_structure({},max_depth=limit)
            self.assertEqual(str(captured.exception),'INVALID_DEPTH')
        cyclic=[]
        cyclic.append(cyclic)
        with self.assertRaises(m.HelperError) as captured:m.redact_structure(cyclic,max_depth=3)
        self.assertEqual(str(captured.exception),'DEPTH_LIMIT')
        for value in ((1,),b'fictional',{1:'fictional'}):
            with self.assertRaises(m.HelperError):m.redact_structure(value)

    def test_redaction_retains_free_text_unknown_fields_and_float_semantics(self):
        source={'note':'fictional token in prose','unlisted':'fictional-value','overflow':float('inf'),'unknown':float('nan')}
        output=m.redact_structure(source)
        self.assertEqual(output['note'],source['note'])
        self.assertEqual(output['unlisted'],source['unlisted'])
        self.assertTrue(math.isinf(output['overflow']))
        self.assertTrue(math.isnan(output['unknown']))


@unittest.skipIf(os.name=='nt','POSIX filesystem fixture')
class PosixInputs(Fixture):
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
            self.assertEqual(m.load_json_object(self.path),{'fictional':True})
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
        copied=library/'helpers.py'
        copied.write_bytes(MODULE.read_bytes())
        spec=importlib.util.spec_from_file_location('isolated_posix_helpers',copied)
        isolated=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(isolated)
        self.assertEqual(isolated.load_json_object(self.path),{'fictional':True})
        self.assertIsNone(isolated._WINDOWS_BACKEND)


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class WindowsInputs(Fixture):
    def test_invalid_spellings_stop_before_native_access(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:self.rejected(value)

    def test_remote_drive_is_refused_before_native_open(self):
        native=w.Native({'Rejected':m.HelperError,'EntryFailure':m.HelperError})
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(m.HelperError):native.open(Path(self.path.anchor),True)

    def test_binary_noninheritable_descriptor_is_retained_and_closed(self):
        with w.regular(self.path,m.HelperError) as fd:
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
        self.assertEqual(m.load_json_object(self.path),{'fictional':True})
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
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.load_json_object(self.path)
        self.path.rename(self.root/'released.json')


if __name__=='__main__':unittest.main()
