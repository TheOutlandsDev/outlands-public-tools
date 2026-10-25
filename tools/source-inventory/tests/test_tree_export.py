"""Generated folder-tree fixtures; never scan a real project or follow input links."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from test_source_inventory import INVENTORY


class TreeExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fictional-tree-')
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.root = self.work / 'input'
        self.output = self.work / 'reports'
        self.root.mkdir()
        self.output.mkdir()

    def file(self, relative, data=b'fictional example\n'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def snapshot(self, **options):
        return INVENTORY.snapshot(self.root, self.output, 'tree-fixture', tree=True, **options)

    def assert_error(self, code, **options):
        with self.assertRaises(INVENTORY.InventoryError) as caught:
            self.snapshot(**options)
        self.assertEqual(str(caught.exception), code)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_default_mode_still_writes_only_original_two_reports(self):
        self.file('one.py')
        run, summary = INVENTORY.snapshot(self.root, self.output, 'old-format')
        self.assertEqual({p.name for p in run.iterdir()}, {'files.csv', 'summary.json'})
        self.assertNotIn('tree', summary)
        self.assertNotIn('additional_excluded_directories', summary)

    def test_created_then_written_unchanged_file_has_comparable_path_fd_identity(self):
        path = self.root / 'created-then-written.py'
        path.touch()
        time.sleep(0.02)
        path.write_bytes(b'fictional bytes written after creation')
        before = path.lstat()
        run, summary = self.snapshot()
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(path.read_bytes(), b'fictional bytes written after creation')
        self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                      (run / 'files.csv').read_text(encoding='utf-8'))
        self.assertEqual(INVENTORY._identity(path.lstat()), INVENTORY._identity(before))

    def test_tree_shares_selected_scope_and_preserves_empty_directories(self):
        (self.root / 'empty').mkdir()
        self.file('nested/part.py', b'part')
        self.file('top.py', b'top')
        run, summary = self.snapshot()
        text = (run / 'tree.txt').read_text(encoding='utf-8')
        self.assertIn('"empty/"', text)
        self.assertIn('"nested/"', text)
        self.assertIn('"part.py"', text)
        self.assertIn('"top.py"', text)
        self.assertEqual(summary['tree']['directory_count'], 2)
        self.assertEqual(summary['tree']['entry_count'], 4)
        self.assertEqual(summary['tree']['displayed_entries'], 4)
        self.assertEqual(summary['file_count'], 2)
        self.assertTrue(summary['tree']['display_complete'])
        self.assertEqual(summary['tree']['hidden_by_depth'], 0)

    def test_tree_hash_matches_exact_utf8_bytes_and_summary_on_disk(self):
        self.file('é.py')
        run, summary = self.snapshot()
        raw = (run / 'tree.txt').read_bytes()
        self.assertIn('é.py', raw.decode('utf-8'))
        self.assertEqual(summary['tree']['tree_txt_sha256'], hashlib.sha256(raw).hexdigest().upper())
        self.assertEqual(json.loads((run / 'summary.json').read_text(encoding='utf-8')), summary)
        self.assertNotIn(str(self.root), raw.decode('utf-8'))
        self.assertNotIn(str(self.output), raw.decode('utf-8'))

    def test_tree_is_deterministic_directory_first_then_casefold_order(self):
        self.file('z.py')
        self.file('a-folder/part.py')
        (self.root / 'B-empty').mkdir()
        self.file('A.py')
        first, _ = self.snapshot()
        second, _ = self.snapshot()
        raw = (first / 'tree.txt').read_bytes()
        self.assertEqual(raw, (second / 'tree.txt').read_bytes())
        text = raw.decode('utf-8')
        self.assertLess(text.index('"a-folder/"'), text.index('"B-empty/"'))
        self.assertLess(text.index('"B-empty/"'), text.index('"A.py"'))
        self.assertLess(text.index('"A.py"'), text.index('"z.py"'))

    def test_excluded_directories_files_and_names_do_not_appear_in_tree(self):
        self.file('ordinary.py')
        self.file('.git/private-name.py')
        self.file('data/private-name.csv')
        self.file('fictional.key')
        run, summary = self.snapshot()
        text = (run / 'tree.txt').read_text(encoding='utf-8')
        self.assertNotIn('.git', text)
        self.assertNotIn('data/', text)
        self.assertNotIn('private-name', text)
        self.assertNotIn('fictional.key', text)
        self.assertEqual(summary['skipped']['directories'], 2)
        self.assertEqual(summary['skipped']['files'], 1)
        self.assertEqual(summary['tree']['entry_count'], 1)

    def test_additional_exclusions_are_casefolded_deduplicated_and_additive(self):
        self.file('Scratch/private.txt')
        self.file('keep/ordinary.py')
        self.file('.git/metadata')
        run, summary = self.snapshot(exclude_directories=['scratch', 'SCRATCH'])
        text = (run / 'tree.txt').read_text(encoding='utf-8')
        self.assertNotIn('Scratch', text)
        self.assertNotIn('private.txt', text)
        self.assertNotIn('.git', text)
        self.assertIn('"keep/"', text)
        self.assertEqual(summary['additional_excluded_directories'], ['scratch'])
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['skipped']['directories'], 2)

    def test_exclusions_apply_without_requesting_a_tree(self):
        self.file('omit/private.py')
        self.file('keep.py')
        run, summary = INVENTORY.snapshot(self.root, self.output, 'exclude-only', exclude_directories=['OMIT'])
        self.assertEqual({p.name for p in run.iterdir()}, {'files.csv', 'summary.json'})
        self.assertEqual(summary['file_count'], 1)
        self.assertNotIn('tree', summary)

    def test_invalid_exclusions_fail_before_scan_or_output(self):
        cases = [None, 'not-a-list', [True], [''], ['.'], ['..'], ['has/slash'],
                 ['has\\slash'], ['control\nname'], ['\ud800'], ['x' * 256], ['x'] * 65]
        for value in cases:
            with self.subTest(value=repr(value)), mock.patch.object(INVENTORY, '_collect') as collect:
                self.assert_error('INVALID_EXCLUSIONS', exclude_directories=value)
                collect.assert_not_called()

    def test_depth_is_display_only_and_does_not_reduce_hash_coverage(self):
        self.file('outer/inner/deep.py', b'unchanged selected bytes')
        run, summary = self.snapshot(tree_depth=1)
        text = (run / 'tree.txt').read_text(encoding='utf-8')
        self.assertIn('"outer/"', text)
        self.assertNotIn('"inner/"', text)
        self.assertNotIn('deep.py', text)
        self.assertIn('[subtree omitted at display depth limit]', text)
        self.assertEqual(summary['tree']['entry_count'], 3)
        self.assertEqual(summary['tree']['displayed_entries'], 1)
        self.assertEqual(summary['tree']['hidden_by_depth'], 2)
        self.assertFalse(summary['tree']['display_complete'])
        self.assertEqual(summary['file_count'], 1)
        self.assertEqual(summary['hashed_file_count'], 1)
        self.assertIn('outer/inner/deep.py', (run / 'files.csv').read_text(encoding='utf-8'))

    def test_depth_exact_boundary_does_not_claim_omission(self):
        self.file('outer/item.py')
        run, summary = self.snapshot(tree_depth=2)
        self.assertTrue(summary['tree']['display_complete'])
        self.assertEqual(summary['tree']['hidden_by_depth'], 0)
        self.assertNotIn('omitted', (run / 'tree.txt').read_text(encoding='utf-8'))

    def test_empty_input_has_minimal_tree_and_zero_entries(self):
        run, summary = self.snapshot()
        self.assertEqual((run / 'tree.txt').read_text(encoding='utf-8'), 'OUTLANDS selected source tree\n.\n')
        self.assertEqual(summary['tree']['entry_count'], 0)
        self.assertTrue(summary['tree']['display_complete'])

    def test_invalid_tree_options_fail_without_output(self):
        for depth in (0, -1, 65, True, '3', 2.0):
            with self.subTest(depth=depth):
                self.assert_error('INVALID_TREE_OPTIONS', tree_depth=depth)
        with self.assertRaises(INVENTORY.InventoryError) as caught:
            INVENTORY.snapshot(self.root, self.output, 'bad-tree', tree='true')
        self.assertEqual(str(caught.exception), 'INVALID_TREE_OPTIONS')
        with self.assertRaises(INVENTORY.InventoryError) as caught:
            INVENTORY.snapshot(self.root, self.output, 'bad-tree', tree_depth=1)
        self.assertEqual(str(caught.exception), 'TREE_REQUIRED')

    def test_tree_byte_bound_is_checked_before_any_report_is_created(self):
        self.file('ordinary.py')
        with mock.patch.object(INVENTORY, 'MAX_TREE_BYTES', 10):
            self.assert_error('TREE_BYTE_LIMIT')

    def test_tree_does_not_trigger_a_second_walk_or_hash_additional_files(self):
        self.file('selected.py')
        self.file('excluded.key')
        with mock.patch.object(INVENTORY.os, 'walk', wraps=INVENTORY.os.walk) as walked, \
                mock.patch.object(INVENTORY, '_sha256', wraps=INVENTORY._sha256) as hashed:
            self.snapshot()
        self.assertEqual(walked.call_count, 1)
        self.assertEqual([call.args[0].name for call in hashed.call_args_list], ['selected.py'])

    def test_control_bidi_and_separator_characters_are_escaped_in_names(self):
        # Pure quoting checks run everywhere; Windows forbids some of these filenames.
        for value in ('line\nbreak', 'tab\tname', '\x1b[31m', '\u202evisible', '\u2028name', 'slash\\name'):
            encoded = INVENTORY._tree_name(value)
            self.assertEqual(json.loads(encoded), value)
            self.assertNotIn('\n', encoded)
            self.assertNotIn('\x1b', encoded)
            self.assertNotIn('\u202e', encoded)
            self.assertNotIn('\u2028', encoded)

    @unittest.skipUnless(os.name == 'posix', 'POSIX permits control characters in filenames')
    def test_actual_newline_and_escape_filenames_cannot_forge_tree_lines(self):
        self.file('line\nbreak.py')
        self.file('\x1b[31m.py')
        run, summary = self.snapshot()
        text = (run / 'tree.txt').read_text(encoding='utf-8')
        self.assertEqual(len(text.splitlines()), 4)
        self.assertIn('line\\nbreak.py', text)
        self.assertIn('\\u001b[31m.py', text)
        self.assertNotIn('\x1b', text)

    def test_symlink_entries_are_neither_followed_nor_rendered(self):
        outside = self.work / 'outside'
        outside.mkdir()
        (outside / 'outside.py').write_text('fictional outside')
        try:
            (self.root / 'linked').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                self.skipTest('Windows account lacks symlink creation permission')
            raise
        run, summary = self.snapshot()
        self.assertNotIn('linked', (run / 'tree.txt').read_text(encoding='utf-8'))
        self.assertNotIn('outside', (run / 'tree.txt').read_text(encoding='utf-8'))
        self.assertEqual(summary['skipped']['links'], 1)
        self.assertEqual(summary['tree']['entry_count'], 0)

    def test_cli_tree_and_exclusion_options_produce_a_tree(self):
        self.file('nested/ordinary.py')
        self.file('omit/private.py')
        with mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.root), '--output-dir', str(self.output),
                                   '--label', 'cli-tree', '--tree', '--tree-depth', '2', '--exclude-dir', 'omit'])
        self.assertEqual(code, 0)
        result = json.loads(capture.getvalue())
        run = self.output / result['snapshot']
        self.assertEqual(result['file_count'], 1)
        self.assertTrue((run / 'tree.txt').is_file())
        self.assertNotIn(str(self.root), capture.getvalue())

    def test_unknown_cli_option_is_refused_without_scanning(self):
        with mock.patch.object(INVENTORY, '_collect') as collect, mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.root), '--output-dir', str(self.output),
                                   '--label', 'unknown', '--tree-unknown'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(capture.getvalue())['error'], 'ARGUMENTS_INVALID')
        collect.assert_not_called()

    def test_explicit_cli_depth_requires_tree_even_when_equal_to_default(self):
        with mock.patch.object(INVENTORY, '_collect') as collect, mock.patch('sys.stdout', new_callable=io.StringIO) as capture:
            code = INVENTORY.main(['--root', str(self.root), '--output-dir', str(self.output),
                                   '--label', 'missing-tree', '--tree-depth', '16'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(capture.getvalue())['error'], 'TREE_REQUIRED')
        collect.assert_not_called()


if __name__ == '__main__':
    unittest.main()
