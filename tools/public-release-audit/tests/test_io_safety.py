"""Invented stable exports/markers and disposable failure fixtures only."""
from contextlib import redirect_stdout
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

MODULE = Path(__file__).resolve().parents[1] / 'release_audit.py'
SPEC = importlib.util.spec_from_file_location('public_audit_io_fixture', MODULE)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
w = r._windows()


class Fixture(unittest.TestCase):
    def setUp(self):
        parent = Path(os.environ.get('OUTLANDS_TEST_TEMP', tempfile.gettempdir())).resolve()
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-audit-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'export'
        self.root.mkdir()
        self.file = self.root / 'example.txt'
        self.file.write_bytes(b'Fictional source text.\n')
        self.control = self.base / 'markers.json'
        self.control.write_text('["fictional-hold"]', encoding='utf-8')
        self.output = self.base / 'report.json'

    def main(self, *extra):
        out = io.StringIO()
        with redirect_stdout(out):
            status = r.main(['--root', str(self.root), *extra])
        return status, json.loads(out.getvalue())

    def feature_failure(self, error, name):
        if os.environ.get('OUTLANDS_AUDIT_REQUIRE_LINKS') == '1':
            raise error
        self.skipTest('Native ' + name + ' creation unavailable in this environment')

    def symlink(self, path, target, directory=False):
        try:
            path.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            self.feature_failure(error, 'symlink')

    def hardlink(self, path, target):
        try:
            os.link(target, path)
        except OSError as error:
            self.feature_failure(error, 'hardlink')

    def junction(self, path, target):
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(path), str(target)], capture_output=True, timeout=10)
        if result.returncode:
            self.feature_failure(RuntimeError('Fictional junction creation failed'), 'junction')
        self.assertTrue(path.is_junction())
        self.addCleanup(lambda: os.rmdir(path) if path.is_junction() else None)


class PortableIOTests(Fixture):
    def test_control_bytes_and_json_semantics_are_preserved(self):
        raw = self.control.read_bytes()
        self.assertEqual(r.read_json(self.control), ['fictional-hold'])
        self.assertEqual(self.control.read_bytes(), raw)

    def test_control_read_limit_precedes_descriptor_read(self):
        with mock.patch.object(r, 'MAX_JSON', 2), mock.patch.object(r.os, 'read', side_effect=AssertionError('OVERSIZED_READ')):
            with self.assertRaises(r.AuditError):
                r.read_json(self.control)

    def test_control_growth_cannot_exceed_read_budget(self):
        self.control.write_bytes(b'["fictional"]')
        original = os.read
        changed, requests = [], []
        def grow(fd, amount):
            requests.append(amount)
            block = original(fd, amount)
            if block and not changed:
                with self.control.open('ab') as handle:
                    handle.write(b' ' * 100)
                changed.append(True)
            return block
        with mock.patch.object(r, 'MAX_JSON', 16), mock.patch.object(r.os, 'read', side_effect=grow):
            with self.assertRaises(r.AuditError):
                r.read_json(self.control)
        self.assertTrue(changed)
        self.assertTrue(all(0 < amount <= 17 for amount in requests))

    def test_same_size_control_mutation_fails(self):
        self.control.write_bytes(b'["aaa"]')
        original = os.read
        changed = []
        def mutate(fd, amount):
            block = original(fd, amount)
            if block and not changed:
                before = self.control.stat().st_mtime_ns
                self.control.write_bytes(b'["bbb"]')
                os.utime(self.control, ns=(before, before + 1_000_000))
                changed.append(True)
            return block
        with mock.patch.object(r.os, 'read', side_effect=mutate), self.assertRaises(r.AuditError):
            r.read_json(self.control)

    def test_directory_control_is_refused(self):
        with self.assertRaises((r.AuditError, OSError)):
            r.read_json(self.root)

    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'mkfifo'), 'POSIX FIFO fixture')
    def test_posix_fifo_control_is_refused_before_open(self):
        fifo = self.base / 'control-fifo'
        os.mkfifo(fifo)
        with mock.patch.object(r.os, 'open', side_effect=AssertionError('FIFO_OPENED')), self.assertRaises(r.AuditError):
            r.read_json(fifo)

    @unittest.skipUnless(os.name == 'posix', 'POSIX no-follow control fixture')
    def test_posix_symlink_control_is_refused(self):
        link = self.base / 'linked.json'
        link.symlink_to(self.control)
        with self.assertRaises(r.AuditError):
            r.read_json(link)

    @unittest.skipUnless(os.name == 'posix', 'Non-Windows API rejection')
    def test_linux_rejects_native_api_initialization(self):
        with self.assertRaisesRegex(r.AuditError, '^WINDOWS_API_UNAVAILABLE$'):
            w.Native({'Rejected': r.AuditError, 'EntryFailure': r.AuditError})

    def test_bad_json_and_marker_schema_do_not_echo_inputs(self):
        for value in ('not JSON FICTIONAL_MARKER_CANARY', '{"fictional":true}', '[2]', '["x"]'):
            self.control.write_text(value, encoding='utf-8')
            status, summary = self.main('--deny-file', str(self.control))
            self.assertEqual((status, summary), (2, {'status': 'ERROR', 'code': 'AUDIT_INPUT_OR_OUTPUT_ERROR'}))

    def test_report_rendering_matches_existing_json_format(self):
        data = {'fictional': ['\u03bb', 1, True], 'value': None}
        self.assertEqual(r._report_bytes(data), (json.dumps(data, indent=2) + '\n').encode('utf-8'))

    def test_report_encoder_rejects_excess_before_any_write(self):
        with mock.patch.object(r, 'MAX_REPORT', 8), self.assertRaises(r.AuditError):
            r._report_bytes({'fictional': 'too much for this fixture'})
        self.assertFalse(self.output.exists())

    def test_private_marker_values_do_not_appear_in_finding_payloads(self):
        marker = 'fictional-hold'
        self.file.write_text('Neutral line\n' + marker + '\n', encoding='utf-8')
        status, summary = self.main('--deny-file', str(self.control), '--report', str(self.output))
        self.assertEqual(status, 1)
        self.assertEqual(summary['findings'], {'PRIVATE_LITERAL': 1})
        report = self.output.read_text(encoding='utf-8')
        self.assertNotIn(marker, report)
        self.assertNotIn(str(self.base), report)
        self.assertEqual(json.loads(report)['findings'], [{'path': 'example.txt', 'rule': 'PRIVATE_LITERAL', 'line': 2}])

    def test_original_detector_examples_and_filename_rules_remain(self):
        text = '\n'.join(['reviewer@example.com', '127.0.0.1 192.0.2.3 2001:db8::1',
                          'person' + '@' + 'fictional.invalid', 'https://' + 'name:fictional' + '@example.com/'])
        self.assertEqual(r.inspect_text(text), [('EMAIL', 3), ('URL_CREDENTIALS', 4)])
        self.file.unlink()
        (self.root / '.env').write_text('fictional excluded bytes')
        (self.root / 'runtime').mkdir()
        result = r.inspect(self.root)
        self.assertEqual({row['rule'] for row in result['findings']}, {'SENSITIVE_FILENAME', 'PRIVATE_OR_RUNTIME_DIRECTORY'})

    def test_filename_markers_remain_private_report_metadata(self):
        self.file.rename(self.root / 'fictional-hold.md')
        status, summary = self.main('--deny-file', str(self.control), '--report', str(self.output))
        self.assertEqual(status, 1)
        self.assertEqual(summary['findings'], {'PATH_PRIVATE_LITERAL': 1})
        self.assertNotIn('fictional-hold', json.dumps(summary))
        self.assertIn('fictional-hold.md', self.output.read_text(encoding='utf-8'))

    def test_manifest_generation_withholds_approval_after_findings(self):
        self.file.write_text('fictional-hold', encoding='utf-8')
        status, _ = self.main('--deny-file', str(self.control), '--write-manifest', str(self.output))
        self.assertEqual(status, 2)
        self.assertFalse(self.output.exists())


@unittest.skipUnless(os.name == 'nt', 'Native Windows I/O fixture')
class NativeWindowsIOTests(Fixture):
    def test_raw_invalid_paths_stop_before_native_access(self):
        values = ['', r'C:relative', r'\fictional', r'\\fictional\share', r'\\?\C:\fictional',
                  '//?/C:/fictional', r'C:\a\..\b', r'C:\NUL.txt', r'C:\file:stream',
                  r'C:\trailing.', r'C:\trailing ', 'C:\\bad\ud800', b'not text', None]
        with mock.patch.object(w, 'Native', side_effect=AssertionError('NATIVE_BEFORE_VALIDATION')):
            for value in values:
                with self.subTest(value=repr(value)), self.assertRaises(r.AuditError):
                    w.checked_path(value, r.AuditError)

    def test_nonlocal_drive_type_stops_before_open(self):
        native = w.Native({'Rejected': r.AuditError, 'EntryFailure': r.AuditError})
        with mock.patch.object(native.dll, 'GetDriveTypeW', return_value=4), mock.patch.object(native.dll, 'CreateFileW', side_effect=AssertionError('REMOTE_OPENED')):
            with self.assertRaises(r.AuditError):
                native.open(Path(self.root.anchor), True)

    def test_root_filesystem_scan_is_refused(self):
        with mock.patch.object(w, 'Native', side_effect=AssertionError('ROOT_SCAN_STARTED')), self.assertRaises(r.AuditError):
            r.inspect(self.root.anchor)

    def test_native_regular_descriptor_is_binary_noninheritable_and_kept(self):
        with w.regular(self.file, r.AuditError) as fd:
            self.assertFalse(os.get_inheritable(fd))
            self.assertEqual(os.read(fd, 100), self.file.read_bytes())
            with self.assertRaises(OSError):
                self.file.rename(self.root / 'renamed.txt')
        self.file.rename(self.root / 'renamed.txt')

    def test_hardlinked_export_names_remain_selected(self):
        self.hardlink(self.root / 'other.txt', self.file)
        result = r.inspect(self.root)
        self.assertEqual(result['status'], 'NO_PATTERN_FINDINGS')
        self.assertEqual(len(result['inventory']), 2)
        self.assertEqual(result['inventory'][0]['sha256'], result['inventory'][1]['sha256'])

    def test_hardlinked_controls_are_refused(self):
        link = self.base / 'markers-link.json'
        self.hardlink(link, self.control)
        with self.assertRaisesRegex(r.AuditError, '^CONTROL_NOT_SINGLE_LINK$'):
            r.read_json(self.control)
        with self.assertRaises(r.AuditError):
            r.read_json(link)

    def test_hardlinked_existing_report_is_not_replaced(self):
        self.hardlink(self.output, self.control)
        before = self.control.read_bytes()
        with self.assertRaises(FileExistsError):
            r.write_new(self.output, {}, self.root)
        self.assertEqual(self.control.read_bytes(), before)

    def test_symlink_entries_require_review_without_target_reads(self):
        target = self.base / 'outside.txt'
        target.write_bytes(b'fictional target outside export')
        self.symlink(self.root / 'linked.txt', target)
        result = r.inspect(self.root)
        self.assertEqual(result['findings'], [{'path': 'linked.txt', 'rule': 'LINK_OR_REPARSE', 'line': None}])
        self.assertEqual(len(result['inventory']), 1)

    def test_symlink_root_and_control_are_refused(self):
        link = self.base / 'linked-root'
        self.symlink(link, self.root, True)
        with self.assertRaises(r.AuditError):
            r.inspect(link)
        control = self.base / 'linked-control.json'
        self.symlink(control, self.control)
        with self.assertRaises(r.AuditError):
            r.read_json(control)

    def test_symlink_report_is_not_replaced(self):
        self.symlink(self.output, self.control)
        before = self.control.read_bytes()
        with self.assertRaises(FileExistsError):
            r.write_new(self.output, {}, self.root)
        self.assertEqual(self.control.read_bytes(), before)

    def test_junction_entry_requires_review_without_target_descent(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'example.txt').write_bytes(b'fictional outside bytes')
        self.junction(self.root / 'linked', outside)
        result = r.inspect(self.root)
        self.assertEqual(result['findings'], [{'path': 'linked', 'rule': 'LINK_OR_REPARSE', 'line': None}])
        self.assertEqual(len(result['inventory']), 1)

    def test_junction_root_and_report_ancestor_are_refused(self):
        link = self.base / 'root-link'
        self.junction(link, self.root)
        with self.assertRaises(r.AuditError):
            r.inspect(link)
        with self.assertRaises(r.AuditError):
            r.write_new(link / 'new.json', {}, self.root)
        self.assertFalse((self.root / 'new.json').exists())

    def test_report_overlap_is_rejected_using_native_name(self):
        with mock.patch.object(w, 'exclusive_write', side_effect=AssertionError('INSIDE_REPORT_CREATED')):
            with self.assertRaisesRegex(r.AuditError, '^REPORT_MUST_BE_OUTSIDE_ROOT$'):
                r.write_new(str(self.root).upper() + '\\new.json', {}, self.root)
        self.assertFalse((self.root / 'new.json').exists())

    def test_directory_enumeration_stops_at_budget_plus_one(self):
        seen = []
        class Entry:
            name = 'fictional.txt'
        class Entries:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self):
                for number in range(100):
                    seen.append(number)
                    yield Entry()
        with mock.patch.object(w.os, 'scandir', return_value=Entries()), mock.patch.object(r, 'MAX_FILES', 2):
            result = r.inspect(self.root)
        self.assertEqual(len(seen), 3)
        self.assertEqual(result['errors'], ['ENTRY_LIMIT'])
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')

    def test_aggregate_reads_stop_before_excess_bytes_are_hashed(self):
        self.file.write_bytes(b'ab')
        original = w.os.read
        requests = []
        def grow(fd, amount):
            requests.append(amount)
            block = original(fd, amount)
            if block and len(requests) == 1:
                with self.file.open('ab') as stream:
                    stream.write(b'cdef')
            return block
        with mock.patch.object(r, 'MAX_TOTAL', 2), mock.patch.object(w.os, 'read', side_effect=grow):
            result = r.inspect(self.root)
        self.assertEqual(result['inventory'], [])
        self.assertEqual(result['errors'], ['BYTE_LIMIT'])
        self.assertEqual(result['scope']['bytes_read'], 3)
        self.assertTrue(all(amount <= 3 for amount in requests))

    def test_file_replacement_before_read_requires_review(self):
        replacement = self.base / 'replacement.txt'
        replacement.write_bytes(b'Fictional replacement.\n')
        original = w.read_bounded
        def replace(value, *args, **kwargs):
            os.replace(replacement, value)
            return original(value, *args, **kwargs)
        with mock.patch.object(w, 'read_bounded', side_effect=replace):
            result = r.inspect(self.root)
        self.assertEqual(result['inventory'], [])
        self.assertEqual(result['findings'], [{'path': 'example.txt', 'rule': 'INPUT_CHANGED', 'line': None}])

    def test_read_error_does_not_echo_exception_or_clear_review(self):
        with mock.patch.object(w.os, 'open', side_effect=OSError('FICTIONAL_READ_DETAIL')):
            status, summary = self.main()
        self.assertEqual(status, 1)
        self.assertEqual(summary['errors'], ['ENTRY_READ_FAILED'])
        self.assertNotIn('FICTIONAL_READ_DETAIL', json.dumps(summary))

    def test_report_short_writes_preserve_exact_encoding(self):
        original = w.os.write
        with mock.patch.object(w.os, 'write', side_effect=lambda fd, data: original(fd, data[:3])):
            r.write_new(self.output, {'fictional': True}, self.root)
        self.assertEqual(self.output.read_bytes(), r._report_bytes({'fictional': True}))

    def test_zero_write_retains_empty_output_and_returns_error(self):
        with mock.patch.object(w.os, 'write', return_value=0):
            status, summary = self.main('--report', str(self.output))
        self.assertEqual(status, 2)
        self.assertEqual(summary['status'], 'ERROR')
        self.assertEqual(self.output.read_bytes(), b'')
        self.output.rename(self.base / 'closed-after-error.json')

    def test_late_flush_failure_retains_unconfirmed_complete_report(self):
        with mock.patch.object(w.os, 'fsync', side_effect=OSError('FICTIONAL_FLUSH_DETAIL')):
            status, summary = self.main('--report', str(self.output))
        self.assertEqual(status, 2)
        self.assertEqual(summary['status'], 'ERROR')
        self.assertEqual(json.loads(self.output.read_text())['status'], 'NO_PATTERN_FINDINGS')
        self.assertNotIn('FICTIONAL_FLUSH_DETAIL', json.dumps(summary))

    def test_report_limit_is_checked_before_file_creation(self):
        with mock.patch.object(r, 'MAX_REPORT', 2), mock.patch.object(w, 'exclusive_write', side_effect=AssertionError('CREATED_AFTER_LIMIT')):
            status, _ = self.main('--report', str(self.output))
        self.assertEqual(status, 2)
        self.assertFalse(self.output.exists())

    def test_interruption_is_generic_and_closes_created_file(self):
        with mock.patch.object(w.os, 'write', side_effect=KeyboardInterrupt):
            status, summary = self.main('--report', str(self.output))
        self.assertEqual((status, summary), (130, {'status': 'ERROR', 'code': 'AUDIT_INTERRUPTED'}))
        self.output.rename(self.base / 'closed-after-interruption.json')

    def test_named_streams_remain_outside_the_selected_inventory(self):
        Path(str(self.file) + ':fictional').write_bytes(b'fictional omitted stream')
        result = r.inspect(self.root)
        self.assertEqual(result['status'], 'NO_PATTERN_FINDINGS')
        self.assertEqual(result['inventory'][0]['size'], len(self.file.read_bytes()))
        self.assertEqual(result['inventory'][0]['sha256'], hashlib.sha256(self.file.read_bytes()).hexdigest())

    def test_short_name_alias_is_refused_when_available(self):
        import ctypes
        from ctypes import wintypes
        method = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
        method.argtypes, method.restype = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD], wintypes.DWORD
        target = self.root / 'fictional long directory'
        target.mkdir()
        buffer = ctypes.create_unicode_buffer(32768)
        length = method(str(target), buffer, len(buffer))
        if not length or buffer.value.casefold() == str(target).casefold():
            self.skipTest('Optional short-name alias unavailable')
        with self.assertRaises(r.AuditError):
            r.inspect(buffer.value)

    def test_static_help_and_argument_errors_omit_private_values(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(r.main(['--unknown', 'FICTIONAL_ARGUMENT_DETAIL']), 2)
        self.assertNotIn('FICTIONAL_ARGUMENT_DETAIL', out.getvalue())
        out = io.StringIO()
        with mock.patch.object(sys, 'argv', ['FICTIONAL_PROGRAM_DETAIL']), redirect_stdout(out), self.assertRaises(SystemExit):
            r.main(['--help'])
        self.assertIn('usage: release_audit.py', out.getvalue())
        self.assertNotIn('FICTIONAL_PROGRAM_DETAIL', out.getvalue())


if __name__ == '__main__':
    unittest.main()
