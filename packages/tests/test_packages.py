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
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('toolkit_builder', ROOT / 'packages/build.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

class Packages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='outlands-packaging-',dir=os.environ.get('OUTLANDS_TEST_TEMP'))
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
        self.assertEqual(13, len(self.catalog['systems']))
        self.assertEqual('4a19ca40f1f04bd210eedf9dd250feaf004ff137',self.catalog['source_revision'])
        self.assertEqual(75,len(self.catalog['components']))
        self.assertNotIn('import-migration-workbench',self.catalog['systems'])
        self.assertEqual(9, len(self.catalog['downloads']))

    def test_new_workbenches_run_their_complete_fictional_demos_from_fresh_zip(self):
        unpack=self.parent/'new-workbench-unpack';unpack.mkdir()
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:archive.extractall(unpack)
        package=next(unpack.iterdir())
        expected={
            'test-evidence-workbench':dict(cases=4,matched=2,unmatched=2,timeouts=1,private_export_files=13,backup_validated=True,original_operational_checks_executed=False),
            'assessment-evidence-workbench':dict(versions=8,submissions=2,finding_state='Resolved',backup_validated=True,execution_performed=False),
            'reliability-incident-workbench':dict(snapshots=10,private_export_files=9,backup_validated=True,network_probed=False,execution_performed=False),
            'backup-recovery-workbench':dict(snapshots=2,files_per_snapshot=3,snapshot_bytes=39,restored_bytes=39,private_report_files=7,index_backup_verified=True,deletion_performed=False,source_files_changed=False)}
        for name,fields in expected.items():
            source=package/'systems'/name;workspace=self.parent/('fictional-'+name)
            result=subprocess.run([sys.executable,'-B',str(source/'workbench.py'),'--workspace',str(workspace),'demo'],cwd=source,capture_output=True,text=True,encoding='utf-8',timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
            self.assertEqual(0,result.returncode,name+': '+result.stderr)
            observed=json.loads(result.stdout)
            for field,value in fields.items():self.assertEqual(value,observed[field],name+': '+field)
            self.assertTrue(observed['mode'].startswith('FICTIONAL_'))

    def test_independent_release_checker_rejects_changed_outer_asset(self):
        script=ROOT/'packages/release_check.py'
        good=subprocess.run([sys.executable,'-B',str(script),'--output',str(self.output)],capture_output=True,text=True,timeout=60)
        self.assertEqual(0,good.returncode,good.stderr)
        changed=self.parent/'altered-assets';changed.mkdir()
        for p in self.output.iterdir():(changed/p.name).write_bytes(p.read_bytes())
        (changed/'catalog.json').write_bytes((changed/'catalog.json').read_bytes()+b' ')
        bad=subprocess.run([sys.executable,'-B',str(script),'--output',str(changed)],capture_output=True,text=True,timeout=60)
        self.assertNotEqual(0,bad.returncode)
        self.assertIn('RELEASE_CHECKSUM_MISMATCH',bad.stderr)

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

    def test_windows_checkout_conversion_cannot_change_source_objects(self):
        original = builder.git
        with patch.object(builder, 'git', side_effect=lambda *args: original('-c', 'core.autocrlf=true', *args)):
            alternate = builder.public_tree(self.catalog['source_revision'])
        self.assertEqual(self.source, alternate)
        with zipfile.ZipFile(io.BytesIO(self.archive('complete'))) as archive:
            prefix = archive.namelist()[0].split('/')[0] + '/'
            modes = {name: mode for name, mode, _ in builder.git_entries(self.catalog['source_revision'])}
            for path, mode in modes.items():
                self.assertEqual(int(mode, 8), archive.getinfo(prefix + path).external_attr >> 16)

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

    def test_uncommitted_control_text_is_not_a_package_input(self):
        with patch.object(Path, 'read_text', side_effect=AssertionError('Working-tree text is not a release input')):
            builder.build(self.parent / 'committed-controls-only')

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

    def test_every_family_runs_its_workshop_from_a_fresh_archive(self):
        total = 0
        for group in self.catalog['groups']:
            family = group['id']; unpack = self.parent / ('workshop-unpack-' + family); unpack.mkdir()
            with zipfile.ZipFile(io.BytesIO(self.archive(family))) as archive: archive.extractall(unpack)
            package = next(unpack.iterdir()); workspace = self.parent / ('workshop-run-' + family)
            result = subprocess.run([sys.executable, '-I', '-B', str(package / 'workshops/run.py'),
                                     '--family', family, '--workspace', str(workspace)],
                                    cwd=package, capture_output=True, text=True, timeout=120)
            self.assertEqual(0, result.returncode, family + ': ' + result.stdout + result.stderr)
            receipt = json.loads((workspace / 'observed-results.json').read_text(encoding='utf-8'))
            self.assertEqual('PASS', receipt['status']); total += receipt['command_checks']
        self.assertEqual(33, total)

if __name__ == '__main__': unittest.main()
