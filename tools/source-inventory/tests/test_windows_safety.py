"""Generated private trees only; native Windows cases never inspect real inputs."""
from contextlib import redirect_stdout
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import source_inventory as s
import classify_inventory as classifier
w = s._windows()


class PortableWindowsContract(unittest.TestCase):
    def test_ambiguous_component_spellings_are_rejected(self):
        for name in ('', '.', '..', 'NUL', 'aux.txt', 'CONIN$', 'com1.bin', 'LPT\u00b2',
                     'last.', 'last ', 'a:b', 'a/b', 'a\\b', 'a\x00b', 'a\nb', 'a?b', 'x' * 256):
            with self.subTest(name=repr(name)):
                self.assertFalse(w._component(name))
        for name in ('fictional.txt', 'unicode-\u03bb', '=fictional', "'quoted", 'com10', 'lpt0', 'inside\u202ename'):
            self.assertTrue(w._component(name))

    def test_native_keys_obey_component_boundaries_and_case(self):
        self.assertTrue(w._inside(r'\Device\HarddiskVolume1\Input\Child', r'\device\harddiskvolume1\input'))
        self.assertTrue(w._inside(r'\Device\HarddiskVolume1\Input', '\\Device\\HarddiskVolume1\\Input\\'))
        self.assertFalse(w._inside(r'\Device\HarddiskVolume1\Input-other', r'\Device\HarddiskVolume1\Input'))
        self.assertFalse(w._inside(r'\Device\HarddiskVolume2\Input', r'\Device\HarddiskVolume1\Input'))

    @unittest.skipIf(os.name == 'nt', 'Non-Windows native API rejection')
    def test_linux_cannot_initialize_native_api(self):
        with self.assertRaisesRegex(s.InventoryError, '^WINDOWS_API_UNAVAILABLE$'):
            w.Native({'Rejected': s.InventoryError, 'EntryFailure': s.InventoryError})


@unittest.skipUnless(os.name == 'nt', 'Native Windows filesystem fixture')
class NativeWindowsInventory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-inventory-windows-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source, self.output = self.base / 'input', self.base / 'reports'
        self.source.mkdir()
        self.output.mkdir()
        self.file = self.source / 'fictional.txt'
        self.file.write_bytes(b'fictional base bytes')

    def snapshot(self, **options):
        return s.snapshot(self.source, self.output, 'demo', **options)

    def failure(self, operation):
        with self.assertRaises((s.InventoryError, OSError)):
            operation()
        self.assertEqual(list(self.output.iterdir()), [])

    def cli(self, **options):
        args = ['--root', str(options.get('source', self.source)), '--output-dir', str(options.get('output', self.output)), '--label', 'demo']
        capture = io.StringIO()
        with redirect_stdout(capture):
            status = s.main(args)
        return status, json.loads(capture.getvalue())

    def link(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if getattr(error, 'winerror', None) == 1314 and os.environ.get('OUTLANDS_INVENTORY_REQUIRE_LINKS') != '1':
                self.skipTest('Native symlink privilege unavailable')
            raise

    def junction(self, path, target):
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(path), str(target)], capture_output=True, timeout=10)
        if result.returncode != 0 and os.environ.get('OUTLANDS_INVENTORY_REQUIRE_LINKS') != '1':
            self.skipTest('Native junction creation unavailable in this environment')
        self.assertEqual(result.returncode, 0, 'Generated junction creation failed')
        self.assertTrue(path.is_junction())
        # Remove only the link, never recurse into its target.
        self.addCleanup(lambda: os.rmdir(path) if path.is_junction() else None)

    def hardlink(self, path, target):
        try:
            os.link(target, path)
        except OSError:
            if os.environ.get('OUTLANDS_INVENTORY_REQUIRE_LINKS') != '1':
                self.skipTest('Native hardlink creation unavailable in this environment')
            raise

    def test_raw_paths_are_refused_before_native_access(self):
        values = ['', r'C:relative', r'\root-relative', r'\\fictional\share', r'\\?\C:\fictional',
                  '//?/C:/fictional', '//./C:/fictional', r'C:\parent\..\other', r'C:\NUL.txt',
                  r'C:\trailing.', r'C:\trailing ', r'C:\file:stream', 'C:\\bad\x00name',
                  'C:\\' + '\\'.join(['level'] * 65), 'C:\\' + 'x' * 256, 'C:\\' + 'x' * 4096,
                  'C:\\bad\ud800', b'not-text', None]
        with mock.patch.object(w, 'Native', side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:
                with self.subTest(value=repr(value)), self.assertRaises(s.InventoryError):
                    w.checked_directory(value, s.InventoryError)

    def test_raw_cli_parent_traversal_is_not_normalized_away(self):
        status, report = self.cli(source=str(self.source) + '\\..\\input')
        self.assertEqual((status, report), (2, {'result': 'INCOMPLETE', 'error': 'PATH_INVALID'}))
        self.assertEqual(list(self.output.iterdir()), [])

    def test_nonlocal_drive_type_is_refused_before_opening_root(self):
        native = w.Native({'Rejected': s.InventoryError, 'EntryFailure': s.InventoryError})
        for kind in (0, 1, 4, 5, 6):
            with self.subTest(kind=kind), mock.patch.object(native.dll, 'GetDriveTypeW', return_value=kind), mock.patch.object(native.dll, 'CreateFileW', side_effect=AssertionError('REMOTE_ROOT_OPENED')):
                with self.assertRaisesRegex(s.InventoryError, '^LOCAL_VOLUME_REQUIRED$'):
                    native.open(Path(self.source.anchor), True)

    def test_relative_input_paths_remain_supported(self):
        previous = os.getcwd()
        try:
            os.chdir(self.base)
            run, summary = s.snapshot('input', 'reports', 'relative')
        finally:
            os.chdir(previous)
        self.assertTrue(run.is_absolute())
        self.assertEqual(summary['file_count'], 1)

    def test_case_variation_does_not_change_selected_bytes(self):
        run, summary = s.snapshot(str(self.source).upper(), self.output, 'case')
        with (run / 'files.csv').open(newline='', encoding='utf-8') as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row['sha256'], hashlib.sha256(self.file.read_bytes()).hexdigest().upper())
        self.assertEqual(summary['total_bytes'], len(self.file.read_bytes()))

    def test_retained_regular_file_is_binary_noninheritable_and_blocks_rename(self):
        with w.regular(self.file, s.InventoryError) as fd:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd, 4096), b'fictional base bytes')
            with self.assertRaises(OSError):
                self.file.rename(self.source / 'renamed.txt')
        self.file.rename(self.source / 'renamed.txt')

    def test_source_hardlinks_remain_counted_per_selected_name(self):
        other = self.source / 'also-fictional.txt'
        self.hardlink(other, self.file)
        run, summary = self.snapshot()
        self.assertEqual(summary['file_count'], 2)
        with (run / 'files.csv').open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]['sha256'], rows[1]['sha256'])
        self.assertEqual(summary['total_bytes'], 2 * len(self.file.read_bytes()))

    def test_named_streams_are_not_inventoried_or_certified(self):
        Path(str(self.file) + ':fictional').write_bytes(b'fictional omitted stream')
        Path(str(self.source) + ':fictional').write_bytes(b'fictional directory stream')
        run, summary = self.snapshot(tree=True)
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['total_bytes'], len(self.file.read_bytes()))
        with (run / 'files.csv').open(newline='', encoding='utf-8') as stream:
            self.assertEqual(next(csv.DictReader(stream))['sha256'], hashlib.sha256(self.file.read_bytes()).hexdigest().upper())
        self.assertNotIn('omitted stream', (run / 'tree.txt').read_text())

    def test_junction_root_and_output_ancestor_are_refused(self):
        linked = self.base / 'junction'
        self.junction(linked, self.source)
        self.failure(lambda: s.snapshot(linked, self.output, 'demo'))
        parent = self.base / 'report-junction'
        self.junction(parent, self.output)
        self.failure(lambda: s.snapshot(self.source, parent, 'demo'))

    def test_junction_entry_is_skipped_without_target_content_reads(self):
        target = self.base / 'outside'
        target.mkdir()
        (target / 'outside.txt').write_bytes(b'fictional excluded target')
        self.junction(self.source / 'linked', target)
        with mock.patch.object(s, '_sha256', wraps=s._sha256) as hashed:
            run, summary = self.snapshot(tree=True)
        self.assertEqual(summary['skipped']['links'], 1)
        self.assertEqual([call.args[0] for call in hashed.call_args_list], [self.file])
        self.assertNotIn('outside.txt', (run / 'tree.txt').read_text())

    def test_directory_is_held_before_each_one_level_walk(self):
        child = self.source / 'child'
        child.mkdir()
        (child / 'nested.txt').write_bytes(b'fictional nested bytes')
        original = w.os.walk
        visited = []
        def observed(path, **kwargs):
            visited.append(Path(path))
            return original(path, **kwargs)
        with mock.patch.object(w.os, 'walk', side_effect=observed):
            _, summary = self.snapshot(tree=True)
        self.assertEqual(visited, [self.source, child])
        self.assertEqual(summary['file_count'], 2)

    def test_junction_attached_after_parent_yield_is_refused_before_descent(self):
        child = self.source / 'child'
        child.mkdir()
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'outside.txt').write_bytes(b'fictional target bytes')
        walker = w.walk(self.source, topdown=True, followlinks=False, onerror=lambda error: None, error=s.InventoryError)
        self.addCleanup(walker.close)
        current, directories, _ = next(walker)
        self.assertEqual(Path(current), self.source)
        child.rmdir()
        self.junction(child, outside)
        with self.assertRaises(s.InventoryError):
            next(walker)
        walker.close()
        self.assertEqual((outside / 'outside.txt').read_bytes(), b'fictional target bytes')

    def test_symlink_root_and_output_are_refused(self):
        linked = self.base / 'linked-source'
        self.link(linked, self.source, True)
        self.failure(lambda: s.snapshot(linked, self.output, 'demo'))
        linked_output = self.base / 'linked-output'
        self.link(linked_output, self.output, True)
        self.failure(lambda: s.snapshot(self.source, linked_output, 'demo'))

    def test_symlink_entries_are_skipped(self):
        self.link(self.source / 'file-link', self.file)
        _, summary = self.snapshot()
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['skipped']['links'], 1)

    def test_symlink_report_is_never_followed(self):
        link = self.output / 'linked-report'
        self.link(link, self.file)
        before = self.file.read_bytes()
        with self.assertRaises(FileExistsError):
            s._exclusive_write(link, b'fictional replacement')
        self.assertEqual(self.file.read_bytes(), before)

    def test_output_inside_source_is_rejected_by_native_key_before_collection(self):
        child = self.source / 'inside'
        child.mkdir()
        with mock.patch.object(s, '_collect', side_effect=AssertionError('SCAN_BEFORE_BOUNDARY')):
            with self.assertRaisesRegex(s.InventoryError, '^OUTPUT_INSIDE_INPUT$'):
                s.snapshot(self.source, child, 'demo')

    def test_windows_native_name_mismatch_fails_before_read(self):
        original = w.Native.describe
        def renamed(native, handle, directory):
            identity, name = original(native, handle, directory)
            return (identity, name + '-fictional-changed') if not directory else (identity, name)
        with mock.patch.object(w.Native, 'describe', new=renamed), mock.patch.object(w.os, 'read', side_effect=AssertionError('READ_AFTER_NAME_CHANGE')):
            self.failure(self.snapshot)

    def test_open_failure_closes_all_native_handles(self):
        handles = set()
        original_open, original_close = w.Native.open, w.Native.close
        def opened(native, *args, **kwargs):
            result = original_open(native, *args, **kwargs)
            handles.add(result[0])
            return result
        def closed(native, handle):
            try:
                return original_close(native, handle)
            finally:
                handles.discard(handle)
        with mock.patch.object(w.Native, 'open', new=opened), mock.patch.object(w.Native, 'close', new=closed), mock.patch.object(w.os, 'open', side_effect=OSError('FICTIONAL_OPEN_DETAIL')):
            self.failure(self.snapshot)
        self.assertEqual(handles, set())

    def test_short_writes_complete_exact_payload(self):
        target = self.output / 'short-write.txt'
        data = b'fictional bytes ' * 30
        original = w.os.write
        with mock.patch.object(w.os, 'write', side_effect=lambda fd, block: original(fd, block[:3])):
            s._exclusive_write(target, data)
        self.assertEqual(target.read_bytes(), data)

    def test_zero_write_progress_retains_new_file_and_refuses_success(self):
        target = self.output / 'zero-write.txt'
        with mock.patch.object(w.os, 'write', return_value=0):
            with self.assertRaisesRegex(s.InventoryError, '^OUTPUT_IO_ERROR$'):
                s._exclusive_write(target, b'fictional data')
        self.assertEqual(target.read_bytes(), b'')
        target.rename(self.output / 'closed-after-failure.txt')

    def test_write_error_is_private_and_keeps_uncertified_partial_run(self):
        original = w.os.write
        calls = []
        def fail(fd, block):
            if calls:
                raise OSError('FICTIONAL_PRIVATE_WRITE_DETAIL')
            calls.append(True)
            return original(fd, block[:3])
        with mock.patch.object(w.os, 'write', side_effect=fail):
            status, report = self.cli()
        self.assertEqual((status, report['result']), (2, 'INCOMPLETE'))
        runs = list(self.output.iterdir())
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs[0] / 'files.csv').stat().st_size, 3)
        self.assertFalse((runs[0] / 'summary.json').exists())
        self.assertNotIn('FICTIONAL_PRIVATE_WRITE_DETAIL', json.dumps(report))

    def test_flush_failure_keeps_new_output_and_cannot_report_complete(self):
        with mock.patch.object(w.os, 'fsync', side_effect=OSError('FICTIONAL_FLUSH_DETAIL')):
            status, report = self.cli()
        self.assertEqual((status, report['result']), (2, 'INCOMPLETE'))
        run = next(self.output.iterdir())
        self.assertTrue((run / 'files.csv').exists())
        self.assertFalse((run / 'summary.json').exists())

    def test_interruption_closes_new_file_and_reports_no_success(self):
        with mock.patch.object(w.os, 'write', side_effect=KeyboardInterrupt):
            status, report = self.cli()
        self.assertEqual((status, report), (130, {'result': 'INCOMPLETE', 'error': 'INTERRUPTED'}))
        run = next(self.output.iterdir())
        target = run / 'files.csv'
        self.assertEqual(target.read_bytes(), b'')
        target.rename(run / 'closed-after-interruption.csv')
        self.assertFalse((run / 'summary.json').exists())

    def test_new_directory_collision_preserves_existing_payload(self):
        target = self.output / 'existing'
        target.mkdir()
        (target / 'keep.txt').write_bytes(b'fictional retained bytes')
        with self.assertRaisesRegex(s.InventoryError, '^OUTPUT_EXISTS$'):
            with w.new_directory(target, s.InventoryError):
                self.fail('Existing directory accepted')
        self.assertEqual((target / 'keep.txt').read_bytes(), b'fictional retained bytes')

    def test_new_directory_does_not_follow_existing_junction(self):
        target = self.output / 'existing-junction'
        self.junction(target, self.source)
        with self.assertRaisesRegex(s.InventoryError, '^OUTPUT_EXISTS$'):
            with w.new_directory(target, s.InventoryError):
                self.fail('Existing junction accepted')
        self.assertEqual(list(self.source.iterdir()), [self.file])

    def test_existing_hardlinked_report_is_never_replaced(self):
        target = self.output / 'existing.txt'
        self.hardlink(target, self.file)
        before = self.file.read_bytes()
        with self.assertRaises(FileExistsError):
            s._exclusive_write(target, b'fictional replacement')
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(target.read_bytes(), before)

    def test_generated_reports_remain_classifier_compatible_and_inputs_unchanged(self):
        (self.source / 'empty').mkdir()
        (self.source / '=formula.txt').write_bytes(b'fictional formula filename')
        before = {path.name: path.read_bytes() for path in self.source.iterdir() if path.is_file()}
        run, summary = self.snapshot(tree=True, when=datetime(2026, 1, 1, tzinfo=timezone.utc))
        rules = self.base / 'rules.json'
        rules.write_text(json.dumps({'schema_version': 'outlands.path_rules.v1', 'case_sensitive': True, 'rules': [
            {'id': 'fictional', 'category': 'text', 'kind': 'suffix', 'value': '.txt'}]}))
        rows, _ = classifier.parse_inventory((run / 'files.csv').read_bytes(), (run / 'summary.json').read_bytes())
        self.assertEqual(len(rows), summary['file_count'])
        result = classifier.classify(run, rules, self.base / 'classification')
        self.assertEqual(result['file_count'], summary['file_count'])
        self.assertEqual(result['unmatched_files'], 0)
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.source.iterdir() if path.is_file()})
        self.assertEqual(summary['tree']['tree_txt_sha256'], hashlib.sha256((run / 'tree.txt').read_bytes()).hexdigest().upper())

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        get_short = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
        get_short.argtypes, get_short.restype = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD], wintypes.DWORD
        target = self.source / 'fictional long directory name'
        target.mkdir()
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_short(str(target), buffer, len(buffer))
        if not length or buffer.value.casefold() == str(target).casefold():
            self.skipTest('Short-name alias unavailable; separate observed-name fixtures run')
        self.failure(lambda: s.snapshot(buffer.value, self.output, 'alias'))

    def test_help_uses_static_name_and_rejects_private_argument_echo(self):
        for arguments in (['--unknown', 'FICTIONAL_ARGUMENT_DETAIL'], ['--root', str(self.source), '--output-dir', str(self.output), '--label', 'bad label']):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(s.main(arguments), 2)
            self.assertNotIn('FICTIONAL_ARGUMENT_DETAIL', output.getvalue())
            self.assertNotIn(str(self.source), output.getvalue())
        output = io.StringIO()
        with mock.patch.object(sys, 'argv', ['FICTIONAL_PROGRAM_DETAIL']), redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
            s.main(['--help'])
        self.assertEqual(stopped.exception.code, 0)
        self.assertIn('usage: source_inventory.py', output.getvalue())
        self.assertNotIn('FICTIONAL_PROGRAM_DETAIL', output.getvalue())


if __name__ == '__main__':
    unittest.main()
