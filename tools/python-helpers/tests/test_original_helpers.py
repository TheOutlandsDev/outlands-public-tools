"""Original five fictional helper fixtures, isolated from unrelated tools."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('helpers_original_fixture',Path(__file__).resolve().parents[1]/'helpers.py')
helpers=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helpers)

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

class HelperTests(Fixture):
    def test_nested_redaction_preserves_original(self):
        value={'items':[{'API-Key':'x'*16}],'visible':'hello'}
        redacted=helpers.redact_structure(value)
        self.assertEqual(redacted['items'][0]['API-Key'],'<redacted>')
        self.assertEqual(value['items'][0]['API-Key'],'x'*16)
    def test_redaction_does_not_claim_free_text_anonymity(self):
        self.assertEqual(helpers.redact_structure({'note':'ordinary text'}),{'note':'ordinary text'})
    def test_depth_and_non_json_types_rejected(self):
        with self.assertRaises(helpers.HelperError):helpers.redact_structure({'items':[[[1]]]},max_depth=1)
        with self.assertRaises(helpers.HelperError):helpers.redact_structure({'object':object()})
    def test_bounded_json_object(self):
        path=self.write('data.json','{"ok":true}')
        self.assertEqual(helpers.load_json_object(path),{'ok':True})
        with self.assertRaises(helpers.HelperError):helpers.load_json_object(path,max_bytes=2)
    def test_invalid_json_errors_omit_source_values_and_paths(self):
        path=self.write('data.json','not valid json')
        with self.assertRaises(helpers.HelperError) as error:helpers.load_json_object(path)
        self.assertNotIn(str(path),str(error.exception));self.assertNotIn('not valid',str(error.exception))

if __name__=='__main__':unittest.main()
