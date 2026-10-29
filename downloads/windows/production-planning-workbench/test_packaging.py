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
from planning_demo import exercise,tree

class Packaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));cls.app=Path(cls.source_temp.name)/'application';cls.app.mkdir()
        manifest=subprocess.check_output(['git','show',build.APP_SOURCE+':systems/production-planning-workbench/SOURCE-MANIFEST.json'],cwd=build.ROOT)
        names=list(json.loads(manifest)['files'])+['SOURCE-MANIFEST.json']
        for name in names:
            p=cls.app/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',build.APP_SOURCE+':systems/production-planning-workbench/'+name],cwd=build.ROOT))
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
    def test_full_original_cli_exercise_numeric_and_restart_oracles(self):
        result=exercise(self.parent/'practice',self.app)
        self.assertEqual(result['command_checks'],14);self.assertEqual(result['initial_totals'],[160,25,85,50,3]);self.assertEqual(result['final_totals'],[170,25,85,60,4])
        for key in ('stale_action_refused','stale_revision_refused','old_report_unchanged','original_inputs_unchanged','report_hashes_independently_verified','saved_revision_reopened'):self.assertTrue(result[key])
        self.assertFalse(result['external_system_writes']);self.assertFalse(result['shipment_execution_authorized'])
    def test_existing_exercise_refused_without_writes(self):
        folder=self.parent/'practice';folder.mkdir();(folder/'operator-note.txt').write_bytes(b'fictional preserved note');before=tree(folder)
        with self.assertRaisesRegex(ValueError,'NEW_PRIVATE_EXERCISE_REQUIRED'):exercise(folder,self.app)
        self.assertEqual(tree(folder),before)
    def test_gui_reopens_without_reseed_and_closes_session_lock(self):
        from planning import application as app,runtime,web
        journal=self.parent/'journal'
        for repeat in range(2):
            with patch.object(sys,'argv',['launch.py','--demo','--workspace',str(journal),'--no-browser']),patch.object(launch,'check_package',return_value={'package_version':'test'}),patch.object(web.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),redirect_stdout(io.StringIO()):launch.main()
            self.assertIsNone(runtime.ROOT);self.assertFalse((journal/'.session-lock').exists())
            if not repeat:before=tree(journal)
            else:self.assertEqual(tree(journal),before)
    def test_wheel_record_corruption_and_uninventoried_file_refused(self):
        import base64,hashlib
        content=b'fictional';record='sample.dist-info/RECORD'
        digest=base64.urlsafe_b64encode(hashlib.sha256(content).digest()).decode().rstrip('=')
        wheel={'sample.py':content,record:('sample.py,sha256='+digest+',9\n'+record+',,\n').encode()}
        build.verify_record(wheel)
        wheel['sample.py']=b'changed'
        with self.assertRaisesRegex(ValueError,'WHEEL_RECORD_HASH_MISMATCH'):build.verify_record(wheel)
        wheel['sample.py']=content;wheel['extra.py']=b'fictional'
        with self.assertRaisesRegex(ValueError,'WHEEL_RECORD_INVENTORY_MISMATCH'):build.verify_record(wheel)
    def test_package_internal_state_refused(self):
        with patch.object(sys,'argv',['launch.py','--workspace',str(launch.ROOT/'private')]),patch.object(launch,'check_package',return_value={'package_version':'test'}),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:launch.main()
        self.assertEqual(caught.exception.code,2);self.assertFalse((launch.ROOT/'private').exists())

if __name__=='__main__':unittest.main()
