import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('workbench_download_builder',ROOT/'downloads/workbenches/build.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class HandoffPackages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='fictional-workbench-packages-');cls.parent=Path(cls.temp.name)
        cls.output=cls.parent/'first';builder.build(cls.output)
        cls.matrix=json.loads((cls.output/'release-matrix.json').read_bytes())
        cls.source=builder.toolkit.public_tree(cls.matrix['applications'][0]['source_revision'])

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_wrapper_keeps_every_application_blob_and_manifest_exact(self):
        for app in self.matrix['applications']:
            with zipfile.ZipFile(self.output/app['filename']) as archive:
                prefix=app['app']+'-'+app['version']+'/'
                source='systems/'+app['app']+'/'
                expected={p[len(source):]:b for p,b in self.source.items() if p.startswith(source)}
                actual={p[len(prefix+'application/'):]:archive.read(p) for p in archive.namelist() if p.startswith(prefix+'application/')}
                self.assertEqual(expected,actual)
                self.assertEqual({prefix+'START-HERE.md',prefix+'PROVENANCE.md',prefix+'PACKAGE-MANIFEST.json'},set(archive.namelist())-{prefix+'application/'+p for p in expected})
                self.assertIn(b'application/workbench.py',archive.read(prefix+'START-HERE.md'))
                self.assertIn(b'application source declaring 0.1.0',archive.read(prefix+'START-HERE.md'))

    def test_rebuilds_have_identical_zip_matrix_and_checksum_bytes(self):
        second=self.parent/'second';builder.build(second)
        self.assertEqual({p.name:p.read_bytes() for p in self.output.iterdir()},{p.name:p.read_bytes() for p in second.iterdir()})

    def test_member_changes_cannot_be_hidden_by_recomputing_zip_crc(self):
        app=self.matrix['applications'][0]
        with zipfile.ZipFile(self.output/app['filename']) as archive:
            prefix=app['app']+'-'+app['version']+'/'
            files={p[len(prefix):]:archive.read(p) for p in archive.namelist()}
        files['application/workbench.py']+=b'\n# changed synthetic test\n'
        with self.assertRaisesRegex(ValueError,'FILE_HASH_MISMATCH'):
            builder.toolkit.verify_archive(builder.toolkit.zip_bytes(files,'fictional'))

    def test_existing_output_is_refused_without_modification(self):
        before={p.name:p.read_bytes() for p in self.output.iterdir()}
        with self.assertRaisesRegex(ValueError,'NEW_EXTERNAL_OUTPUT_REQUIRED'):builder.build(self.output)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.output.iterdir()})


if __name__=='__main__':unittest.main()
