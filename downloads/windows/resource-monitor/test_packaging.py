"""Upstream/archive and browser-dispatch boundaries, no real browser or metrics."""
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from build import members,download
class Boundaries(unittest.TestCase):
    def test_changed_upstream_refused(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('OUTLANDS_TEST_TEMP')) as d:
            p=Path(d)/'changed';p.write_bytes(b'changed')
            with self.assertRaises(ValueError):download('unused','0'*64,100,p)
    def test_raw_zip_paths_and_duplicate_refused(self):
        for n in ('../outside','/absolute','a/./b','a//b','a\\b','drive:x'):
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:z.writestr(n.replace('\\','|'),b'fixture')
            raw=b.getvalue().replace(b'a|b',b'a\\b')
            with self.assertRaises(ValueError):members(raw)
    def test_browser_preserves_capability_fragment_and_refuses_foreign_urls(self):
        spec=importlib.util.spec_from_file_location('portable_monitor',Path(__file__).with_name('launch.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        good='http://127.0.0.1:32123/#token='+'a'*43
        with patch.object(module.webbrowser,'open',return_value=True) as opened:
            self.assertTrue(module.open_browser(good));opened.assert_called_once_with(good)
            for bad in ('https://example.invalid/#token='+'a'*43,'http://user@127.0.0.1:32123/#token='+'a'*43,'http://127.0.0.1:32123/#token=short'):
                with self.assertRaises(ValueError):module.open_browser(bad)
            self.assertEqual(opened.call_count,1)
if __name__=='__main__':unittest.main()
