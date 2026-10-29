"""Package boundaries and one complete, original-CLI fictional workflow."""
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import build
import launch
from workflow_demo import exercise,tree

class Packaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));cls.app=Path(cls.source_temp.name)/'application';cls.app.mkdir()
        manifest=subprocess.check_output(['git','show',build.APP_SOURCE+':systems/assessment-evidence-workbench/SOURCE-MANIFEST.json'],cwd=build.ROOT)
        names=list(json.loads(manifest)['files'])+['SOURCE-MANIFEST.json']
        for name in names:
            p=cls.app/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',build.APP_SOURCE+':systems/assessment-evidence-workbench/'+name],cwd=build.ROOT))
        sys.path.insert(0,str(cls.app))
    @classmethod
    def tearDownClass(cls):cls.source_temp.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name)
    def test_changed_upstream_digest_refused(self):
        p=self.parent/'upstream.zip';p.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'UPSTREAM_DIGEST_MISMATCH'):build.download('https://example.invalid/source','0'*64,1024,p)
    def test_unsafe_ambiguous_and_duplicate_zip_names_refused(self):
        for names in [('/file',),('../file',),('a/./file',),('a//file',),('a\\file',),('C:file',),('file','FILE')]:
            raw=io.BytesIO()
            with zipfile.ZipFile(raw,'w') as z:
                for name in names:
                    info=zipfile.ZipInfo('fixture');info.filename=info.orig_filename=name
                    z.writestr(info,b'fictional')
            with self.subTest(names=names),self.assertRaises(ValueError):build.members(raw.getvalue())
    def test_link_zip_member_refused(self):
        raw=io.BytesIO();info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
        with zipfile.ZipFile(raw,'w') as z:z.writestr(info,b'elsewhere')
        with self.assertRaises(ValueError):build.members(raw.getvalue())
    def test_changed_payload_refused_before_any_application_start(self):
        folder=self.parent/'package';folder.mkdir();(folder/'sample.txt').write_bytes(b'changed');(folder/'PACKAGE-MANIFEST.json').write_text(json.dumps(dict(files=[dict(path='sample.txt',bytes=8,sha256='0'*64)])))
        with patch.object(launch,'ROOT',folder),self.assertRaisesRegex(ValueError,'Package changed or incomplete'):launch.check_package()
    def test_full_cli_workflow_history_export_backup_and_reopen(self):
        result=exercise(self.parent/'practice',self.app)
        self.assertEqual(result['command_checks'],32);self.assertEqual(result['private_export_files'],6)
        for key in ('independent_revision_and_receipt_hashes','independent_export_members_and_hashes','stale_change_refused_without_writes','review_refused_without_writes','old_exports_unchanged','database_backup_integrity_and_rows','state_reopened_without_replay'):self.assertTrue(result[key])
        self.assertTrue(result['operator_assertions_unverified']);self.assertFalse(result['execution_performed']);self.assertFalse(result['publication_authorized'])
    def test_existing_exercise_refused_without_writes(self):
        folder=self.parent/'practice';folder.mkdir();(folder/'operator-note.txt').write_bytes(b'fictional preserved note');before=tree(folder)
        with self.assertRaises(ValueError):exercise(folder,self.app)
        self.assertEqual(before,tree(folder))
    def test_demo_gui_initializes_empty_then_reopens_without_reseed(self):
        from assessment import application as app,runtime as r,web
        journal=self.parent/'journal'
        for repeat in range(2):
            with patch.object(sys,'argv',['launch.py','--demo','--workspace',str(journal),'--no-browser']),patch.object(launch,'check_package',return_value={'package_version':'test'}),patch.object(web.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),redirect_stdout(io.StringIO()):launch.main()
            self.assertFalse((journal/'.session-lock').exists());r.configure(journal)
            try:self.assertEqual(app.assessments(),dict(assessments=[]))
            finally:r.close()
            if not repeat:before=tree(journal)
            else:self.assertEqual(tree(journal),before)
    def test_independent_export_reader_refuses_changed_member(self):
        from assessment import application as app,runtime as r
        from workflow_demo import verify_export
        journal=self.parent/'export';r.configure(journal,create=True)
        try:
            r.initialize();app.demo();record=app.assessment('sample_assessment');folder=next((journal/'reports').iterdir());result=dict(directory=folder.relative_to(journal).as_posix(),manifest=json.loads((folder/'manifest.json').read_bytes()));verify_export(journal,result,record,8)
            (folder/'history.json').write_bytes((folder/'history.json').read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError,'EXPORT_HASH_FAILED'):verify_export(journal,result,record,8)
        finally:r.close()
    def test_package_internal_state_refused(self):
        with patch.object(sys,'argv',['launch.py','--workspace',str(launch.ROOT/'private')]),patch.object(launch,'check_package',return_value={'package_version':'test'}),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:launch.main()
        self.assertEqual(caught.exception.code,2);self.assertFalse((launch.ROOT/'private').exists())

if __name__=='__main__':unittest.main()
