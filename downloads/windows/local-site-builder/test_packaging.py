"""Boundary tests for downloaded archives; fixture bytes only."""
import io
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from build import members,tar_members,download,validate_native
class Boundaries(unittest.TestCase):
    def test_changed_upstream_refused(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("OUTLANDS_TEST_TEMP")) as d:
            p=Path(d)/'changed';p.write_bytes(b'changed')
            with self.assertRaises(ValueError):download('unused','0'*64,100,p)
    def test_zip_traversal_and_alias_refused(self):
        for n in ('../outside','/absolute','a/./b','a//b','a\\b','drive:x'):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:z.writestr(n.replace('\\','|'),b'fixture')
            raw=b.getvalue().replace(b'a|b',b'a\\b')
            with self.assertRaises(ValueError):members(raw)
    def test_npm_special_and_traversal_refused(self):
        for n,kind in [('package/../outside',tarfile.REGTYPE),('package/link',tarfile.SYMTYPE)]:
            b=io.BytesIO()
            with tarfile.open(fileobj=b,mode='w:gz') as t:
                i=tarfile.TarInfo(n);i.type=kind;t.addfile(i)
            with self.assertRaises(ValueError):tar_members(b.getvalue())
    def test_native_x64_required(self):
        with self.assertRaises(ValueError):validate_native(b'not PE')
if __name__=='__main__':unittest.main()
