"""Independent actual CLI checks using only authored PDFs and local scratch files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DownloadCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pdf-cli-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.demo = self.work / "authored demo"
        result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "examples/make_demo.py"),
                                 "--destination", str(self.demo)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0)

    def run_cli(self, name, expected, **options):
        output = self.work / (name + " report")
        args = [sys.executable, "-I", "-B", str(ROOT / "pdf_bounds.py"), "--pdf", str(self.demo / (name + ".pdf")),
                "--output", str(output)]
        for key, value in options.items(): args += ["--" + key, str(value)]
        result = subprocess.run(args, capture_output=True, timeout=40)
        self.assertEqual(result.returncode, expected, result.stdout)
        self.assertFalse(result.stderr)
        self.assertNotIn(str(self.work).encode(), result.stdout)
        return output, json.loads(result.stdout)

    def test_real_inside_outside_manifest_and_immutable_inputs(self):
        before = {p.name: p.read_bytes() for p in self.demo.iterdir()}
        for name, code, chars, findings in [("inside", 0, 16, 0), ("outside", 1, 4, 4)]:
            output, summary = self.run_cli(name, code)
            self.assertEqual((summary["characters_observed"], summary["outside_characters"]), (chars, findings))
            manifest = json.loads((output / "MANIFEST.json").read_text())
            self.assertEqual(set(p.name for p in output.iterdir()), {"MANIFEST.json", "report.json", "report.html"})
            for row in manifest["files"]:
                data = (output / row["path"]).read_bytes()
                self.assertEqual((len(data), hashlib.sha256(data).hexdigest()), (row["bytes"], row["sha256"]))
                for token in (b"Fictional inside", b"EDGE", str(self.work).encode()): self.assertNotIn(token, data)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.demo.iterdir()})

    def test_crop_rotation_origin_and_textless_review(self):
        output, summary = self.run_cli("crop", 1, box="crop", tolerance=0)
        self.assertGreater(summary["outside_characters"], 0)
        for name in ("rotated", "nonzero-origin"): self.run_cli(name, 0)
        output, summary = self.run_cli("empty", 1)
        self.assertEqual(summary["coverage_issues"], ["PAGES_WITH_NO_TEXT_OBSERVED"])

    def test_malformed_is_incomplete_with_no_report(self):
        (self.demo / "broken.pdf").write_bytes(b"%PDF-1.4\nnot an object tree\n%%EOF\n")
        output, summary = self.run_cli("broken", 2)
        self.assertEqual(summary["status"], "INCOMPLETE")
        self.assertFalse(output.exists())

    def test_existing_output_and_input_remain_unchanged(self):
        output = self.work / "inside report"
        output.mkdir(); (output / "keep").write_bytes(b"retained")
        before = (self.demo / "inside.pdf").read_bytes()
        _, summary = self.run_cli("inside", 2)
        self.assertEqual(summary["error"], "OUTPUT_EXISTS")
        self.assertEqual([p.name for p in output.iterdir()], ["keep"])
        self.assertEqual((output / "keep").read_bytes(), b"retained")
        self.assertEqual((self.demo / "inside.pdf").read_bytes(), before)

    def test_actual_audit_hook_refuses_socket_process_and_write(self):
        code = """import sys,socket,subprocess
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from pdf_bounds import _worker_guard
sys.addaudithook(_worker_guard)
actions = [lambda: socket.socket(), lambda: subprocess.run([sys.executable, '-c', 'pass']),
           lambda: Path(sys.argv[2]).write_bytes(b'not written')]
for action in actions:
    try: action()
    except PermissionError: pass
    else: raise SystemExit('AUDIT_REFUSAL_MISSING')
print('AUDIT_REFUSALS_PASS')
"""
        path = self.work / "refused write"
        result = subprocess.run([sys.executable, "-I", "-B", "-W", "error", "-c", code, str(ROOT), str(path)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), b"AUDIT_REFUSALS_PASS")
        self.assertFalse(result.stderr); self.assertFalse(path.exists())

if __name__ == "__main__": unittest.main()
