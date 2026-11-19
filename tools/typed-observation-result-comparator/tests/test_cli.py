"""Focused subprocess checks for the standalone saved-result comparator."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


CLI = Path(__file__).resolve().parents[1] / "typed_observation_compare.py"
SENTINEL = "FICTIONAL-PRIVATE-MARKER"
ROW = (
    SENTINEL,
    'Comma, quote" and newline\n',
    "001",
    "2042-09-24T01:02:03.456789",
    "2042-09-24T01:00:00.123456",
)
REPORT_FIELDS = {
    "status",
    "all_values_match",
    "columns_compared",
    "expected_rows",
    "actual_rows",
    "matched_rows",
    "expected_only_rows",
    "actual_only_rows",
    "expected_only_distinct_rows",
    "actual_only_distinct_rows",
    "comparison_basis",
}


def payload(rows):
    return json.dumps(rows).encode("utf-8")


class TypedComparisonCLITests(unittest.TestCase):
    def run_comparison(self, expected, actual):
        filenames = (f"expected {SENTINEL}.json", f"actual {SENTINEL}.json")
        inputs = dict(zip(filenames, (expected, actual), strict=True))
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, contents in inputs.items():
                (folder / name).write_bytes(contents)
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(CLI),
                 "--expected", filenames[0], "--actual", filenames[1]],
                cwd=folder, capture_output=True, encoding="utf-8", timeout=15,
            )
            self.assertEqual(set(inputs), {path.name for path in folder.iterdir()})
            self.assertEqual(inputs, {name: (folder / name).read_bytes() for name in inputs})
        self.assertNotIn(SENTINEL, result.stdout + result.stderr)
        return result

    def test_matches_reordered_rows_and_preserves_files(self):
        rows = (ROW, (None, "", None, None, None), ROW)
        result = self.run_comparison(payload(rows), payload((rows[1], ROW, ROW)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(set(report), REPORT_FIELDS)
        self.assertEqual(report["status"], "match")
        self.assertTrue(report["all_values_match"])
        self.assertEqual(report["matched_rows"], 3)
        self.assertEqual(report["expected_only_rows"], 0)
        self.assertEqual(report["actual_only_rows"], 0)

    def test_distinguishes_microsecond_changes_in_either_column(self):
        edits = (
            (3, "2042-09-24T01:02:03.456788"),
            (4, "2042-09-24T01:00:00.123455"),
        )
        for index, value in edits:
            with self.subTest(column=index):
                changed = list(ROW)
                changed[index] = value
                result = self.run_comparison(payload([ROW]), payload([changed]))
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stderr, "")
                report = json.loads(result.stdout)
                self.assertEqual(set(report), REPORT_FIELDS)
                self.assertEqual(report["status"], "mismatch")
                self.assertFalse(report["all_values_match"])
                self.assertEqual(report["matched_rows"], 0)
                self.assertEqual(report["expected_only_rows"], 1)
                self.assertEqual(report["actual_only_rows"], 1)

    def test_rejects_malformed_or_imprecise_input_without_disclosing_it(self):
        imprecise = list(ROW)
        imprecise[4] = "2042-09-24T01:00:00.1234567"
        for bad in (payload([ROW])[:-1], payload([imprecise])):
            with self.subTest(input_size=len(bad)):
                result = self.run_comparison(payload([ROW]), bad)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr.strip())
                self.assertNotIn("Traceback", result.stderr)
                self.assertNotIn(imprecise[4], result.stderr)
