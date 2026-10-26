"""Invented documentation and disposable metadata/read failure fixtures only."""
from contextlib import redirect_stdout
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

SPEC=importlib.util.spec_from_file_location('docs_safety_fixture',Path(__file__).resolve().parents[1]/'docs_check.py')
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
w=m._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(prefix='fictional-docs-',dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name)
        self.root=self.base/'documents'
        self.root.mkdir()
        self.file=self.root/'example.md'
        self.file.write_bytes(b'# Fictional\n')

    def cli(self,*args):
        output=io.StringIO()
        with redirect_stdout(output):
            code=m.main(['--root',str(self.root),*args])
        return code,json.loads(output.getvalue())

    def feature_failure(self,error,name):
        if os.environ.get('OUTLANDS_DOCS_REQUIRE_LINKS')=='1':
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


class PortableIO(Fixture):
    def test_bom_newlines_and_relative_line_numbers_remain(self):
        self.file.write_bytes(b'\xef\xbb\xbf# Fictional\r\n\r[x](absent.txt)\n')
        report=m.check(self.root)
        self.assertEqual(report['checked_documents'],1)
        self.assertEqual(report['findings'],[dict(path='example.md',line=3,rule='MISSING_OR_LINKED_TARGET')])

    def test_json_semantics_and_nonstandard_constants_remain(self):
        for index,text in enumerate(('null','{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"x":-Infinity}')):
            (self.root/(str(index)+'.json')).write_text(text,encoding='utf-8')
        report=m.check(self.root)
        self.assertEqual(report['checked_documents'],6)
        self.assertEqual([row['path'] for row in report['findings']],['2.json','3.json','4.json'])
        self.assertTrue(all(row['rule']=='INVALID_JSON' for row in report['findings']))

    def test_exclusions_and_selected_extensions_remain(self):
        for name in ('.git','.hidden','node_modules','runtime','private','__pycache__'):
            folder=self.root/name
            folder.mkdir()
            (folder/'invalid.json').write_bytes(b'{fictional')
        (self.root/'ignored.txt').write_bytes(b'{fictional')
        (self.root/'upper.JSON').write_bytes(b'{}')
        report=m.check(self.root)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['checked_documents'],2)

    def test_case_sensitive_name_sort_and_finding_order_remain(self):
        self.file.unlink()
        for name in ('b.md','Z.md','A.md'):
            (self.root/name).write_text('[x](absent.txt)',encoding='utf-8')
        self.assertEqual([row['path'] for row in m.check(self.root)['findings']],['A.md','Z.md','b.md'])

    def test_external_links_and_code_are_not_fetched_or_executed(self):
        self.file.write_text('```python\n[x](absent.txt)\n```\n`[x](absent.txt)`\n[site](https://example.org/)\n[mail](mailto:reader@example.com)\n',encoding='utf-8')
        with mock.patch.object(subprocess,'run',side_effect=AssertionError('SOURCE_EXECUTED')):
            self.assertEqual(m.check(self.root)['status'],'PASS')

    def test_local_target_failure_omits_target_and_exception_values(self):
        self.file.write_text('[x](fictional-target.bin)',encoding='utf-8')
        with mock.patch.object(m,'_check_target',side_effect=OSError('FICTIONAL_PRIVATE_DETAIL')):
            code,report=self.cli()
        self.assertEqual(code,1)
        self.assertNotIn('FICTIONAL_PRIVATE_DETAIL',json.dumps(report))
        self.assertNotIn('fictional-target.bin',json.dumps(report))
        self.assertEqual(report['findings'][0]['rule'],'MISSING_OR_LINKED_TARGET')

    def test_initial_oversize_is_refused_without_descriptor_read(self):
        with mock.patch.object(m,'MAX_BYTES',2),mock.patch.object(os,'read',side_effect=AssertionError('OVERSIZED_READ')):
            report=m.check(self.root)
        self.assertEqual(report['findings'],[dict(path='example.md',rule='SIZE_OR_TYPE')])
        self.assertEqual(report['checked_documents'],0)

    def test_growth_cannot_exceed_limit_plus_one_or_report_pass(self):
        self.file.write_bytes(b'fictional')
        original=os.read
        changed,consumed,requests=[],[],[]
        def grow(fd,amount):
            requests.append(amount)
            block=original(fd,amount)
            consumed.append(len(block))
            if block and not changed:
                with self.file.open('ab') as handle:handle.write(b'X'*100)
                changed.append(True)
            return block
        with mock.patch.object(m,'MAX_BYTES',16),mock.patch.object(os,'read',side_effect=grow):
            report=m.check(self.root)
        self.assertTrue(changed)
        self.assertLessEqual(sum(consumed),17)
        self.assertTrue(all(0<amount<=17 for amount in requests))
        self.assertEqual(report['findings'],[dict(path='example.md',rule='READ_ERROR')])
        self.assertEqual(report['checked_documents'],0)

    def test_same_size_mutation_requires_read_error(self):
        original=os.read
        changed=[]
        def mutate(fd,amount):
            block=original(fd,amount)
            if block and not changed:
                stamp=self.file.stat().st_mtime_ns
                self.file.write_bytes(b'X'*len(b'# Fictional\n'))
                os.utime(self.file,ns=(stamp,stamp+1_000_000))
                changed.append(True)
            return block
        with mock.patch.object(os,'read',side_effect=mutate):report=m.check(self.root)
        self.assertEqual(report['findings'],[dict(path='example.md',rule='READ_ERROR')])

    def test_decode_and_read_failures_cannot_clear_review(self):
        self.file.write_bytes(b'\xffFICTIONAL_CONTENT_DETAIL')
        code,report=self.cli()
        self.assertEqual(code,1)
        self.assertEqual(report['checked_documents'],0)
        self.assertNotIn('FICTIONAL_CONTENT_DETAIL',json.dumps(report))
        with mock.patch.object(m,'_read_text',side_effect=OSError('FICTIONAL_EXCEPTION_DETAIL')):
            code,report=self.cli()
        self.assertEqual(code,1)
        self.assertNotIn('FICTIONAL_EXCEPTION_DETAIL',json.dumps(report))

    def test_directory_budget_stops_before_sorting_excess_entries(self):
        consumed=[]
        class Entry:
            @property
            def name(self):raise AssertionError('SORTED_BEFORE_LIMIT')
        class Stream:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def __iter__(self):
                for _ in range(20):
                    consumed.append(True)
                    yield Entry()
        with mock.patch.object(m,'MAX_FILES',3),mock.patch.object(os,'scandir',side_effect=lambda _:Stream()):
            code,report=self.cli()
        self.assertEqual((code,report['status']),(2,'ERROR'))
        self.assertEqual(len(consumed),4)

    def test_exact_entry_budget_includes_excluded_directory(self):
        folder=self.root/'private'
        folder.mkdir()
        (folder/'ignored.json').write_bytes(b'{fictional')
        (self.root/'target.txt').write_bytes(b'fictional')
        with mock.patch.object(m,'MAX_FILES',3):
            report=m.check(self.root)
        self.assertEqual((report['status'],report['checked_documents']),('PASS',1))

    def test_check_writes_no_files_and_preserves_input_bytes(self):
        before={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(self.cli()[0],0)
        after={path.relative_to(self.root).as_posix():path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        self.assertEqual(before,after)

    def test_directory_rename_is_blocked_or_detected(self):
        moved=[]
        try:
            with m._directory_entries(self.root,100):
                try:self.root.rename(self.base/'renamed')
                except OSError:pass
                else:moved.append(True)
        except (OSError,m.DocsError):
            self.assertTrue(moved)
        else:self.assertFalse(moved,'Directory change was neither blocked nor detected')

    def test_hardlinked_documents_remain_separate_names(self):
        self.hardlink(self.root/'second.md',self.file)
        report=m.check(self.root)
        self.assertEqual((report['status'],report['checked_documents']),('PASS',2))

    def test_filenames_remain_private_report_metadata(self):
        self.file.rename(self.root/'fictional-identifier.md')
        (self.root/'fictional-identifier.md').write_text('[x](absent.txt)',encoding='utf-8')
        code,report=self.cli()
        self.assertEqual(code,1)
        self.assertIn('fictional-identifier.md',json.dumps(report))

    @unittest.skipIf(os.name=='nt','Non-Windows API rejection')
    def test_linux_cannot_initialize_native_api(self):
        with self.assertRaises(m.DocsError):w.Native({'Rejected':m.DocsError,'EntryFailure':m.DocsError})

    @unittest.skipIf(os.name=='nt','POSIX symlink fixture')
    def test_posix_symlink_sources_targets_and_root_are_refused(self):
        outside=self.base/'outside.txt'
        outside.write_bytes(b'fictional outside')
        (self.root/'linked.md').symlink_to(outside)
        (self.root/'linked.txt').symlink_to(outside)
        self.file.write_text('[x](linked.txt)',encoding='utf-8')
        self.assertEqual({row['rule'] for row in m.check(self.root)['findings']},{'LINK_OR_REPARSE','MISSING_OR_LINKED_TARGET'})
        alias=self.base/'root-link'
        alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(m.DocsError):m.check(alias)

    @unittest.skipIf(os.name=='nt','POSIX FIFO fixture')
    def test_posix_fifo_source_refused_and_target_only_checked_for_existence(self):
        os.mkfifo(self.root/'pipe.md')
        os.mkfifo(self.root/'target.fifo')
        self.file.write_text('[x](target.fifo)',encoding='utf-8')
        report=m.check(self.root)
        self.assertEqual(report['findings'],[dict(path='pipe.md',rule='SIZE_OR_TYPE')])

    @unittest.skipIf(os.name=='nt','POSIX no-follow fixture')
    def test_posix_leaf_replacement_link_is_refused_before_open(self):
        expected=self.file.lstat()
        self.file.unlink()
        outside=self.base/'outside.txt'
        outside.write_bytes(b'fictional outside')
        self.file.symlink_to(outside)
        with mock.patch.object(os,'open',side_effect=AssertionError('LINK_OPENED')),self.assertRaises(m.DocsError):
            m._read_text(self.file,expected)

    @unittest.skipIf(os.name=='nt','POSIX interruption behavior')
    def test_posix_interruption_is_reraised(self):
        with mock.patch.object(m,'_read_text',side_effect=KeyboardInterrupt),self.assertRaises(KeyboardInterrupt):self.cli()


@unittest.skipUnless(os.name=='nt','Native Windows fixture')
class NativeWindowsDocs(Fixture):
    def test_invalid_root_spellings_stop_before_native_access(self):
        values=['',r'C:relative',r'\fictional',r'\\fictional\share',r'\\?\C:\fictional',
                '//?/C:/fictional',r'C:\a\..\b',r'C:\NUL.txt',r'C:\file:stream',
                r'C:\trailing.',r'C:\trailing ','C:\\bad\ud800',b'not text',None]
        with mock.patch.object(w,'Native',side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:
                with self.subTest(value=repr(value)),self.assertRaises(m.DocsError):m.check(value)

    def test_nonlocal_drive_type_stops_before_native_open(self):
        native=w.Native({'Rejected':m.DocsError,'EntryFailure':m.DocsError})
        with mock.patch.object(native.dll,'GetDriveTypeW',return_value=4),mock.patch.object(native.dll,'CreateFileW',side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(m.DocsError):native.open(Path(self.root.anchor),True)

    def test_filesystem_root_is_refused_before_open(self):
        with mock.patch.object(w,'Native',side_effect=AssertionError('ROOT_SCAN_STARTED')),self.assertRaises(m.DocsError):
            m.check(self.root.anchor)

    def test_read_descriptor_is_binary_noninheritable_and_held(self):
        before=self.file.read_bytes()
        with w.regular(self.file,m.DocsError) as fd:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd,100),before)
            with self.assertRaises(OSError):self.file.rename(self.root/'blocked.md')
        self.file.rename(self.root/'closed.md')

    def test_replacement_before_open_refuses_old_identity(self):
        expected=self.file.lstat()
        self.file.rename(self.root/'retained.bin')
        self.file.write_bytes(b'# Fictional\n')
        with self.assertRaises(m.DocsError):m._read_text(self.file,expected)
        self.assertEqual((self.root/'retained.bin').read_bytes(),b'# Fictional\n')

    def test_symlink_document_requires_review_without_target_reads(self):
        target=self.base/'outside.txt'
        target.write_bytes(b'fictional outside bytes')
        self.file.unlink()
        self.symlink(self.file,target)
        with mock.patch.object(m,'_read_text',side_effect=AssertionError('LINK_TARGET_READ')):
            report=m.check(self.root)
        self.assertEqual(report['findings'],[dict(path='example.md',rule='LINK_OR_REPARSE')])
        self.assertEqual(report['checked_documents'],0)

    def test_symlink_root_and_local_target_are_refused(self):
        alias=self.base/'root-link'
        self.symlink(alias,self.root,True)
        with self.assertRaises(m.DocsError):m.check(alias)
        outside=self.base/'outside.txt'
        outside.write_bytes(b'fictional outside')
        self.symlink(self.root/'target.bin',outside)
        self.file.write_text('[x](target.bin)',encoding='utf-8')
        report=m.check(self.root)
        self.assertIn('MISSING_OR_LINKED_TARGET',[row['rule'] for row in report['findings']])

    def test_symlink_target_ancestor_is_not_followed(self):
        outside=self.base/'outside'
        outside.mkdir()
        (outside/'target.bin').write_bytes(b'fictional outside')
        self.symlink(self.root/'linked',outside,True)
        self.file.write_text('[x](linked/target.bin)',encoding='utf-8')
        report=m.check(self.root)
        self.assertEqual({row['rule'] for row in report['findings']},{'LINK_OR_REPARSE','MISSING_OR_LINKED_TARGET'})

    def test_symlink_root_git_metadata_is_flagged_before_exclusion(self):
        outside=self.base/'outside'
        outside.mkdir()
        self.symlink(self.root/'.git',outside,True)
        self.assertEqual(m.check(self.root)['findings'],[dict(path='.git',rule='LINK_OR_REPARSE')])

    def test_junction_root_is_refused(self):
        alias=self.base/'root-junction'
        self.junction(alias,self.root)
        with self.assertRaises(m.DocsError):m.check(alias)

    def test_junction_entry_and_link_target_are_not_followed(self):
        outside=self.base/'outside'
        outside.mkdir()
        (outside/'target.bin').write_bytes(b'fictional outside')
        self.junction(self.root/'linked',outside)
        self.file.write_text('[x](linked/target.bin)',encoding='utf-8')
        report=m.check(self.root)
        self.assertEqual({row['rule'] for row in report['findings']},{'LINK_OR_REPARSE','MISSING_OR_LINKED_TARGET'})
        self.assertEqual(report['checked_documents'],1)

    def test_hardlinked_local_target_is_checked_without_reading_data(self):
        target=self.root/'target.bin'
        target.write_bytes(b'fictional bytes')
        alias=self.root/'alias.bin'
        self.hardlink(alias,target)
        with mock.patch.object(os,'read',side_effect=AssertionError('TARGET_DATA_READ')):
            w.check_target(alias,self.root,m.DocsError)
        self.assertEqual(target.read_bytes(),b'fictional bytes')

    def test_local_target_requests_attributes_without_stream_reads(self):
        target=self.root/'target.bin'
        target.write_bytes(b'fictional bytes')
        original=w.Native.open
        observed=[]
        def probe(native,path,directory,expected=None,**kwargs):
            if path==target:
                observed.append(kwargs.get('attributes_only'))
            return original(native,path,directory,expected,**kwargs)
        with mock.patch.object(w.Native,'open',new=probe),mock.patch.object(os,'read',side_effect=AssertionError('TARGET_DATA_READ')):
            w.check_target(target,self.root,m.DocsError)
        self.assertEqual(observed,[True])

    def test_observed_native_target_outside_selected_root_is_refused(self):
        original=w.Native.open
        def outside(native,path,directory,expected=None,**kwargs):
            handle,identity,final=original(native,path,directory,expected,**kwargs)
            if path==self.file and kwargs.get('attributes_only'):
                final=r'\Device\HarddiskVolume999\fictional-target'
            return handle,identity,final
        with mock.patch.object(w.Native,'open',new=outside),self.assertRaises(m.DocsError):
            w.check_target(self.file,self.root,m.DocsError)
        self.file.rename(self.root/'closed.md')

    def test_ads_link_argument_is_refused_without_reading_stream(self):
        target=self.root/'target.bin'
        target.write_bytes(b'fictional ordinary bytes')
        stream=Path(str(target)+':fictional')
        stream.write_bytes(b'fictional stream bytes')
        self.file.write_text('[x](target.bin%3Afictional)',encoding='utf-8')
        report=m.check(self.root)
        self.assertEqual(report['findings'],[dict(path='example.md',line=1,rule='MISSING_OR_LINKED_TARGET')])
        self.assertEqual(stream.read_bytes(),b'fictional stream bytes')

    def test_named_document_stream_remains_outside_scan(self):
        stream=Path(str(self.file)+':fictional')
        stream.write_bytes(b'[x](fictional-missing.txt)')
        self.assertEqual(m.check(self.root)['status'],'PASS')
        self.assertEqual(stream.read_bytes(),b'[x](fictional-missing.txt)')

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method=ctypes.WinDLL('kernel32',use_last_error=True).GetShortPathNameW
        method.argtypes,method.restype=[wintypes.LPCWSTR,wintypes.LPWSTR,wintypes.DWORD],wintypes.DWORD
        folder=self.base/'fictional long directory'
        folder.mkdir()
        buffer=ctypes.create_unicode_buffer(32768)
        size=method(str(folder),buffer,len(buffer))
        if not size or buffer.value.casefold()==str(folder).casefold():self.skipTest('Optional short-name alias unavailable')
        with self.assertRaises(m.DocsError):m.check(buffer.value)

    def test_interruption_is_generic_and_closes_input_handles(self):
        with mock.patch.object(os,'read',side_effect=KeyboardInterrupt):code,report=self.cli()
        self.assertEqual((code,report),(130,dict(status='ERROR',code='DOCUMENTATION_CHECK_INTERRUPTED')))
        self.file.rename(self.root/'closed.md')

    def test_static_help_and_argument_errors_omit_private_values(self):
        output=io.StringIO()
        with redirect_stdout(output):self.assertEqual(m.main(['--unknown','FICTIONAL_ARGUMENT_DETAIL']),2)
        self.assertNotIn('FICTIONAL_ARGUMENT_DETAIL',output.getvalue())
        output=io.StringIO()
        with mock.patch.object(sys,'argv',['FICTIONAL_PROGRAM_DETAIL']),redirect_stdout(output),self.assertRaises(SystemExit):m.main(['--help'])
        self.assertIn('usage: docs_check.py',output.getvalue())
        self.assertNotIn('FICTIONAL_PROGRAM_DETAIL',output.getvalue())


if __name__=='__main__':unittest.main()
