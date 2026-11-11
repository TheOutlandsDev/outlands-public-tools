"""Original six fictional workspace fixtures, isolated from unrelated tools."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('workspace_original_fixture',Path(__file__).resolve().parents[1]/'workspace.py')
workspace=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workspace)

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

class WorkspaceTests(Fixture):
    def test_default_plan_has_no_writes(self):
        self.assertEqual(workspace.create(self.root,'demo')['status'],'PLAN_ONLY')
        self.assertEqual(list(self.root.iterdir()),[])
    def test_created_copies_are_byte_identical_and_neutrally_named(self):
        source=self.parent/'input.txt';data=b'fictional input\r\n';source.write_bytes(data)
        result=workspace.create(self.root,'demo',source,True)
        self.assertTrue(result['source_verified'])
        for folder in ('original','working'):self.assertEqual((self.root/'demo'/folder/'intake.bin').read_bytes(),data)
        metadata=json.loads((self.root/'demo/original/SOURCE.json').read_text())
        self.assertEqual(metadata['sha256'],hashlib.sha256(data).hexdigest())
        self.assertNotIn(str(source),(self.root/'demo/CONTROL.md').read_text())
        self.assertEqual(source.read_bytes(),data)
    def test_existing_workspace_not_overwritten(self):
        workspace.create(self.root,'demo',commit=True)
        with self.assertRaises(workspace.WorkspaceError):workspace.create(self.root,'demo',commit=True)
        self.assertTrue((self.root/'demo/CONTROL.md').exists())
    def test_invalid_and_reserved_names_rejected(self):
        for name in ('../escape','CON','con','a/b','hidden.name',''):
            with self.subTest(name=name),self.assertRaises(workspace.WorkspaceError):workspace.create(self.root,name,commit=True)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_invalid_source_does_not_create_partial_workspace(self):
        with self.assertRaises(OSError):workspace.create(self.root,'demo',self.parent/'missing',True)
        self.assertFalse((self.root/'demo').exists())
    def test_workspace_has_private_ignore_default(self):
        workspace.create(self.root,'demo',commit=True)
        self.assertEqual((self.root/'demo/.gitignore').read_text(),'*\n')

if __name__=='__main__':unittest.main()
