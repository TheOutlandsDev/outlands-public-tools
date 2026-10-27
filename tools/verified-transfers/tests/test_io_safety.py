"""Invented source packages and disposable copy/verification failures only."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
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

MODULE=Path(__file__).resolve().parents[1]/'transfer.py'
SPEC=importlib.util.spec_from_file_location('transfer_io_fixture',MODULE)
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-transfer-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.candidate=self.base/'candidate';self.candidate.mkdir()
        self.current=self.base/'current';self.current.mkdir()
        self.path=self.candidate/'payload.py'
        self.raw=b"raise RuntimeError('FICTIONAL_EXECUTED')\n"
        self.path.write_bytes(self.raw)
        self.manifest=self.base/'manifest.json'
        self.manifest.write_text(json.dumps(dict(schema_version=1,inventory=[dict(path=self.path.name,size=len(self.raw),sha256=hashlib.sha256(self.raw).hexdigest())])),encoding='utf-8')
        self.pin=hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.output=self.base/'new-output.json'
        self.bundle=self.base/'new-bundle'
        self.result=dict(schema_version=1,fictional='invented')

    def reject(self,call,*args,**kwargs):
        with self.assertRaises((m.TransferError,OSError,ValueError,TypeError,RecursionError)):call(*args,**kwargs)

    def write_output(self):m.write_new(self.output,(json.dumps(self.result,indent=2,ensure_ascii=True)+'\n').encode())

    def package(self):return m.package_source(self.candidate,self.manifest,self.bundle,expected_manifest_sha=self.pin)

    def cli(self,*args):
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):code=m.main(list(args))
        self.assertEqual(stderr.getvalue(),'')
        result=json.loads(stdout.getvalue())
        self.assertNotIn(str(self.base),stdout.getvalue())
        self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',stdout.getvalue())
        return code,result

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_TRANSFERS_REQUIRE_LINKS')=='1':raise AssertionError('Required native '+name+' creation failed') from error
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
    def test_package_copies_only_selected_source_without_execution(self):
        hidden=self.candidate/'.env';hidden.write_bytes(b'fictional unselected')
        folder=self.candidate/'.git';folder.mkdir();control=folder/'config';control.write_bytes(b'fictional control')
        original=m.checked_file
        def read(path,**kwargs):
            self.assertNotIn(Path(path),(hidden,control))
            return original(path,**kwargs)
        with mock.patch.object(m,'checked_file',side_effect=read),mock.patch.object(subprocess,'run',side_effect=AssertionError('PAYLOAD_EXECUTED')),mock.patch.object(os,'system',side_effect=AssertionError('SHELL_EXECUTED')):
            result=self.package()
        self.assertEqual(result['format'],m.SOURCE_FORMAT)
        self.assertEqual((self.bundle/'payload'/self.path.name).read_bytes(),self.raw)
        self.assertEqual({p.name for p in (self.bundle/'payload').iterdir()},{self.path.name})
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_source_pin_failure_prevents_destination_creation(self):
        self.reject(m.package_source,self.candidate,self.manifest,self.bundle,expected_manifest_sha='0'*64)
        self.assertFalse(self.bundle.exists())
        self.manifest.write_bytes(self.manifest.read_bytes()+b' ')
        self.reject(self.package);self.assertFalse(self.bundle.exists())

    def test_uppercase_source_and_bundle_pins_remain_supported(self):
        result=m.package_source(self.candidate,self.manifest,self.bundle,expected_manifest_sha=self.pin.upper())
        self.assertEqual(m.verify(self.bundle,expected_manifest_sha=result['manifest_sha256'].upper()),result)

    def test_payload_tampering_is_rejected(self):
        result=self.package();(self.bundle/'payload'/self.path.name).write_bytes(b'fictional changed')
        self.reject(m.verify,self.bundle,expected_manifest_sha=result['manifest_sha256'])

    def test_resigned_bundle_cannot_pass_the_previous_external_pin(self):
        result=self.package();raw=b'fictional resigned text'
        (self.bundle/'payload'/self.path.name).write_bytes(raw)
        manifest=json.loads((self.bundle/m.MANIFEST).read_bytes())
        manifest['inventory'][0].update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        data=(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n').encode()
        (self.bundle/m.MANIFEST).write_bytes(data)
        (self.bundle/m.CHECKSUM).write_bytes((hashlib.sha256(data).hexdigest()+'  '+m.MANIFEST+'\n').encode('ascii'))
        self.assertEqual(m.verify(self.bundle)['inventory'],manifest['inventory'])
        self.reject(m.verify,self.bundle,expected_manifest_sha=result['manifest_sha256'])

    def test_utf8_bom_split_reads_and_invalid_final_sequences(self):
        original=os.read
        self.path.write_bytes(b'\xef\xbb\xbf'+ 'fictional \u03bb'.encode())
        with mock.patch.object(os,'read',side_effect=lambda fd,amount:original(fd,min(amount,1))):
            row=m.checked_file(self.path,output=self.output,text=True)
        self.assertEqual(self.output.read_bytes(),self.path.read_bytes())
        self.assertEqual(row['size'],len(self.path.read_bytes()))
        for raw in (b'fictional\x00text',b'fictional\xe2\x82'):
            self.path.write_bytes(raw);self.reject(m.checked_file,self.path,text=True)

    def test_zero_copy_write_retains_partial_bundle_without_manifest(self):
        with mock.patch.object(os,'write',return_value=0):self.reject(self.package)
        self.assertTrue(self.bundle.is_dir())
        self.assertFalse((self.bundle/m.MANIFEST).exists())
        self.assertEqual((self.bundle/'payload'/self.path.name).read_bytes(),b'')

    def test_changed_source_after_destination_creation_retains_partial(self):
        original=m.new_destination
        def changed(path):
            result=original(path);self.path.write_bytes(b'fictional changed');return result
        with mock.patch.object(m,'new_destination',side_effect=changed):self.reject(self.package)
        self.assertTrue(self.bundle.is_dir());self.assertFalse((self.bundle/m.MANIFEST).exists())

    def test_empty_selected_file_remains_supported(self):
        self.path.write_bytes(b'')
        self.manifest.write_text(json.dumps(dict(schema_version=1,inventory=[dict(path=self.path.name,size=0,sha256=hashlib.sha256(b'').hexdigest())])),encoding='utf-8')
        self.pin=hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        result=self.package();self.assertEqual(result['inventory'][0]['size'],0)
        self.assertEqual((self.bundle/'payload'/self.path.name).read_bytes(),b'')

    def test_short_writes_complete_payload_and_metadata(self):
        original=os.write
        with mock.patch.object(os,'write',side_effect=lambda fd,data:original(fd,data[:3])):result=self.package()
        self.assertEqual(m.verify(self.bundle,expected_manifest_sha=result['manifest_sha256']),result)

    def test_streamed_hash_and_collection_preserve_source(self):
        expected=dict(size=len(self.raw),sha256=hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(m.checked_file(self.path),expected)
        self.assertEqual(m.checked_file(self.path,collect=True),(expected,self.raw))
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_empty_file_with_zero_limit_remains_supported(self):
        self.path.write_bytes(b'')
        self.assertEqual(m.checked_file(self.path,max_bytes=0),dict(size=0,sha256=hashlib.sha256(b'').hexdigest()))

    def test_short_reads_are_completed(self):
        original=os.read
        with mock.patch.object(os,'read',side_effect=lambda fd,amount:original(fd,min(3,amount))):
            self.assertEqual(m.checked_file(self.path,collect=True)[1],self.raw)

    def test_early_eof_never_verifies_a_truncated_file(self):
        with mock.patch.object(os,'read',side_effect=[b'{}',b'']):self.reject(m.checked_file,self.path)

    def test_growth_reads_no_more_than_limit_plus_one(self):
        original=os.read;consumed=[];changed=[]
        def grow(fd,amount):
            block=original(fd,amount);consumed.append(len(block))
            if block and not changed:
                with self.path.open('ab') as handle:handle.write(b' '*100)
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=grow):self.reject(m.checked_file,self.path,max_bytes=len(self.raw))
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),len(self.raw)+1)

    def test_same_size_observed_mutation_is_refused(self):
        original=os.read;changed=[]
        def mutate(fd,amount):
            block=original(fd,amount)
            if block and not changed:
                stamp=self.path.stat().st_mtime_ns
                self.path.write_bytes(b'x'*len(self.raw));os.utime(self.path,ns=(stamp,stamp+1000000));changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=mutate):self.reject(m.checked_file,self.path)

    def test_oversize_is_refused_before_descriptor_open(self):
        with mock.patch.object(os,'open',side_effect=AssertionError('OVERSIZE_OPENED')):self.reject(m.checked_file,self.path,max_bytes=1)

    def test_read_failure_releases_handles(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(m.checked_file,self.path)
        self.path.rename(self.candidate/'released.py')

    def test_hardlinked_input_is_refused_without_changes(self):
        alias=self.base/'alias.py';self.hardlink(alias,self.path)
        self.reject(m.checked_file,self.path)
        self.assertEqual(alias.read_bytes(),self.raw)

    def test_new_output_bytes_and_exclusive_creation(self):
        self.write_output()
        expected=(json.dumps(self.result,indent=2,ensure_ascii=True)+'\n').encode()
        self.assertEqual(self.output.read_bytes(),expected)
        self.reject(self.write_output)
        self.assertEqual(self.output.read_bytes(),expected)

    def test_partial_writes_complete_and_verify(self):
        original=os.write
        with mock.patch.object(os,'write',side_effect=lambda fd,data:original(fd,data[:3])):self.write_output()
        self.assertEqual(json.loads(self.output.read_bytes()),self.result)

    def test_zero_write_fails_and_retains_new_unconfirmed_file(self):
        with mock.patch.object(os,'write',return_value=0):self.reject(self.write_output)
        self.assertTrue(self.output.exists())
        self.assertEqual(self.output.read_bytes(),b'')

    def test_fsync_failure_retains_new_unconfirmed_file(self):
        with mock.patch.object(os,'fsync',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(self.write_output)
        self.assertTrue(self.output.exists())

    def test_readback_failure_prevents_success_and_retains_output(self):
        with mock.patch.object(os,'read',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):self.reject(self.write_output)
        self.assertTrue(self.output.exists())


    def test_missing_output_parent_is_never_created(self):
        self.output=self.base/'missing'/'report.json'
        self.reject(self.write_output)
        self.assertFalse(self.output.parent.exists())


    def test_invalid_paths_fail_without_cli_details(self):
        for path in ('\x00FICTIONAL_PRIVATE_DETAIL',str(self.base/'missing')):
            code,result=self.cli('verify','--bundle',path)
            self.assertEqual(code,2);self.assertEqual(result['status'],'ERROR')

    def test_bad_arguments_do_not_echo_values(self):
        for args in (('FICTIONAL_PRIVATE_DETAIL',),('verify','--bundle')):
            self.assertEqual(self.cli(*args)[0],2)


@unittest.skipIf(os.name=='nt','POSIX filesystem fixture')
class PosixIO(Fixture):
    def test_package_directory_modes_are_private_requests(self):
        self.package()
        self.assertEqual(self.bundle.stat().st_mode&0o777,0o700)
        self.assertEqual((self.bundle/'payload').stat().st_mode&0o777,0o700)

    def test_library_interruption_propagates_and_releases_descriptors(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):m.checked_file(self.path)
        self.path.rename(self.base/'released.py')

    def test_fifo_is_refused_before_open(self):
        target=self.base/'fifo';os.mkfifo(target)
        with mock.patch.object(os,'open',side_effect=AssertionError('FIFO_OPENED')):self.reject(m.checked_file,target)

    def test_socket_is_refused_before_open(self):
        target=self.base/'socket'
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as endpoint:
            endpoint.bind(str(target))
            with mock.patch.object(os,'open',side_effect=AssertionError('SOCKET_OPENED')):self.reject(m.checked_file,target)

    def test_symlink_leaf_and_ancestor_are_refused(self):
        alias=self.base/'alias.py';alias.symlink_to(self.path)
        parent=self.base/'parent-link';parent.symlink_to(self.candidate,target_is_directory=True)
        self.reject(m.checked_file,alias);self.reject(m.checked_file,parent/self.path.name)

    def test_replaced_leaf_is_not_followed(self):
        original=os.open;outside=self.base/'outside';outside.write_bytes(b'fictional retained')
        def replace(path,flags,*args,**kwargs):
            self.path.rename(self.base/'retained.py');self.path.symlink_to(outside)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=replace):self.reject(m.checked_file,self.path)
        self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_inserted_output_symlink_never_replaces_target(self):
        original=os.open;outside=self.base/'outside';outside.write_bytes(b'fictional retained')
        def replace(path,flags,*args,**kwargs):
            if Path(path)==self.output:self.output.symlink_to(outside)
            return original(path,flags,*args,**kwargs)
        with mock.patch.object(os,'open',side_effect=replace):self.reject(self.write_output)
        self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_open_flags_noninheritance_and_output_mode(self):
        original_open,original_read=os.open,os.read;flags=[]
        def opened(path,mode,*args,**kwargs):flags.append(mode);return original_open(path,mode,*args,**kwargs)
        def read(fd,amount):self.assertFalse(os.get_inheritable(fd));return original_read(fd,amount)
        with mock.patch.object(os,'open',side_effect=opened),mock.patch.object(os,'read',side_effect=read):
            m.checked_file(self.path);self.write_output()
        for name in ('O_NOFOLLOW','O_NONBLOCK'):
            if hasattr(os,name):self.assertTrue(all(flag&getattr(os,name) for flag in flags))
        self.assertEqual(self.output.stat().st_mode&0o777,0o600)

    def test_parent_identity_change_after_read_is_refused(self):
        original=m._posix_chain;observed=[]
        def changed(path):
            rows=original(path);observed.append(True)
            if len(observed)>1:
                first,*rest=rows;return ((first[0],first[1],first[2]+1,first[3]),*rest)
            return rows
        with mock.patch.object(m,'_posix_chain',side_effect=changed):self.reject(m.checked_file,self.path)

    def test_posix_works_without_windows_backend_file(self):
        copied=self.base/'transfer.py';copied.write_bytes(MODULE.read_bytes())
        spec=importlib.util.spec_from_file_location('isolated_posix_transfer',copied)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.checked_file(self.path)['size'],len(self.raw));self.assertIsNone(module._WINDOWS_BACKEND)


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class WindowsIO(Fixture):
    def test_symlink_destination_is_not_followed_or_replaced(self):
        self.symlink(self.bundle,self.current,True)
        self.reject(self.package);self.assertEqual(list(self.current.iterdir()),[])

    def test_junction_destination_is_not_followed_or_replaced(self):
        self.junction(self.bundle,self.current)
        self.reject(self.package);self.assertEqual(list(self.current.iterdir()),[])

    def test_native_destination_alias_inside_source_is_refused(self):
        original=w.Native.open
        native=w.Native(w._core(m.TransferError))
        with w.Chain(native,self.candidate) as chain:source=chain.items[-1][2]
        def alias(native,path,directory,expected=None):
            handle,identity,final=original(native,path,directory,expected)
            if path==self.base:final=source
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=alias):self.reject(w.separate_destination,self.candidate,self.bundle,m.TransferError)
        self.assertFalse(self.bundle.exists())

    def test_invalid_spellings_stop_before_native_access(self):
        values=[r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800']
        with mock.patch.object(w,'Native',side_effect=AssertionError('INVALID_PATH_OPENED')):
            for value in values:self.reject(m.checked_file,value)

    def test_remote_volume_is_refused_before_native_open(self):
        native=w.Native(w._core(m.TransferError))
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
        with mock.patch.object(w.Native,'describe',new=mismatch),mock.patch.object(os,'read',side_effect=AssertionError('MISMATCH_READ')):self.reject(m.checked_file,self.path)

    def test_binary_noninheritable_descriptor_is_retained(self):
        with w.regular(self.path,m.TransferError,single_link=True) as fd:
            self.assertFalse(os.get_inheritable(fd));self.assertEqual(os.read(fd,100),self.raw)
            with self.assertRaises(OSError):self.path.rename(self.base/'blocked.py')
        self.path.rename(self.base/'released.py')

    def test_symlink_input_leaf_is_refused(self):
        alias=self.base/'source-link';self.symlink(alias,self.path);self.reject(m.checked_file,alias)

    def test_symlink_input_ancestor_is_refused(self):
        alias=self.base/'parent-link';self.symlink(alias,self.candidate,True);self.reject(m.checked_file,alias/self.path.name)

    def test_junction_candidate_is_refused(self):
        alias=self.base/'candidate-junction';self.junction(alias,self.candidate);self.reject(m.package_source,alias,self.manifest,self.bundle,expected_manifest_sha=self.pin)


    def test_junction_output_parent_is_refused(self):
        alias=self.base/'report-junction';self.junction(alias,self.current)
        self.reject(m.write_new,alias/'report.json',b'fictional')
        self.assertFalse((self.current/'report.json').exists())

    def test_symlink_output_leaf_never_replaces_target(self):
        outside=self.base/'retained';outside.write_bytes(b'fictional retained');self.symlink(self.output,outside)
        self.reject(self.write_output);self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_hardlinked_output_is_never_overwritten(self):
        outside=self.base/'retained';outside.write_bytes(b'fictional retained');self.hardlink(self.output,outside)
        self.reject(self.write_output);self.assertEqual(outside.read_bytes(),b'fictional retained')

    def test_named_stream_argument_is_refused(self):
        stream=Path(str(self.path)+':fictional');stream.write_bytes(b'fictional stream')
        self.reject(m.checked_file,stream);self.assertEqual(stream.read_bytes(),b'fictional stream')

    def test_ordinary_file_does_not_read_or_change_named_stream(self):
        stream=Path(str(self.path)+':fictional');stream.write_bytes(b'fictional stream')
        self.assertEqual(m.checked_file(self.path,collect=True)[1],self.raw)
        self.assertEqual(stream.read_bytes(),b'fictional stream')

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        folder=self.base/'fictional long directory';folder.mkdir();source=folder/'payload.py';source.write_bytes(self.raw)
        buffer=ctypes.create_unicode_buffer(32768);size=method(str(source),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(source).casefold():self.skipTest('Optional short-name alias unavailable')
        self.reject(m.checked_file,buffer.value)

    def test_native_output_repository_alias_is_refused_before_creation(self):
        native=w.Native(w._core(m.TransferError))
        with w.Chain(native,m.REPOSITORY) as root:repository=root.items[-1][2]
        original=w.Native.open
        def alias(native,path,directory,expected=None):
            handle,identity,final=original(native,path,directory,expected)
            if path==self.base:final=repository
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=alias):self.reject(self.write_output)
        self.assertFalse(self.output.exists())


    def test_cli_interruption_and_help_use_fixed_public_text(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt):
            code,result=self.cli('package','--source',str(self.candidate),'--manifest',str(self.manifest),'--expected-manifest-sha',self.pin,'--destination',str(self.bundle))
        self.assertEqual((code,result['code']),(130,'TRANSFER_INTERRUPTED'))
        self.path.rename(self.base/'released.py')
        stdout=io.StringIO()
        with mock.patch.object(m.sys,'argv',['FICTIONAL_PRIVATE_DETAIL']),redirect_stdout(stdout),self.assertRaises(SystemExit) as captured:m.main(['--help'])
        self.assertEqual(captured.exception.code,0);self.assertIn('transfer.py',stdout.getvalue());self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',stdout.getvalue())


if __name__=='__main__':unittest.main()
