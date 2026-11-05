"""Determinism, exact source selection, archive metadata and tamper refusal."""
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

from build import archive_bytes, build, payload, plan, safe_name, source_files
from verify import verify, verify_archive
from public_download import allowed


class ModelRoutingPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = plan()
        cls.files = payload(cls.value, source_files(cls.value))
        cls.raw = archive_bytes(cls.value, cls.files)

    def test_exact_tools_and_deterministic_bytes(self):
        self.assertEqual(len(self.value['tools']), 4)
        self.assertEqual(len(self.files), 75)
        self.assertEqual(self.raw, archive_bytes(self.value, self.files))
        self.assertEqual(verify_archive(self.raw, self.value)['archive_members'], 75)

    def test_fresh_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(prefix='routing4-build-test-') as directory:
            result = build(directory)
            self.assertEqual(result['sha256'], self.value['expected_zip_sha256'])
            archive = Path(directory) / result['filename']
            self.assertEqual(verify(archive, Path(directory) / 'SHA256SUMS.txt')['status'], 'PASS')
            with self.assertRaises(FileExistsError):
                build(directory)

    def test_path_metadata_and_content_tamper_refused(self):
        with self.assertRaises(ValueError):
            safe_name('../private.txt')
        with self.assertRaises(ValueError):
            safe_name('tools/example/.env')
        changed = dict(self.files)
        changed['README.md'] = b'changed\n'
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_PIN_MISMATCH'):
            verify_archive(archive_bytes(self.value, changed), self.value)
        stream = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(self.raw)) as original, zipfile.ZipFile(stream, 'w') as altered:
            for info in original.infolist():
                if info.filename.endswith('/README.md'):
                    info.comment = b'host metadata'
                altered.writestr(info, original.read(info))
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_METADATA_REFUSED'):
            verify_archive(stream.getvalue(), self.value)

    def test_public_download_redirect_hosts_are_bounded(self):
        self.assertTrue(allowed('https://github.com/example/release'))
        self.assertTrue(allowed('https://release-assets.githubusercontent.com/example'))
        self.assertFalse(allowed('http://github.com/example'))
        self.assertFalse(allowed('https://github.com.evil.example/example'))


if __name__ == '__main__':
    unittest.main()
