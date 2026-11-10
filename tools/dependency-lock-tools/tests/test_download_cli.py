"""Five portable fresh-process checks using four copied runtime files only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ("lock_common.py", "lock_windows.py", "report_to_lock.py", "verify_locks.py")
BOOTSTRAP = """import os,runpy,socket,subprocess,sys
from pathlib import Path
def deny(*args,**kwargs): raise AssertionError('NO_EXTERNAL_ACTION')
socket.socket=socket.create_connection=subprocess.Popen=os.system=deny
for action in (socket.socket,socket.create_connection,subprocess.Popen,os.system):
    try: action()
    except AssertionError: pass
    else: raise AssertionError('DENIAL_GUARD_FAILED')
folder=Path(sys.argv[1]); script=folder/sys.argv[2]
sys.path.insert(0,str(folder));sys.argv=[str(script)]+sys.argv[3:]
runpy.run_path(str(script),run_name='__main__')
"""


class DownloadCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="lock-fictional-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.app = self.root / "runtime"
        self.app.mkdir()
        for name in RUNTIME:
            shutil.copyfile(ROOT / name, self.app / name)
        self.runtime_hashes = {name: hashlib.sha256((self.app/name).read_bytes()).hexdigest() for name in RUNTIME}
        self.report = self.root / "fictional-Ω-report.json"
        self.output = self.root / "fictional.lock"
        record = {"metadata":{"name":"Demo_Package","version":"1.2.3","summary":"PRIVATE-CANARY"},
                  "download_info":{"url":"PRIVATE-CANARY","archive_info":{"hashes":{"sha256":"a"*64}}}}
        self.payload = {"version":"1","install":[record]}
        self.report.write_text(json.dumps(self.payload), encoding="utf-8")

    def cli(self, script, *args, status=0):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
        env.pop("PYTHONPATH", None)
        result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", BOOTSTRAP, str(self.app), script, *map(str,args)],
                                cwd=self.root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, status, "Copied-runtime CLI status differs")
        self.assertEqual(result.stderr, "")
        self.assertNotIn("PRIVATE-CANARY", result.stdout)
        self.assertNotIn(str(self.root), result.stdout)
        self.assertEqual({name:hashlib.sha256((self.app/name).read_bytes()).hexdigest() for name in RUNTIME}, self.runtime_hashes)
        self.assertEqual({p.name for p in self.app.iterdir()}, set(RUNTIME))
        return result

    def convert(self, status=0):
        return self.cli("report_to_lock.py", "--report", self.report, "--output", self.output, status=status)

    def test_copied_runtime_roundtrip_is_offline_and_preserves_report(self):
        original = self.report.read_bytes()
        self.assertEqual(json.loads(self.convert().stdout), {"result":"LOCK_WRITTEN","packages":1})
        self.assertEqual(json.loads(self.cli("verify_locks.py",self.output).stdout), {"result":"PASS","locks":1,"package_records":1})
        self.assertEqual(self.report.read_bytes(), original)
        self.assertNotIn(b"PRIVATE-CANARY", self.output.read_bytes())
        self.assertIn(b"demo-package==1.2.3", self.output.read_bytes())

    def test_existing_output_and_report_are_not_overwritten(self):
        self.output.write_bytes(b"Fictional existing output")
        self.convert(status=2)
        self.assertEqual(self.output.read_bytes(), b"Fictional existing output")
        before = self.report.read_bytes()
        self.cli("report_to_lock.py","--report",self.report,"--output",self.report,status=2)
        self.assertEqual(self.report.read_bytes(), before)

    def test_invalid_report_creates_no_lock_and_omits_private_values(self):
        self.payload["install"][0]["metadata"]["version"] = "PRIVATE-CANARY"
        self.report.write_text(json.dumps(self.payload),encoding="utf-8")
        self.assertEqual(json.loads(self.convert(status=2).stdout)["code"], "VERSION_UNSUPPORTED")
        self.assertFalse(self.output.exists())

    def test_requirement_directive_is_rejected_without_external_actions(self):
        self.output.write_bytes(b"--index-url PRIVATE-CANARY\n")
        self.assertEqual(json.loads(self.cli("verify_locks.py",self.output,status=2).stdout)["code"], "LOCK_LINE_INVALID")
        self.assertEqual(self.output.read_bytes(), b"--index-url PRIVATE-CANARY\n")

    def test_help_and_argument_rejection_need_no_report_or_output(self):
        for script in ("report_to_lock.py","verify_locks.py"):
            self.assertIn("usage:", self.cli(script,"--help").stdout)
            self.assertEqual(json.loads(self.cli(script,"--unknown","PRIVATE-CANARY",status=2).stdout)["code"], "ARGUMENTS_INVALID")
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
