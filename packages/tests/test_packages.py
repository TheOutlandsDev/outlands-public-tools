import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('toolkit_builder', ROOT / 'packages/build.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

class Packages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='outlands-packaging-')
        cls.parent = Path(cls.scratch.name)
        cls.output = cls.parent / 'downloads'
        builder.build(cls.output)
        cls.catalog = json.loads((cls.output / 'catalog.json').read_text(encoding='utf-8'))
        cls.source = builder.public_tree(cls.catalog['source_revision'])

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def archive(self, name='release-qa'):
        record = next(x for x in self.catalog['downloads'] if x['id'] == name)
        return (self.output / record['filename']).read_bytes()

    def mutate(self, mutation):
        with zipfile.ZipFile(io.BytesIO(self.archive())) as archive:
            files = {p.split('/', 1)[1]: archive.read(p) for p in archive.namelist()}
        mutation(files)
        return builder.zip_bytes(files, 'fictional-package')

    def test_every_tool_exactly_once_and_all_systems_present(self):
        builder.validate_catalog(self.catalog, self.source)
        names = [n for g in self.catalog['groups'] for n in g['tools']]
        self.assertEqual(62, len(names))
        self.assertEqual(6, len(self.catalog['systems']))
        self.assertEqual(9, len(self.catalog['downloads']))

    def test_missing_and_duplicate_components_refused(self):
        for mode in ('missing', 'duplicate'):
            bad = copy.deepcopy(self.catalog)
            if mode == 'missing': bad['groups'][0]['tools'].pop()
            else: bad['groups'][0]['tools'].append(bad['groups'][0]['tools'][0])
            with self.assertRaisesRegex(ValueError, 'TOOL_COVERAGE_MISMATCH'):
                builder.validate_catalog(bad, self.source)

    def test_all_manifests_and_preserved_public_bytes(self):
        for record in self.catalog['downloads']:
            body = (self.output / record['filename']).read_bytes()
            manifest = builder.verify_archive(body)
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                prefix = archive.namelist()[0].split('/')[0] + '/'
                for path, entry in manifest['files'].items():
                    if entry['origin'] == 'published-source':
                        self.assertEqual(self.source[path], archive.read(prefix + path))
            self.assertEqual(record['sha256'], builder.digest(body))

    def test_complete_contains_every_source_file(self):
        manifest = builder.verify_archive(self.archive('complete'))
        self.assertTrue(set(self.source).issubset(manifest['files']))

    def test_family_does_not_include_other_tool_implementations(self):
        for group in self.catalog['groups']:
            manifest = builder.verify_archive(self.archive(group['id']))
            found = {p.split('/')[1] for p in manifest['files'] if p.startswith('tools/')}
            self.assertEqual(set(group['tools']), found)

    def test_recomputed_crc_cannot_hide_changed_file(self):
        def change(files): files['START-HERE.md'] += b'changed fictional marker\n'
        with self.assertRaisesRegex(ValueError, 'FILE_HASH_MISMATCH'):
            builder.verify_archive(self.mutate(change))

    def test_unlisted_file_refused(self):
        with self.assertRaisesRegex(ValueError, 'INVENTORY_MISMATCH'):
            builder.verify_archive(self.mutate(lambda files: files.update({'unexpected.txt': b'fictional'})))

    def test_missing_file_refused(self):
        with self.assertRaisesRegex(ValueError, 'INVENTORY_MISMATCH'):
            builder.verify_archive(self.mutate(lambda files: files.pop('START-HERE.md')))

    def test_unsafe_paths_refused(self):
        for path in ('../outside', '/absolute', 'a\\b', 'C:/sample', 'a/.git/config', 'a/__pycache__/x'):
            with self.subTest(path=path), self.assertRaises(ValueError): builder.safe_name(path)

    def test_archive_is_deterministic_across_input_order(self):
        one = builder.zip_bytes({'b.txt': b'b', 'a.txt': b'a'}, 'demo')
        two = builder.zip_bytes({'a.txt': b'a', 'b.txt': b'b'}, 'demo')
        self.assertEqual(one, two)
        with zipfile.ZipFile(io.BytesIO(one)) as archive:
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in archive.infolist()))

    def test_existing_output_refused(self):
        with self.assertRaisesRegex(ValueError, 'NEW_EXTERNAL_OUTPUT_REQUIRED'):
            builder.build(self.output)

    def test_relative_external_output_is_resolved_before_boundary_check(self):
        with tempfile.TemporaryDirectory(prefix='outlands-relative-', dir=ROOT.parent) as scratch:
            destination = Path(scratch) / 'relative-output'
            builder.build(os.path.relpath(destination, ROOT))
            self.assertTrue((destination / 'SHA256SUMS.txt').is_file())

    def test_fresh_archive_runs_actual_fictional_workflows(self):
        for name in ('complete', 'release-qa'):
            unpack = self.parent / ('unpacked-' + name); unpack.mkdir()
            with zipfile.ZipFile(io.BytesIO(self.archive(name))) as archive: archive.extractall(unpack)
            package = next(unpack.iterdir())
            result = subprocess.run([sys.executable, '-I', '-B', str(package / 'methodology/worked-examples/run_examples.py'),
                                     '--workspace', str(self.parent / ('examples-' + name))],
                                    cwd=package, capture_output=True, text=True, timeout=120)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(3, receipt['examples_passed'])
            self.assertEqual(8, receipt['command_checks'])
            second = subprocess.run([sys.executable, '-I', '-B', str(package / 'methodology/worked-examples/run_examples.py'),
                                     '--workspace', str(self.parent / ('examples-' + name))],
                                    cwd=package, capture_output=True, text=True, timeout=20)
            self.assertEqual(1, second.returncode)

if __name__ == '__main__': unittest.main()
