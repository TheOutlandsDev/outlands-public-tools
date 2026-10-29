"""Portable archive refusal and fictional update preservation boundaries."""
import io
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile
import build
import launch
import update_demo

sys.path.insert(0,str(build.ROOT/'systems/release-update-workbench'))
from releases import runtime as r,web
update_demo.APP=build.ROOT/'systems/release-update-workbench'

class PortableBoundaries(unittest.TestCase):
    def test_modified_payload_is_refused_before_starting_the_application(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);original=b'fictional original';(root/'payload.txt').write_bytes(b'fictional changed')
            (root/'PACKAGE-MANIFEST.json').write_text(json.dumps(dict(files=[dict(path='payload.txt',bytes=len(original),sha256=hashlib.sha256(original).hexdigest())])))
            with patch.object(launch,'ROOT',root),self.assertRaisesRegex(ValueError,'Package changed or incomplete'):launch.check_package()

    def test_changed_upstream_digest_refused(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            path=Path(folder)/'bad.zip';path.write_bytes(b'fictional')
            with self.assertRaisesRegex(ValueError,'UPSTREAM_DIGEST_MISMATCH'):build.download('https://example.invalid','0'*64,100,path)

    def test_ambiguous_member_names_refused(self):
        for names in [('../escape',),('/absolute',),('bad//member',),('C:stream',),('duplicate','duplicate'),('Name','name')]:
            with self.subTest(names=names):
                data=io.BytesIO()
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',UserWarning)
                    with zipfile.ZipFile(data,'w') as archive:
                        for name in names:archive.writestr(name,b'fictional')
                with self.assertRaisesRegex(ValueError,'UNEXPECTED_ARCHIVE_MEMBER'):build.members(data.getvalue())

    def test_symlink_zip_member_refused(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:
            info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16;archive.writestr(info,b'target')
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_ARCHIVE_MEMBER'):build.members(data.getvalue())

    def test_exercise_checks_differences_scoped_approval_revocation_and_preservation(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            result=update_demo.exercise(Path(folder)/'new instance')
            self.assertEqual([result[k] for k in ('snapshots','files_per_snapshot','blockers_before','blockers_after','private_handoff_files','command_checks')],[2,4,5,0,8,34])
            self.assertEqual(result['file_counts'],dict(ADD=1,REMOVE=1,REPLACE=2,UNCHANGED=1))
            for key in ('blocked_approval_refused','unapproved_export_refused','revoked_export_refused','input_bytes_unchanged','copied_snapshots_unchanged','fictional_target_unchanged'):self.assertTrue(result[key])
            self.assertEqual(result['manual_checkpoints'],'NOT_PERFORMED')
            for key in ('new_plan_inherits_approval','target_updates_performed','programs_executed','network_probed','rollback_restore_performed'):self.assertFalse(result[key])

    def test_exercise_refuses_existing_state_before_writes(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);(root/'keep.txt').write_bytes(b'fictional preserved')
            with self.assertRaisesRegex(ValueError,'EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE'):update_demo.exercise(root)
            self.assertEqual(list(root.iterdir()),[root/'keep.txt']);self.assertEqual((root/'keep.txt').read_bytes(),b'fictional preserved')

    def test_browser_dispatch_uses_owned_loopback_and_reopens_without_reseed(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder)/'private'
            for repeat in range(2):
                with patch.object(sys,'argv',['launch.py','--demo','--workspace',str(root)]),patch.object(launch,'check_package',return_value={}),patch.object(web.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),patch.object(launch.webbrowser,'open',return_value=True) as browser:
                    launch.main();self.assertRegex(browser.call_args.args[0],r'^http://127\.0\.0\.1:[0-9]+/$')
                if not repeat:(root/'inbox/operator-note.txt').write_bytes(b'fictional saved change')
            self.assertEqual((root/'inbox/operator-note.txt').read_bytes(),b'fictional saved change')

    def test_package_internal_private_state_refused(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);target=root/'state'
            with patch.object(launch,'ROOT',root),patch.object(launch,'check_package',return_value={}),patch.object(sys,'argv',['launch.py','--workspace',str(target)]):
                with self.assertRaises(SystemExit) as error:launch.main()
                self.assertEqual(error.exception.code,2);self.assertFalse(target.exists())

if __name__=='__main__':unittest.main()
