"""Exercise archive refusal, fresh state and preservation using invented files."""
import io
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
sys.path.insert(0,str(build.ROOT/'systems/backup-recovery-workbench'))
from recovery import runtime as r,web
from recovery_demo import exercise


class PortableBoundaries(unittest.TestCase):
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
                    with zipfile.ZipFile(data,'w') as z:
                        for name in names:z.writestr(name,b'fictional')
                with self.assertRaisesRegex(ValueError,'UNEXPECTED_ARCHIVE_MEMBER'):build.members(data.getvalue())

    def test_symlink_zip_member_refused(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            info=zipfile.ZipInfo('link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,b'target')
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_ARCHIVE_MEMBER'):build.members(data.getvalue())

    def test_fictional_recovery_and_damaged_copy(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            try:
                result=exercise(Path(folder)/'new instance')
                self.assertEqual((result['files'],result['bytes'],result['completed_jobs'],result['failed_jobs']),(3,39,3,1))
                self.assertEqual(result['damaged_copy_error'],'SNAPSHOT_CONTENT_MISMATCH')
                self.assertTrue(result['changed_source_preserved']);self.assertTrue(result['original_snapshot_unchanged'])
                self.assertFalse(result['damaged_copy_restore_created'])
            finally:r.close()

    def test_exercise_refuses_existing_state_before_writes(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);(root/'keep.txt').write_bytes(b'fictional preserved')
            with self.assertRaisesRegex(ValueError,'EXERCISE_REQUIRES_NEW_INSTANCE'):exercise(root)
            self.assertEqual(list(root.iterdir()),[root/'keep.txt'])
            self.assertEqual((root/'keep.txt').read_bytes(),b'fictional preserved')

    def test_browser_dispatch_uses_owned_loopback_and_reopens_without_reseed(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder)/'private'
            for repeat in range(2):
                with patch.object(sys,'argv',['launch.py','--demo','--workspace',str(root)]),patch.object(launch,'check_package',return_value={}),patch.object(web.LocalServer,'serve_forever',side_effect=KeyboardInterrupt),patch.object(launch.webbrowser,'open',return_value=True) as browser:
                    launch.main();self.assertRegex(browser.call_args.args[0],r'^http://127\.0\.0\.1:[0-9]+/$')
                if not repeat:(root/'inbox/sample-files-v1/empty.txt').write_bytes(b'fictional saved change')
            self.assertEqual((root/'inbox/sample-files-v1/empty.txt').read_bytes(),b'fictional saved change')

    def test_package_internal_private_state_refused(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);target=root/'state'
            with patch.object(launch,'ROOT',root),patch.object(launch,'check_package',return_value={}),patch.object(sys,'argv',['launch.py','--workspace',str(target)]):
                with self.assertRaises(SystemExit) as error:launch.main()
                self.assertEqual(error.exception.code,2);self.assertFalse(target.exists())


if __name__=='__main__':unittest.main()
