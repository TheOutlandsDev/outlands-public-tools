"""Fresh copied-pair CLI checks using authored Markdown and disposable outputs."""

import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ('markdown_docx.py', 'docx_windows.py')
SUCCESS = b'Document created; review its content before sharing.' + (b'\r\n' if os.name == 'nt' else b'\n')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS = {'dc': 'http://purl.org/dc/elements/1.1/',
      'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
      'dcterms': 'http://purl.org/dc/terms/'}
MARKDOWN = ('# Fictional Parts Request\nInvented material request for review.\n'
            '- Fictional bullet\n1. Fictional number\n## Fictional details\n'
            '| Item | Quantity |\n| --- | --- |\n| DEMO-A | 2 |\n| DEMO-B | 3 |\n')
PROBE = r'''
import os,socket,subprocess,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import markdown_docx as m
import docx_windows as w
m.windows_backend=lambda:w
kind=sys.argv[2]
if os.name=='nt' and hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(newline='\n')
if kind=='no_external':
 def refuse(*args,**kwargs):raise AssertionError('UNEXPECTED_EXTERNAL_ACTION')
 socket.socket=refuse;subprocess.Popen=refuse;os.system=refuse;os.scandir=refuse
elif kind=='interrupt':
 def interrupt(*args,**kwargs):raise KeyboardInterrupt
 m.read_markdown=interrupt
elif kind=='flush':
 if os.name=='nt':
  def failure(*args,**kwargs):raise m.BuildError('FICTIONAL_FLUSH_FAILURE')
  w.Native.flush=failure
 else:
  def failure(*args,**kwargs):raise OSError('fictional-private-error')
  os.fsync=failure
elif kind=='partial':
 assert os.name=='nt'
 original=w.Native.write
 def failure(self,handle,data):
  original(self,handle,data[:11]);raise m.BuildError('FICTIONAL_WRITE_FAILURE')
 w.Native.write=failure
elif kind=='short':
 assert os.name=='nt'
 original=w.Native.__init__
 def initialize(self,*args,**kwargs):
  original(self,*args,**kwargs);write=self.dll.WriteFile
  def short(handle,buffer,length,written,overlapped):
   return write(handle,buffer,min(13,length),written,overlapped)
  self.dll.WriteFile=short
 w.Native.__init__=initialize
elif kind=='copied_import':
 assert Path(m.__file__).resolve().parent==Path(sys.argv[1]).resolve()
 assert Path(w.__file__).resolve().parent==Path(sys.argv[1]).resolve()
 assert set(p.name for p in Path(sys.argv[1]).iterdir())=={'markdown_docx.py','docx_windows.py'}
else:raise AssertionError('UNKNOWN_PROBE')
raise SystemExit(m.main(sys.argv[3:]))
'''


class Download(unittest.TestCase):
    def setUp(self):
        parent = os.environ.get('OUTLANDS_TEST_TEMP')
        self.temp = tempfile.TemporaryDirectory(prefix='fictional-docx-download-', dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name)
        self.copy = self.private / 'copied runtime'
        self.copy.mkdir()
        self.pins = {}
        for name in RUNTIME:
            data = (ROOT / name).read_bytes()
            (self.copy / name).write_bytes(data)
            self.pins[name] = hashlib.sha256(data).hexdigest()
        self.source = self.private / 'fictional input.md'
        self.source.write_text(MARKDOWN, encoding='utf-8', newline='\n')
        self.output = self.private / 'fictional output.docx'
        self.addCleanup(self.runtime_preserved)

    def runtime_preserved(self):
        self.assertEqual({p.name for p in self.copy.iterdir()}, set(RUNTIME))
        self.assertEqual({n: hashlib.sha256((self.copy / n).read_bytes()).hexdigest()
                          for n in RUNTIME}, self.pins)
        self.assertEqual(list(self.private.rglob('*.pyc')), [])

    def args(self, source=None, output=None, title='Fictional title'):
        return ['--input', str(self.source if source is None else source), '--output',
                str(self.output if output is None else output), '--title', title]

    def call(self, arguments=None, code=0, probe=None, no_site=False):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1',
                   PYTHON_COLORS='0', NO_COLOR='1')
        env.pop('PYTHONPATH', None)
        flags = ['-B'] + (['-S'] if no_site else [])
        command = ([sys.executable, *flags, '-c', PROBE, str(self.copy), probe]
                   if probe else [sys.executable, *flags, str(self.copy / 'markdown_docx.py')])
        done = subprocess.run(command + (self.args() if arguments is None else arguments),
                              cwd=self.private, env=env, capture_output=True, timeout=60)
        self.assertEqual(done.returncode, code, done.stderr.decode('utf-8', errors='replace'))
        public = done.stdout + done.stderr
        for value in (str(self.private).encode(), b'Traceback', b'fictional-private-error'):
            self.assertNotIn(value, public)
        if code == 0 and arguments != ['--help']:
            self.assertEqual(done.stdout, SUCCESS)
            self.assertEqual(done.stderr, b'')
        if code == 2:
            self.assertEqual(done.stdout, b'')
            self.assertTrue(done.stderr.startswith(b'DOCUMENT_BUILD_FAILED:'))
            self.assertEqual(len(done.stderr.splitlines()), 1)
        return done

    def reject(self, arguments=None, reason=None, **kwargs):
        done = self.call(arguments, code=2, **kwargs)
        if reason is not None:
            self.assertEqual(done.stderr, ('DOCUMENT_BUILD_FAILED:' + reason + '\n').encode())
        return done

    def inspect(self, path=None, title='Fictional title'):
        with zipfile.ZipFile(self.output if path is None else path) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIsNone(archive.testzip())
            self.assertIn('[Content_Types].xml', names)
            self.assertIn('word/document.xml', names)
            for name in names:
                self.assertNotIn('..', name.split('/'))
                self.assertFalse(name.startswith('/'))
                if name.endswith(('.xml', '.rels')):
                    raw = archive.read(name)
                    self.assertNotIn(str(self.private).encode(), raw)
                    tree = ET.fromstring(raw)
                    if name.endswith('.rels'):
                        self.assertFalse(any(node.get('TargetMode') == 'External' for node in tree))
            self.assertFalse(any(n.startswith('word/media/') or 'vbaProject' in n or
                                 '/embeddings/' in n for n in names))
            root = ET.fromstring(archive.read('word/document.xml'))
            core = ET.fromstring(archive.read('docProps/core.xml'))
            expected = {'dc:title': title, 'dc:subject': 'Local Markdown document',
                        'dc:creator': 'OUTLANDS', 'cp:lastModifiedBy': 'OUTLANDS',
                        'dcterms:created': '2000-01-01T00:00:00Z',
                        'dcterms:modified': '2000-01-01T00:00:00Z',
                        'cp:revision': '1', 'dc:language': 'en'}
            for key, value in expected.items():
                self.assertEqual(core.findtext(key, namespaces=NS), value)
            for key in ('dc:description', 'cp:keywords', 'cp:category', 'dc:identifier'):
                self.assertFalse(core.findtext(key, namespaces=NS))
            return root, archive.read('word/document.xml'), names

    def symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except OSError as error:
            if os.name == 'nt' and getattr(error, 'winerror', None) == 1314:
                if os.environ.get('OUTLANDS_DOCX_REQUIRE_NATIVE_LINKS') == '1':
                    raise AssertionError('REQUIRED_NATIVE_SYMLINK_UNAVAILABLE') from error
                self.skipTest('Native symlink privilege unavailable')
            raise

    def test_static_help_has_no_selected_paths_or_files(self):
        done = self.call(['--help'])
        self.assertEqual(done.stderr, b'')
        self.assertIn(b'usage: markdown_docx.py', done.stdout)
        self.assertIn(b'--input', done.stdout)
        self.assertFalse(self.output.exists())

    def test_unknown_version_and_arguments_have_fixed_redacted_errors(self):
        for args in ([], ['--version'], ['--unknown', 'FICTIONAL_PRIVATE_SENTINEL'],
                     ['--input'], ['--input', str(self.source)]):
            done = self.reject(args, 'ARGUMENTS_INVALID')
            self.assertNotIn(b'FICTIONAL_PRIVATE_SENTINEL', done.stderr)
        self.assertFalse(self.output.exists())

    def test_success_has_exact_heading_list_table_and_layout_contract(self):
        self.call()
        root, raw, _ = self.inspect()
        styles = [p.get(W + 'val') for p in root.iter(W + 'pStyle')]
        for style in ('Heading1', 'Heading2', 'ListBullet', 'ListNumber'):
            self.assertIn(style, styles)
        self.assertEqual(len(list(root.iter(W + 'tbl'))), 1)
        self.assertEqual(len(list(root.iter(W + 'tr'))), 3)
        self.assertEqual(len(list(root.iter(W + 'tc'))), 6)
        self.assertEqual(len(list(root.iter(W + 'tblHeader'))), 1)
        self.assertIn(b'DEMO-A', raw)
        margins = next(root.iter(W + 'pgMar'))
        self.assertEqual([margins.get(W + side) for side in ('top', 'bottom', 'left', 'right')], ['864'] * 4)

    def test_input_and_copied_pair_stay_unchanged_and_only_output_is_created(self):
        before = self.source.read_bytes()
        self.call()
        self.inspect()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual({p.name for p in self.private.iterdir()},
                         {self.copy.name, self.source.name, self.output.name})

    def test_bom_and_unicode_are_preserved(self):
        self.source.write_bytes(b'\xef\xbb\xbf' + '# Fictional échantillon\nInvented Ω text.\n'.encode())
        self.call()
        _, raw, _ = self.inspect()
        self.assertIn('échantillon'.encode(), raw)
        self.assertIn('Ω'.encode(), raw)

    def test_empty_input_still_creates_reviewable_package(self):
        self.source.write_bytes(b'')
        self.call()
        self.inspect()

    def test_title_is_trimmed_and_exact_160_character_limit_is_preserved(self):
        self.call(self.args(title='  Fictional title  '))
        self.inspect()
        target = self.private / 'long title.docx'
        title = 'T' * 160
        self.call(self.args(output=target, title=title))
        self.inspect(target, title)
        for value in ('', ' ', 'T' * 161, 'fictional\nprivate'):
            self.reject(self.args(output=self.private / 'rejected title.docx', title=value), 'TITLE_INVALID')
        self.assertFalse((self.private / 'rejected title.docx').exists())

    def test_exact_input_byte_cap_succeeds_and_one_extra_byte_is_refused(self):
        data = (b'x' * 3999 + b'\n') * 65 + b'x' * 2144
        self.assertEqual(len(data), 262144)
        self.source.write_bytes(data)
        self.call()
        self.inspect()
        self.source.write_bytes(data + b'x')
        self.reject(self.args(output=self.private / 'oversize.docx'),
                    'INPUT_SIZE_LIMIT' if os.name == 'nt' else 'INPUT_TOO_LARGE')
        self.assertFalse((self.private / 'oversize.docx').exists())

    def test_line_count_limit_accepts_5000_and_refuses_5001(self):
        self.source.write_bytes(b'\n' * 4999 + b' ')
        self.call()
        self.inspect()
        self.source.write_bytes(b'\n' * 5000 + b' ')
        self.reject(self.args(output=self.private / 'many lines.docx'), 'INPUT_STRUCTURE_LIMIT')
        self.assertFalse((self.private / 'many lines.docx').exists())

    def test_line_character_limit_accepts_4000_and_refuses_4001(self):
        self.source.write_bytes(b'x' * 4000)
        self.call()
        self.inspect()
        self.source.write_bytes(b'x' * 4001)
        self.reject(self.args(output=self.private / 'long line.docx'), 'INPUT_STRUCTURE_LIMIT')
        self.assertFalse((self.private / 'long line.docx').exists())

    def test_invalid_utf8_and_control_characters_create_no_document(self):
        for data, reason in ((b'\xff', 'INPUT_OR_IO'), (b'fictional\x00text', 'INPUT_CONTROL_CHARACTER'),
                             (b'fictional\x01text', 'INPUT_CONTROL_CHARACTER')):
            self.source.write_bytes(data)
            self.reject(reason=reason)
            self.assertFalse(self.output.exists())

    def test_ragged_wide_and_overlong_tables_are_refused(self):
        cases = [('| A | B |\n| --- | --- |\n| one |\n', 'TABLE_NOT_RECTANGULAR'),
                 ('|' + ' A |' * 17 + '\n|' + ' --- |' * 17 + '\n', 'TABLE_LIMIT'),
                 ('| A | B |\n| --- | --- |\n' + '| one | two |\n' * 1001, 'TABLE_LIMIT')]
        for data, reason in cases:
            self.source.write_text(data, encoding='utf-8')
            self.reject(reason=reason)
            self.assertFalse(self.output.exists())

    def test_sixteen_column_table_has_exact_cell_coverage(self):
        self.source.write_text('|' + ' A |' * 16 + '\n|' + ' --- |' * 16 + '\n|' + ' X |' * 16 + '\n', encoding='utf-8')
        self.call()
        root, _, _ = self.inspect()
        self.assertEqual(len(list(root.iter(W + 'tc'))), 32)
        self.assertEqual(len(list(root.iter(W + 'tr'))), 2)

    def test_existing_file_directory_and_source_destination_are_preserved(self):
        self.output.write_bytes(b'FICTIONAL_PRIOR_DOCUMENT')
        self.reject(reason='OUTPUT_EXISTS')
        self.assertEqual(self.output.read_bytes(), b'FICTIONAL_PRIOR_DOCUMENT')
        folder = self.private / 'existing.docx'
        folder.mkdir()
        (folder / 'kept.txt').write_bytes(b'kept')
        self.reject(self.args(output=folder), 'OUTPUT_EXISTS')
        self.assertEqual((folder / 'kept.txt').read_bytes(), b'kept')
        before = self.source.read_bytes()
        self.reject(self.args(output=self.source), 'OUTPUT_EXISTS')
        self.assertEqual(self.source.read_bytes(), before)

    def test_missing_parent_and_wrong_extension_create_no_output(self):
        missing = self.private / 'missing parent' / 'new.docx'
        self.reject(self.args(output=missing))
        self.assertFalse(missing.parent.exists())
        wrong = self.private / 'new.txt'
        self.reject(self.args(output=wrong), 'OUTPUT_EXTENSION')
        self.assertFalse(wrong.exists())

    def test_missing_and_directory_inputs_have_fixed_refusals(self):
        for source in (self.private / 'absent.md', self.private):
            self.reject(self.args(source=source))
            self.assertFalse(self.output.exists())

    def test_relative_paths_spaces_and_uppercase_docx_extension_work(self):
        output = Path('fictional relative.DOCX')
        self.call(self.args(source=Path(self.source.name), output=output))
        self.inspect(self.private / output)

    def test_literal_markup_never_fetches_or_generates_remote_relationships(self):
        self.source.write_text('# Fictional\n![demo](https://example.invalid/image.png)\n'
                               '[demo](https://example.invalid/)\n<script>fictional()</script>\n', encoding='utf-8')
        self.call(probe='no_external')
        _, raw, _ = self.inspect()
        self.assertIn(b'https://example.invalid/', raw)
        self.assertIn(b'&lt;script&gt;fictional()&lt;/script&gt;', raw)

    def test_traversal_in_input_and_output_is_refused_before_creation(self):
        for args in (self.args(source=str(self.private / 'unused' / '..' / self.source.name)),
                     self.args(output=str(self.private / 'unused' / '..' / self.output.name))):
            self.reject(args)
        self.assertFalse(self.output.exists())

    def test_crlf_and_lf_have_equal_document_text_and_core_properties(self):
        self.call()
        first, _, _ = self.inspect()
        self.source.write_bytes(MARKDOWN.replace('\n', '\r\n').encode())
        second = self.private / 'crlf.docx'
        self.call(self.args(output=second))
        other, _, _ = self.inspect(second)
        self.assertEqual(ET.tostring(first), ET.tostring(other))

    def test_copied_pair_imports_are_independent_of_collection_layout(self):
        self.call(probe='copied_import')
        self.inspect()

    def test_missing_site_dependencies_refuse_build_but_static_help_works(self):
        self.reject(reason='DEPENDENCY_UNAVAILABLE', no_site=True)
        self.assertFalse(self.output.exists())
        done = self.call(['--help'], no_site=True)
        self.assertIn(b'usage: markdown_docx.py', done.stdout)

    def test_handled_input_errors_never_echo_private_argument_values(self):
        bad = self.private / 'FICTIONAL_PRIVATE_INPUT.md'
        done = self.reject(self.args(source=bad))
        self.assertNotIn(b'FICTIONAL_PRIVATE_INPUT', done.stderr)
        self.reject(self.args(title='FICTIONAL_PRIVATE\tVALUE'), 'TITLE_INVALID')
        self.assertFalse(self.output.exists())

    def test_flush_failure_obeys_platform_specific_cleanup_and_retry(self):
        self.reject(probe='flush', reason='FICTIONAL_FLUSH_FAILURE' if os.name == 'nt' else 'INPUT_OR_IO')
        if os.name == 'nt':
            self.inspect()
            before = self.output.read_bytes()
            self.reject(reason='OUTPUT_EXISTS')
            self.assertEqual(self.output.read_bytes(), before)
        else:
            self.assertFalse(self.output.exists())
            self.call()
            self.inspect()

    def test_interruption_before_output_has_fixed_error_and_no_document(self):
        self.reject(probe='interrupt', reason='INTERRUPTED')
        self.assertFalse(self.output.exists())

    def test_native_hardlink_input_policy_and_existing_output_are_preserved(self):
        linked = self.private / 'hardlinked.md'
        os.link(self.source, linked)
        before = self.source.read_bytes()
        if os.name == 'nt':
            self.reject(self.args(source=linked))
            self.assertFalse(self.output.exists())
        else:
            self.call(self.args(source=linked))
            self.inspect()
        self.assertEqual(self.source.read_bytes(), before)
        destination = self.private / 'hardlinked output.docx'
        os.link(self.source, destination)
        self.reject(self.args(output=destination), 'OUTPUT_EXISTS')
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(destination.read_bytes(), before)

    def test_native_symlink_input_leaf_and_parent_are_refused(self):
        linked = self.private / 'linked.md'
        self.symlink(linked, self.source)
        self.reject(self.args(source=linked))
        parent = self.private / 'linked directory'
        actual = self.private / 'actual directory'
        actual.mkdir()
        nested = actual / 'nested.md'
        nested.write_bytes(self.source.read_bytes())
        self.symlink(parent, actual, True)
        self.reject(self.args(source=parent / nested.name))
        self.assertFalse(self.output.exists())
        self.assertEqual(nested.read_bytes(), self.source.read_bytes())

    def test_native_symlink_output_leaf_dangling_and_parent_preserve_targets(self):
        before = self.source.read_bytes()
        self.symlink(self.output, self.source)
        self.reject()
        self.assertEqual(self.source.read_bytes(), before)
        dangling = self.private / 'dangling.docx'
        absent = self.private / 'never-created.docx'
        self.symlink(dangling, absent)
        self.reject(self.args(output=dangling))
        self.assertFalse(absent.exists())
        actual = self.private / 'actual directory'
        actual.mkdir()
        parent = self.private / 'linked directory'
        self.symlink(parent, actual, True)
        self.reject(self.args(output=parent / 'new.docx'))
        self.assertEqual(list(actual.iterdir()), [])

    @unittest.skipUnless(os.name == 'nt', 'Native Windows junction and stream fixture')
    def test_native_windows_junction_and_stream_spellings_preserve_input(self):
        actual = self.private / 'actual directory'
        actual.mkdir()
        source = actual / 'fictional.md'
        source.write_bytes(self.source.read_bytes())
        junction = self.private / 'fictional junction'
        done = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(actual)],
                              capture_output=True, timeout=30)
        self.assertEqual(done.returncode, 0, 'REQUIRED_NATIVE_JUNCTION_UNAVAILABLE')
        self.reject(self.args(source=junction / source.name))
        self.reject(self.args(output=junction / 'new.docx'))
        for value in (str(self.source) + ':fictional', str(self.source) + '.', str(self.source) + ' '):
            self.reject(self.args(source=value))
        for value in (str(self.output) + ':fictional', str(self.output) + '.', str(self.output) + ' '):
            self.reject(self.args(output=value))
        self.assertFalse(self.output.exists())
        self.assertEqual(source.read_bytes(), self.source.read_bytes())
        partial = self.private / 'partial.docx'
        self.reject(self.args(output=partial), probe='partial', reason='FICTIONAL_WRITE_FAILURE')
        self.assertEqual(partial.read_bytes()[:2], b'PK')
        self.assertEqual(partial.stat().st_size, 11)
        self.reject(self.args(output=partial), 'OUTPUT_EXISTS')
        self.call(probe='short')
        self.inspect()

    @unittest.skipIf(os.name == 'nt', 'Native POSIX FIFO fixture')
    def test_native_posix_fifo_is_refused(self):
        fifo = self.private / 'fictional.fifo'
        os.mkfifo(fifo)
        self.reject(self.args(source=fifo), 'INPUT_NOT_REGULAR')
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
