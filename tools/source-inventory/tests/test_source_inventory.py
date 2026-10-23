"""Fictional temporary trees only; no network or original-project execution."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

STAGED = Path(__file__).resolve().parents[1] / 'source_inventory.py'
SPEC = importlib.util.spec_from_file_location('staged_source_inventory', STAGED)
assert SPEC is not None and SPEC.loader is not None
INVENTORY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INVENTORY)


def setUpModule():
    for target in ('socket.socket', 'socket.create_connection', 'socket.getaddrinfo'):
        patcher = mock.patch(target, side_effect=AssertionError('Network forbidden in fixture tests'))
        patcher.start()
        unittest.addModuleCleanup(patcher.stop)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic-inventory-')
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.source = self.work / 'input'
        self.output = self.work / 'output'
        self.source.mkdir(mode=0o700)
        self.output.mkdir(mode=0o700)

    def file(self, name, data=b'fictional fixture\n'):
        path = self.source / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o600)
        return path

    def snapshot(self, **changes):
        return INVENTORY.snapshot(self.source, self.output, 'fixture', **changes)

    def rows(self, run):
        with (run / 'files.csv').open(encoding='utf-8', newline='') as stream:
            return list(csv.DictReader(stream))

    def assert_code(self, expected, action):
        with self.assertRaises(INVENTORY.InventoryError) as caught:
            action()
        self.assertEqual(str(caught.exception), expected)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_tiny_tree_has_exact_hashes_counts_and_owner_private_outputs(self):
        self.file('top.py', b'a')
        self.file('nested/part.py', b'bc')
        run, summary = self.snapshot()
        rows = self.rows(run)
        self.assertEqual([row['path'] for row in rows], ['nested/part.py', 'top.py'])
        self.assertEqual([row['sha256'] for row in rows], [
            hashlib.sha256(b'bc').hexdigest().upper(), hashlib.sha256(b'a').hexdigest().upper()])
        self.assertEqual(summary['file_count'], 2)
        self.assertEqual(summary['total_bytes'], 3)
        self.assertEqual(summary['files_csv_sha256'], hashlib.sha256((run / 'files.csv').read_bytes()).hexdigest().upper())
        self.assertEqual(stat.S_IMODE(run.stat().st_mode), 0o700)
        for name in ('files.csv', 'summary.json'):
            self.assertEqual(stat.S_IMODE((run / name).stat().st_mode), 0o600)

    def test_repeat_csv_is_deterministic_and_input_bytes_are_unchanged(self):
        paths = [self.file('b.py', b'b'), self.file('A.py', b'A'), self.file('a.py', b'a')]
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        first, _ = self.snapshot()
        second, _ = self.snapshot()
        self.assertEqual((first / 'files.csv').read_bytes(), (second / 'files.csv').read_bytes())
        self.assertEqual([row['path'] for row in self.rows(first)], ['A.py', 'a.py', 'b.py'])
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths})

    def test_empty_selected_tree_has_zero_counts_and_header_only_csv(self):
        run, summary = self.snapshot()
        self.assertEqual(self.rows(run), [])
        self.assertEqual(summary['file_count'], 0)
        self.assertEqual(summary['total_bytes'], 0)
        self.assertEqual(summary['coverage'], 'selected_regular_files_only')

    def test_default_exclusions_are_not_hashed_and_are_counted(self):
        self.file('app.py')
        self.file('.env', b'fictional, no credential')
        self.file('test.key', b'fictional, no key')
        self.file('.git/example', b'fictional metadata')
        self.file('data/example.csv', b'fictional,example')
        original = INVENTORY._sha256
        with mock.patch.object(INVENTORY, '_sha256', wraps=original) as hashed:
            _, summary = self.snapshot()
        self.assertEqual([call.args[0].name for call in hashed.call_args_list], ['app.py'])
        self.assertEqual(summary['skipped']['directories'], 2)
        self.assertEqual(summary['skipped']['files'], 2)

    def test_csv_formula_prefixes_are_escaped_reversibly_and_unicode_newlines_survive(self):
        names = ['=1+1.txt', '+1.txt', '-1.txt', '@name.txt', '\t=1.txt',
                 '  =1.txt', "'quoted.txt", 'é.txt', 'line\nbreak.txt']
        for name in names:
            self.file(name)
        run, _ = self.snapshot()
        original_names = []
        for row in self.rows(run):
            cell = row['path']
            if row['path_escaped'] == 'true':
                self.assertTrue(cell.startswith("'"))
                cell = cell[1:]
            original_names.append(cell)
            if cell in names[:7]:
                self.assertEqual(row['path_escaped'], 'true')
        self.assertEqual(set(original_names), set(names))

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO fixture')
    def test_file_and_directory_links_and_fifo_are_skipped_without_opening(self):
        self.file('ordinary.py')
        outside = self.work / 'outside'
        outside.mkdir(mode=0o700)
        (outside / 'fictional.txt').write_bytes(b'fictional outside fixture')
        (self.source / 'file-link.py').symlink_to(outside / 'fictional.txt')
        (self.source / 'directory-link').symlink_to(outside, target_is_directory=True)
        os.mkfifo(self.source / 'pipe', 0o600)
        original = INVENTORY._sha256
        with mock.patch.object(INVENTORY, '_sha256', wraps=original) as hashed:
            _, summary = self.snapshot()
        self.assertEqual([call.args[0].name for call in hashed.call_args_list], ['ordinary.py'])
        self.assertEqual(summary['skipped']['links'], 2)
        self.assertEqual(summary['skipped']['nonregular'], 1)

    def test_linked_root_or_output_is_rejected(self):
        linked = self.work / 'linked-input'
        linked.symlink_to(self.source, target_is_directory=True)
        self.assert_code('LINKED_PATH', lambda: INVENTORY.snapshot(linked, self.output, 'fixture'))
        linked.unlink()
        linked.symlink_to(self.output, target_is_directory=True)
        self.assert_code('LINKED_PATH', lambda: INVENTORY.snapshot(self.source, linked, 'fixture'))

    def test_output_equal_to_or_inside_source_is_rejected_before_hashing(self):
        inside = self.source / 'output'
        inside.mkdir(mode=0o700)
        for output in (self.source, inside):
            with self.subTest(output=output.name), mock.patch.object(INVENTORY, '_sha256') as hashed:
                self.assert_code('OUTPUT_INSIDE_INPUT', lambda: INVENTORY.snapshot(self.source, output, 'fixture'))
                hashed.assert_not_called()

    def test_invalid_label_and_limits_fail_before_output(self):
        for label in ('', '../escape', 'has space', 'UpperCase', 'x' * 49):
            with self.subTest(label=label):
                self.assert_code('INVALID_LABEL', lambda: INVENTORY.snapshot(self.source, self.output, label))
        for changes in ({'max_files': True}, {'max_files': 0}, {'max_file_bytes': -1},
                        {'max_total_bytes': 0}, {'max_files': 10001}):
            with self.subTest(changes=changes):
                self.assert_code('INVALID_LIMIT', lambda: self.snapshot(**changes))

    def test_per_file_count_aggregate_and_entry_limits_fail_before_hashing(self):
        self.file('one.py', b'ab')
        self.file('two.py', b'cd')
        for changes, code in (({'max_file_bytes': 1}, 'FILE_BYTE_LIMIT'),
                              ({'max_files': 1}, 'FILE_COUNT_LIMIT'),
                              ({'max_total_bytes': 3}, 'TOTAL_BYTE_LIMIT')):
            with self.subTest(code=code), mock.patch.object(INVENTORY, '_sha256') as hashed:
                self.assert_code(code, lambda: self.snapshot(**changes))
                hashed.assert_not_called()
        with mock.patch.object(INVENTORY, 'MAX_ENTRIES', 1):
            self.assert_code('ENTRY_LIMIT', self.snapshot)

    def test_walk_error_is_not_silent_and_main_omits_private_error_detail(self):
        def failed_walk(*args, **kwargs):
            kwargs['onerror'](PermissionError('fictional sensitive detail'))
            return iter(())
        with mock.patch.object(INVENTORY.os, 'walk', side_effect=failed_walk), \
                mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.source), '--output-dir', str(self.output), '--label', 'fixture'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(capture.getvalue())['error'], 'SOURCE_SCAN_FAILED')
        self.assertNotIn('fictional sensitive detail', capture.getvalue())
        self.assertNotIn(str(self.source), capture.getvalue())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_file_open_failure_cannot_report_a_complete_inventory(self):
        target = self.file('private.py')
        original_open = INVENTORY.os.open
        def denied(path, *args, **kwargs):
            if Path(path) == target:
                raise PermissionError('fictional sensitive detail')
            return original_open(path, *args, **kwargs)
        with mock.patch.object(INVENTORY.os, 'open', side_effect=denied), \
                mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.source), '--output-dir', str(self.output), '--label', 'fixture'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(capture.getvalue())['result'], 'INCOMPLETE')
        self.assertNotIn('fictional sensitive detail', capture.getvalue())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_actual_stream_growth_is_bounded_and_no_output_is_created(self):
        target = self.file('growing.py', b'a')
        original_read, changed, sizes = INVENTORY.os.read, [], []
        def growing(fd, size):
            sizes.append(size)
            block = original_read(fd, size)
            if block and not changed:
                with target.open('ab') as stream:
                    stream.write(b'bcdef')
                changed.append(True)
            return block
        with mock.patch.object(INVENTORY.os, 'read', side_effect=growing):
            self.assert_code('FILE_BYTE_LIMIT', lambda: self.snapshot(max_file_bytes=1))
        self.assertTrue(changed)
        self.assertTrue(all(size <= 2 for size in sizes))

    def test_same_size_content_change_during_read_is_detected(self):
        target = self.file('changing.py', b'old')
        old_mtime = target.stat().st_mtime_ns
        original_read, changed = INVENTORY.os.read, []
        def mutate(fd, size):
            block = original_read(fd, size)
            if block and not changed:
                target.write_bytes(b'new')
                os.utime(target, ns=(old_mtime, old_mtime + 1000000))
                changed.append(True)
            return block
        with mock.patch.object(INVENTORY.os, 'read', side_effect=mutate):
            self.assert_code('SOURCE_CHANGED', self.snapshot)

    def test_replacement_between_selection_and_open_is_detected(self):
        target = self.file('replaced.py', b'original')
        replacement = self.work / 'replacement'
        replacement.write_bytes(b'replaced')
        original_hash = INVENTORY._sha256
        def replace(path, expected, limit):
            os.replace(replacement, target)
            return original_hash(path, expected, limit)
        with mock.patch.object(INVENTORY, '_sha256', side_effect=replace):
            self.assert_code('SOURCE_CHANGED', self.snapshot)

    def test_existing_run_and_existing_report_are_never_overwritten(self):
        self.file('example.py')
        fixed = datetime(2026, 1, 1, tzinfo=timezone.utc)
        with mock.patch.object(INVENTORY.secrets, 'token_hex', return_value='abcdef'):
            run, _ = self.snapshot(when=fixed)
            before = {x.name: x.read_bytes() for x in run.iterdir()}
            with self.assertRaises(INVENTORY.InventoryError) as caught:
                self.snapshot(when=fixed)
        self.assertEqual(str(caught.exception), 'OUTPUT_EXISTS')
        self.assertEqual(before, {x.name: x.read_bytes() for x in run.iterdir()})
        for report in (run / 'files.csv', run / 'summary.json'):
            with self.assertRaises(FileExistsError):
                INVENTORY._exclusive_write(report, b'fictional replacement')
        self.assertEqual(before, {x.name: x.read_bytes() for x in run.iterdir()})

    def test_linked_report_is_not_followed_by_exclusive_write(self):
        target = self.work / 'existing'
        target.write_bytes(b'preserve fictional fixture')
        link = self.output / 'linked-report'
        link.symlink_to(target)
        with self.assertRaises(FileExistsError):
            INVENTORY._exclusive_write(link, b'replacement')
        self.assertEqual(target.read_bytes(), b'preserve fictional fixture')

    def test_success_cli_and_report_omit_absolute_root_and_output_paths(self):
        self.file('demo.py')
        with mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.source), '--output-dir', str(self.output), '--label', 'fixture'])
        self.assertEqual(code, 0)
        stdout = capture.getvalue()
        self.assertEqual(json.loads(stdout)['result'], 'COMPLETE_WITH_EXCLUSIONS')
        for text in [stdout, *((p.read_text()) for p in self.output.glob('*/*'))]:
            self.assertNotIn(str(self.source), text)
            self.assertNotIn(str(self.output), text)


if __name__ == '__main__':
    unittest.main()
