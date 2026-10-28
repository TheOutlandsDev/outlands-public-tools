"""Boundary tests for downloaded archives; fixture bytes only."""
import io
import os
from pathlib import Path
import tarfile
import tempfile
import subprocess
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
    def test_default_browser_dispatch_preserves_url_without_cmd_parsing(self):
        script = r"""
const assert=require('node:assert/strict'),cp=require('node:child_process');
const calls=[];cp.spawn=(exe,args,options)=>{calls.push({exe,args,options});return {on(){},unref(){}};};
const {browser}=require(process.argv[1]);
process.env.SystemRoot=process.env.SystemRoot||'/Windows';
const url='http://127.0.0.1:32123/admin';browser(url);
assert.equal(calls.length,1);assert(calls[0].exe.endsWith('rundll32.exe'));
assert.deepEqual(calls[0].args,['url.dll,FileProtocolHandler',url]);
assert.equal(calls[0].options.windowsHide,true);
assert.throws(()=>browser('https://example.invalid/admin'));
assert.throws(()=>browser(url+'&unexpected=1'));
assert.equal(calls.length,1);
"""
        r=subprocess.run(['node','-e',script,str(Path(__file__).with_name('launch.js').resolve())],capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr.decode('utf-8',errors='replace'))

    def test_native_x64_required(self):
        with self.assertRaises(ValueError):validate_native(b'not PE')
if __name__=='__main__':unittest.main()
