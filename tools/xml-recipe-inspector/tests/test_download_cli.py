"""Fresh-process checks with two copied runtime modules and invented XML only."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_xml_windows import fixture

RUNTIME = ("xml_recipe_inspector.py", "xml_windows.py")
BOOTSTRAP = """import os,runpy,socket,subprocess,sys
from pathlib import Path
def deny(*args,**kwargs): raise AssertionError('NO_EXTERNAL_ACTION')
socket.socket=socket.create_connection=subprocess.Popen=os.system=deny
for action in (socket.socket,socket.create_connection,subprocess.Popen,os.system):
    try: action()
    except AssertionError: pass
    else: raise AssertionError('DENIAL_GUARD_FAILED')
folder=Path(sys.argv[1]);script=folder/'xml_recipe_inspector.py'
sys.path.insert(0,str(folder));sys.argv=[str(script)]+sys.argv[2:]
runpy.run_path(str(script),run_name='__main__')
"""


class DownloadCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="xml-fictional-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = self.root / "runtime"
        self.app.mkdir()
        for name in RUNTIME:
            shutil.copyfile(ROOT / name, self.app / name)
        self.hashes = {name:hashlib.sha256((self.app/name).read_bytes()).hexdigest() for name in RUNTIME}
        self.source = self.root / "fictional-Ω.xml"
        self.source.write_bytes(fixture())
        self.output = self.root / "fresh-reports"

    def cli(self, *args, status=0):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        env.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable,"-I","-S","-B","-c",BOOTSTRAP,str(self.app),*map(str,args)],
                                cwd=self.root,env=env,capture_output=True,text=True,encoding="utf-8",timeout=20)
        self.assertEqual(result.returncode,status,"Copied-runtime XML CLI status differs")
        for value in (result.stdout,result.stderr):
            self.assertNotIn("PRIVATE-CANARY",value)
            self.assertNotIn(str(self.root),value)
        self.assertEqual({name:hashlib.sha256((self.app/name).read_bytes()).hexdigest() for name in RUNTIME},self.hashes)
        self.assertEqual({p.name for p in self.app.iterdir()},set(RUNTIME))
        return result

    def convert(self,status=0):
        return self.cli(self.source,"--out-dir",self.output,status=status)

    def test_copied_runtime_exports_reopen_and_preserve_input(self):
        before = self.source.read_bytes()
        result = self.convert()
        self.assertEqual(result.stderr,"")
        self.assertEqual(json.loads(result.stdout),dict(status="ok",modules=1,measurements=1,overlay_rows=1,files_written=4))
        self.assertEqual(self.source.read_bytes(),before)
        self.assertEqual({p.name for p in self.output.iterdir()},
                         {"modules_summary.json","measurements_summary.json","overlay_line_line_summary.json","overlay_line_line_summary.csv"})
        overlay = json.loads((self.output/"overlay_line_line_summary.json").read_bytes())[0]
        self.assertEqual((overlay["delta_mid_x_um"],overlay["delta_mid_y_um"]),(.5,1))
        for path in self.output.glob("*.json"):
            json.loads(path.read_bytes())

    def test_existing_directory_and_file_are_preserved(self):
        self.output.mkdir()
        marker = self.output/"fictional-kept.txt"
        marker.write_bytes(b"Fictional existing data")
        self.assertEqual(json.loads(self.convert(status=2).stderr)["code"],"OUTPUT_EXISTS")
        self.assertEqual(marker.read_bytes(),b"Fictional existing data")
        other = self.root/"existing-file"
        other.write_bytes(b"Fictional existing file")
        self.cli(self.source,"--out-dir",other,status=2)
        self.assertEqual(other.read_bytes(),b"Fictional existing file")

    def test_declarations_refused_in_utf8_and_utf16_before_output(self):
        for text in ('<!DOCTYPE Recipe [<!ENTITY x "PRIVATE-CANARY">]><Recipe>&x;</Recipe>',
                     '<?fictional PRIVATE-CANARY?><Recipe/>'):
            for encoding in ("utf-8","utf-16"):
                self.source.write_bytes(text.encode(encoding))
                self.assertEqual(json.loads(self.convert(status=2).stderr)["code"],"XML_DECLARATION_FORBIDDEN")
                self.assertFalse(self.output.exists())

    def test_csv_formula_shielding_preserves_json_text(self):
        self.source.write_bytes(fixture("=PRIVATE-CANARY"))
        self.convert()
        rows = list(csv.DictReader(io.StringIO((self.output/"overlay_line_line_summary.csv").read_text(encoding="utf-8"))))
        self.assertEqual(rows[0]["id"],"'=PRIVATE-CANARY")
        self.assertEqual(json.loads((self.output/"overlay_line_line_summary.json").read_bytes())[0]["id"],"=PRIVATE-CANARY")

    def test_help_and_invalid_arguments_need_no_input_or_output(self):
        result = self.cli("--help")
        self.assertIn("usage: xml_recipe_inspector.py",result.stdout)
        self.assertEqual(result.stderr,"")
        self.assertEqual(json.loads(self.cli("--unknown","PRIVATE-CANARY",status=2).stderr)["code"],"ARGUMENTS_INVALID")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
