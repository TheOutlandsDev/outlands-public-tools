"""Qualification guards exercised with disposable test suites."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / "check_shared_python315.py"


class QualificationGuards(unittest.TestCase):
    def execute(self, source):
        with tempfile.TemporaryDirectory(prefix="shared-lane-guard-") as directory:
            root = Path(directory)
            runner = root / "integrations" / "windows-ai-readiness" / RUNNER.name
            runner.parent.mkdir(parents=True)
            runner.write_bytes(RUNNER.read_bytes())
            (root / "tests").mkdir()
            (root / "tests" / "test_assessment_records.py").write_text(source, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(runner), "--suite", "test_assessment_records.py"],
                capture_output=True, text=True, timeout=20,
            )
            return completed.returncode, json.loads(completed.stdout)

    def test_zero_discovered_tests_are_not_a_pass(self):
        code, result = self.execute("# Deliberately no tests.\n")
        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "NO_TESTS")
        self.assertEqual(result["tests_run"], 0)

    def test_an_entirely_skipped_suite_is_not_a_pass(self):
        code, result = self.execute(
            "import unittest\nclass Example(unittest.TestCase):\n"
            " @unittest.skip('fixture')\n def test_one(self): pass\n")
        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "ALL_SKIPPED")
        self.assertEqual(result["tests_run"], result["skipped"])

    def test_a_real_failure_is_not_a_pass(self):
        code, result = self.execute(
            "import unittest\nclass Example(unittest.TestCase):\n"
            " def test_one(self): self.fail('fixture')\n")
        self.assertNotEqual(code, 0)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failures"], 1)

    def test_a_success_requires_an_executed_test(self):
        code, result = self.execute(
            "import unittest\nclass Example(unittest.TestCase):\n"
            " def test_one(self): self.assertEqual(2 + 2, 4)\n")
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tests_run"], 1)


if __name__ == "__main__":
    unittest.main()
