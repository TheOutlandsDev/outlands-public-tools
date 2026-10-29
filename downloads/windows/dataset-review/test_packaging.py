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
from review_demo import exercise,tree

class Packaging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp=tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP'));cls.app=Path(cls.source_temp.name)/'application';cls.app.mkdir()
        manifest=subprocess.check_output(['git','show',build.APP_SOURCE+':systems/dataset-review/SOURCE-MANIFEST.json'],cwd=build.ROOT)
        names=list(json.loads(manifest)['files'])+['SOURCE-MANIFEST.json']
        for name in names:
            p=cls.app/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','show',build.APP_SOURCE+':systems/dataset-review/'+name],cwd=build.ROOT))
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
    def test_full_original_cli_dedup_holdouts_pins_exports_and_reopen(self):
        result=exercise(self.parent/'practice',self.app)
        self.assertEqual(result['command_checks'],24);self.assertEqual([result[k] for k in ('input_rows','records','test_records','approved_records','provenance_rows','exported_records','export_files')],[5,4,2,1,5,1,2])
        for key in ('independent_record_ids_and_group_splits_checked','provenance_source_rows_independently_checked','logical_state_pin_independently_checked','stale_review_refused','missing_review_checks_refused','stale_export_and_backup_refused','invalid_batch_atomicity_checked','reimport_preserves_reviews_and_pin','export_bytes_and_hashes_independently_verified','backup_integrity_and_logical_rows_checked','saved_records_reopened'):self.assertTrue(result[key])
        self.assertFalse(result['public_release_authorized']);self.assertFalse(result['export_automatically_training_only'])
    def test_existing_exercise_refused_without_writes(self):
        folder=self.parent/'practice';folder.mkdir();(folder/'operator-note.txt').write_bytes(b'fictional preserved note');before=tree(folder)
        with self.assertRaisesRegex(ValueError,'NEW_PRIVATE_EXERCISE_REQUIRED'):exercise(folder,self.app)
        self.assertEqual(tree(folder),before)
    def test_gui_reopens_without_import_and_releases_owned_lock(self):
        from dataset_workbench import application as app,web
        journal=self.parent/'journal'
        for repeat in range(2):
            with patch.object(sys,'argv',['launch.py','--demo','--workspace',str(journal),'--no-browser']),patch.object(launch,'check_package',return_value={'package_version':'test'}),patch.object(web.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),redirect_stdout(io.StringIO()):launch.main()
            self.assertFalse((journal/'.session-lock').exists())
            with app.Workbench(journal) as controller:self.assertEqual(controller.state()['total'],0)
            if not repeat:before=tree(journal)
            else:self.assertEqual(tree(journal),before)
    def test_independent_export_reader_rejects_changed_payload(self):
        from dataset_workbench import application as a
        from review_demo import fixture_ids,verify_export
        journal=self.parent/'export';a.Workbench.initialize(journal)
        with a.Workbench(journal) as app:
            app.mutate('import',dict(expected=app.state()['head'],file='inbox/sample-records.jsonl'));fixture=fixture_ids(self.app)
            app.mutate('review',dict(expected=app.state()['head'],id=fixture['train'],decision='approved',actor='sample_reviewer',note='Fictional review',checks=dict.fromkeys(('quality','privacy','rights','context'),True)))
            result=app.mutate('export',dict(expected=app.state()['head']))['result'];verify_export(journal,result,fixture,True)
            (journal/result['directory']/'approved.jsonl').write_bytes(b'changed')
            with self.assertRaises(AssertionError):verify_export(journal,result,fixture,True)
    def test_package_internal_state_refused(self):
        with patch.object(sys,'argv',['launch.py','--workspace',str(launch.ROOT/'private')]),patch.object(launch,'check_package',return_value={'package_version':'test'}),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as caught:launch.main()
        self.assertEqual(caught.exception.code,2);self.assertFalse((launch.ROOT/'private').exists())

if __name__=='__main__':unittest.main()
