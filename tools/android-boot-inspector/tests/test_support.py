"""Generated local files only; shared first-party safeguards for each standalone tool."""
from pathlib import Path
import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import inspection_support as support


class SupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.input = self.base/'generated.txt'
        self.input.write_bytes(b'fictional input\n')

    def fails(self, code, call, *args):
        with self.assertRaisesRegex(support.TextError, '^'+code+'$'): call(*args)

    def test_snapshot_exact_and_unchanged(self):
        self.assertEqual(support.snapshot(self.input), b'fictional input\n')
        self.assertEqual(self.input.read_bytes(), b'fictional input\n')

    def test_absolute_and_traversal_required(self):
        self.fails('LOCAL_ABSOLUTE_PATH_REQUIRED', support.local_path, 'relative.txt')
        self.fails('LOCAL_ABSOLUTE_PATH_REQUIRED', support.local_path, self.base/'..'/'generated.txt')
        self.fails('LOCAL_ABSOLUTE_PATH_REQUIRED', support.local_path, '//server/share/file')

    @unittest.skipUnless(os.name == 'nt', 'Windows alternate stream syntax only')
    def test_windows_stream_rejected(self):
        self.fails('DEVICE_OR_STREAM_PATH_REJECTED', support.local_path, str(self.input)+':stream')

    def test_regular_file_required(self):
        self.fails('REGULAR_FILE_REQUIRED', support.snapshot, self.base)

    def test_byte_boundary(self):
        self.input.write_bytes(b'a'*support.MAX_BYTES)
        self.assertEqual(len(support.snapshot(self.input)), support.MAX_BYTES)
        self.input.write_bytes(b'a'*(support.MAX_BYTES+1))
        self.fails('INPUT_BYTE_LIMIT', support.snapshot, self.input)

    def test_fd_mutation_detected(self):
        original = os.read; called = False
        def changed(fd, count):
            nonlocal called
            data = original(fd, count)
            if not called:
                called = True; self.input.write_bytes(b'changed length input')
            return data
        with patch.object(support.os, 'read', side_effect=changed):
            self.fails('INPUT_CHANGED', support.snapshot, self.input)

    def test_duplicate_path_and_hardlink_inputs_rejected(self):
        self.fails('DUPLICATE_INPUT_FILE', support.source_inputs, [self.input, self.input])
        linked = self.base/'hardlink.txt'
        try: os.link(self.input, linked)
        except OSError: self.skipTest('Hardlinks unavailable in test environment')
        self.fails('DUPLICATE_INPUT_FILE', support.source_inputs, [self.input, linked])

    def test_link_and_linked_parent_rejected(self):
        link = self.base/'link.txt'
        try: link.symlink_to(self.input)
        except OSError: self.skipTest('Symlink creation requires platform privileges')
        self.fails('LINKED_PATH_REJECTED', support.snapshot, link)
        route = self.base/'linked-dir'; route.symlink_to(self.base, target_is_directory=True)
        self.fails('LINKED_PATH_REJECTED', support.snapshot, route/self.input.name)
        self.fails('LINKED_PATH_REJECTED', support.write_report, self.report(), route/'report', [self.input])

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO test')
    def test_fifo_rejected_without_opening(self):
        fifo = self.base/'pipe'; os.mkfifo(fifo)
        self.fails('REGULAR_FILE_REQUIRED', support.snapshot, fifo)

    def test_aggregate_and_count_limits(self):
        self.fails('INPUT_COUNT_LIMIT', support.source_inputs, [])
        self.fails('INPUT_COUNT_LIMIT', support.source_inputs, [self.input]*33)
        files = []
        for index in range(5):
            item = self.base/f'{index}.txt'; item.write_bytes(b'x'*support.MAX_BYTES); files.append(item)
        self.fails('TOTAL_BYTE_LIMIT', support.source_inputs, files)

    def test_utf8_bom_crlf(self):
        self.assertEqual(support.text_lines(b'\xef\xbb\xbfa\r\nb'), [(1,'a'), (2,'b')])

    def test_encoding_controls_and_line_limits(self):
        self.fails('UTF8_REQUIRED', support.text_lines, b'\xff')
        for value in ('a\rb', 'a\0b', 'a\u202eb', 'a\u2028b', 'a\ud800b'):
            if '\ud800' in value: continue
            self.fails('TEXT_CONTROL_UNSUPPORTED', support.text_lines, value.encode())
        self.fails('TEXT_LINE_LIMIT', support.text_lines, b'x'*8193)
        self.fails('TEXT_LINE_LIMIT', support.text_lines, b'\n'*20000)

    def test_structural_bounds_and_fixed_codes(self):
        self.fails('RECORD_LIMIT', support.bounded_append, [{}]*4000, {})
        self.fails('FINDING_LIMIT', support.issue, [{}]*4000, 'CODE', 'input', 1)
        parser = support.Parser(); parser.add_argument('--required', required=True)
        self.fails('ARGUMENTS_INVALID', parser.parse_args, ['--private-unknown=value'])

    def test_strict_json(self):
        self.assertEqual(support.strict_json(b'{"value":1}'), {'value':1})
        for value in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1.5}', b'{', b'\xff', b'[[[[[[[[[[0]]]]]]]]]]'):
            with self.assertRaises(support.TextError): support.strict_json(value)

    def test_explicit_json_limits_bom_and_controls(self):
        data=json.dumps([0]*1100).encode()
        self.fails('JSON_STRUCTURE_LIMIT',support.strict_json,data)
        self.assertEqual(len(support.strict_json(data,support.MAX_BYTES,40000,8192)),1100)
        self.assertEqual(support.strict_json(b'\xef\xbb\xbf{"value":1}'),{'value':1})
        self.fails('JSON_LIMIT_INVALID',support.strict_json,b'{}',False)
        self.fails('JSON_TEXT_UNSUPPORTED',support.strict_json,b'{"value":"\\u202e"}')

    def report(self):
        return {'tool':'Generated <test>', 'text':'</pre><script>bad()</script>\nsecond', 'findings':[], 'coverage_issues':[]}

    def test_fresh_report_html_and_manifest(self):
        out = self.base/'report'; support.write_report(self.report(), out, [self.input])
        self.assertEqual(set(p.name for p in out.iterdir()), {'report.json','report.html','MANIFEST.json'})
        rendered = (out/'report.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>bad()', rendered); self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('Content-Security-Policy', rendered); self.assertIn('\n', rendered)
        for row in json.loads((out/'MANIFEST.json').read_text())['files']:
            data = (out/row['path']).read_bytes()
            self.assertEqual(row['bytes'], len(data)); self.assertEqual(row['sha256'], hashlib.sha256(data).hexdigest())
        self.fails('OUTPUT_EXISTS', support.write_report, self.report(), out, [self.input])

    def test_input_never_overwritten(self):
        before = self.input.read_bytes()
        self.fails('OUTPUT_EXISTS', support.write_report, self.report(), self.input, [self.input])
        self.assertEqual(self.input.read_bytes(), before)

    def test_report_limit_before_any_output(self):
        value = self.report(); value['text'] = '<'*support.MAX_REPORT
        self.fails('REPORT_BYTE_LIMIT', support.write_report, value, self.base/'too-big', [self.input])
        self.assertFalse((self.base/'too-big').exists())


if __name__ == '__main__': unittest.main()
