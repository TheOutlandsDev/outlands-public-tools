"""Portable archive refusal and fictional setup preservation boundaries."""
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
import setup_demo

sys.path.insert(0,str(build.ROOT/'systems/environment-setup-workbench'))
from setupplan import runtime as r,web
setup_demo.APP=build.ROOT/'systems/environment-setup-workbench'

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

    def test_exercise_checks_blockers_review_scope_hashes_and_persistence(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            result=setup_demo.exercise(Path(folder)/'new instance')
            self.assertEqual([result[k] for k in ('checks','blocked_steps_before','blocked_steps_after','private_handoff_files','command_checks')],[9,3,0,6,19])
            self.assertEqual(result['ordered_steps'],['prepare','review','handoff'])
            self.assertTrue(result['review_refused']);self.assertTrue(result['input_bytes_unchanged'])
            self.assertEqual(result['manual_verifications'],'NOT_PERFORMED')
            for key in ('runtime_verified','programs_executed','network_probed'):self.assertFalse(result[key])

    def test_exercise_refuses_existing_state_before_writes(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as folder:
            root=Path(folder);(root/'keep.txt').write_bytes(b'fictional preserved')
            with self.assertRaisesRegex(ValueError,'EXERCISE_REQUIRES_NEW_ABSOLUTE_INSTANCE'):setup_demo.exercise(root)
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
