"""Fictional native filesystem, resource and diagnostic boundaries."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import toolkit as t


class Buffers(unittest.TestCase):
    def test_duplicate_json_keys(self):
        with self.assertRaisesRegex(t.Rejected, 'JSON_DUPLICATE_KEY'):
            t.decode(b'{"a":1,"a":2}')

    def test_nonfinite_and_float_json(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1.0}', b'{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(t.Rejected):
                t.decode(raw)

    def test_json_depth_and_unicode(self):
        for raw in (b'[' * 34 + b'0' + b']' * 34, b'"\\ud800"', b'\xff'):
            with self.assertRaises(t.Rejected):
                t.decode(raw)

    def test_bounded_json_and_output(self):
        with self.assertRaises(t.Rejected):
            t.decode(b' ' * (t.MAX_INPUT + 1))
        with self.assertRaises(t.Rejected):
            t.encode({'x': float('nan')})

    def test_xml_entity_utf16_and_pi_refused(self):
        texts = ['<!DOCTYPE x [<!ENTITY e "Fictional">]><x>&e;</x>',
                 '<!DOCTYPE x SYSTEM "example.invalid"><x/>', '<?test data?><x/>', '<x><!-- note --></x>']
        for text in texts:
            for encoding in ('utf-8', 'utf-16'):
                with self.subTest(encoding=encoding), self.assertRaises(t.Rejected):
                    t.xml(text.encode(encoding))

    def test_xml_limits_and_character_reference(self):
        self.assertEqual(t.xml(b'<x>&amp;</x>').text, '&')
        with self.assertRaises(t.Rejected):
            t.xml(('<x>' * 33 + '</x>' * 33).encode())

    def test_duplicate_bindings(self):
        with self.assertRaisesRegex(t.Rejected, 'DUPLICATE_BINDING'):
            t.bindings([('sample', 'a'), ('sample', 'b')])

    def test_argument_error_does_not_echo_supplied_text(self):
        parser = t.Parser(prog='fictional-tool')
        parser.add_argument('--out')
        output = io.StringIO()
        with redirect_stdout(output):
            code = t.run(parser, lambda _: {'status': 'PASS'}, ['SYNTHETIC_SENTINEL'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue()), {'status': 'ERROR', 'code': 'ARGUMENTS_INVALID'})


class Files(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-intake-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'sample.txt'
        self.source.write_bytes(b'Fictional source')

    def fixture(self, action):
        try:
            action()
        except (OSError, NotImplementedError):
            if os.environ.get('OUTLANDS_INTAKE_REQUIRE_LINKS') == '1':
                self.fail('Required native fixture unavailable')
            self.skipTest('Native link fixture unavailable on selected local volume')

    def test_native_read_and_hash(self):
        self.assertEqual(t.read(self.source), b'Fictional source')

    def test_native_write_new_readback_and_posix_mode(self):
        path = self.root / 'new.json'
        raw = t.encode({'fictional': True})
        t.write_new(path, raw)
        self.assertEqual(t.read(path), raw)
        if os.name == 'posix':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_native_overwrite_refusal(self):
        with self.assertRaises((OSError, t.Rejected)):
            t.write_new(self.source, b'changed')
        self.assertEqual(self.source.read_bytes(), b'Fictional source')

    def test_parent_traversal_refusal(self):
        with self.assertRaises((OSError, t.Rejected)):
            t.read(str(self.root / 'nested' / '..' / self.source.name))

    def test_missing_and_directory_inputs(self):
        for path in (self.root, self.root / 'missing'):
            with self.assertRaises((OSError, t.Rejected)):
                t.read(path)

    def test_oversize_read_refused(self):
        with self.assertRaises((OSError, t.Rejected)):
            t.read(self.source, 1)

    def test_output_inside_source_refused(self):
        output = Path(t.__file__).parent / 'fictional-forbidden-report.json'
        self.assertFalse(output.exists())
        with self.assertRaises((OSError, t.Rejected)):
            t.write_new(output, b'{}')
        self.assertFalse(output.exists())

    def test_collection_archive_without_git_metadata_protects_whole_source(self):
        archive = self.root / 'collection'
        tool = archive / 'tools/sample-tool'
        tool.mkdir(parents=True)
        (archive / 'systems').mkdir()
        (archive / 'catalog').mkdir()
        (archive / 'catalog/registry.json').write_bytes(b'{}')
        with patch('toolkit.__file__', str(tool / 'toolkit.py')):
            self.assertEqual(t.source_root(), archive)
            with self.assertRaises((OSError, t.Rejected)):
                t.write_new(archive / 'private-report.json', b'{}')
        self.assertFalse((archive / 'private-report.json').exists())

    def test_native_hardlink_input_refused(self):
        link = self.root / 'hardlink.txt'
        self.assertEqual(t.read(self.source), b'Fictional source')
        self.fixture(lambda: os.link(self.source, link))
        for path in (self.source, link):
            with self.assertRaisesRegex(t.Rejected, 'CONTROL_NOT_SINGLE_LINK' if os.name == 'nt' else 'INPUT_UNSAFE'):
                t.read(path)

    def test_native_linked_parent_read_and_write_refused(self):
        target, link = self.root / 'target', self.root / 'junction'
        target.mkdir()
        (target / 'sample.txt').write_bytes(b'Fictional target')
        self.assertEqual(t.read(target / 'sample.txt'), b'Fictional target')
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(target)],
                                    capture_output=True, timeout=15)
            if result.returncode:
                self.fixture(lambda: (_ for _ in ()).throw(OSError()))
            self.assertTrue(os.path.isjunction(link))
        else:
            self.fixture(lambda: link.symlink_to(target, target_is_directory=True))
        for action in (lambda: t.read(link / 'sample.txt'), lambda: t.write_new(link / 'new.json', b'{}')):
            with self.assertRaises((OSError, t.Rejected)):
                action()
        self.assertFalse((target / 'new.json').exists())

    @unittest.skipUnless(os.name == 'posix', 'POSIX-only leaf symlink fixture')
    def test_posix_leaf_symlink_refused(self):
        link = self.root / 'link.txt'
        self.fixture(lambda: link.symlink_to(self.source))
        with self.assertRaises((OSError, t.Rejected)):
            t.read(link)

    def test_native_input_change_detected(self):
        original = os.read
        def changed(fd, amount):
            result = original(fd, amount)
            if result:
                self.source.write_bytes(b'Changed fictional source')
            return result
        with patch('toolkit.os.read', side_effect=changed), self.assertRaises(t.Rejected):
            t.read(self.source)

    def test_failed_output_retained_without_input_change(self):
        path = self.root / 'partial.json'
        with patch('os.fsync', side_effect=OSError()), self.assertRaises(OSError):
            t.write_new(path, b'Fictional unconfirmed output')
        self.assertTrue(path.exists())
        self.assertEqual(self.source.read_bytes(), b'Fictional source')

    @unittest.skipUnless(os.name == 'nt', 'Windows-only path grammar fixtures')
    def test_windows_ambiguous_paths_refused(self):
        import native_windows as native
        for value in ('sample.txt:stream', 'sample.', 'sample ', 'con', 'x:relative', '//example.invalid/share'):
            with self.subTest(value=value), self.assertRaises(t.Rejected):
                native.selected_path(value, native._core(t.Rejected))


if __name__ == '__main__':
    unittest.main()
