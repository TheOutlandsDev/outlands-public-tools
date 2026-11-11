"""Original five fictional documentation fixtures, isolated from unrelated tools."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('docs_original_fixture',Path(__file__).resolve().parents[1]/'docs_check.py')
docs=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)

class Fixture(unittest.TestCase):
    def setUp(self):
        temp_parent=Path(os.environ.get('OUTLANDS_TEST_TEMP',tempfile.gettempdir())).resolve()
        self.temporary=tempfile.TemporaryDirectory(dir=temp_parent)
        def cleanup():
            target=Path(self.temporary.name).resolve()
            if target==temp_parent or not target.is_relative_to(temp_parent):raise RuntimeError('UNEXPECTED_CLEANUP_TARGET')
            self.temporary.cleanup()
        self.addCleanup(cleanup)
        self.parent=Path(self.temporary.name);self.root=self.parent/'export';self.root.mkdir()
    def write(self,name,text):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8');return path

class DocumentationTests(Fixture):
    def test_local_links_and_valid_json(self):
        self.write('README.md','[usage](docs/usage.md)\n[site](https://example.org)')
        self.write('docs/usage.md','# Usage');self.write('sample.json','{"demo":true}')
        self.assertEqual(docs.check(self.root)['status'],'PASS')
    def test_missing_escaping_and_local_absolute_links_fail(self):
        self.write('README.md','[missing](absent.md)\n[escape](../outside.md)')
        self.assertEqual(len(docs.check(self.root)['findings']),2)
    def test_fenced_and_inline_code_not_treated_as_links(self):
        self.write('README.md','```text\n[x](missing)\n```\n`[x](missing)`')
        self.assertEqual(docs.check(self.root)['status'],'PASS')
    def test_json_nonstandard_constants_rejected(self):
        self.write('sample.json','{"demo":NaN}')
        self.assertEqual(docs.check(self.root)['findings'][0]['rule'],'INVALID_JSON')
    def test_reference_and_encoded_links(self):
        self.write('README.md','[ref]: <some%20file.md>\n[ref]')
        self.write('some file.md','# Demo')
        self.assertEqual(docs.check(self.root)['status'],'PASS')

if __name__=='__main__':unittest.main()
