"""Offline tests for saved CSV result comparison."""

from __future__ import annotations

import csv
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from rdl_query_lab.compare_results import compare_csvs, main


class CompareResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.files: dict[str, bytes] = {}

        def open_fixture(
            path: Path,
            mode: str = "r",
            buffering: int = -1,
            encoding: str | None = None,
            errors: str | None = None,
            newline: str | None = None,
        ) -> io.TextIOWrapper:
            if mode != "r":
                raise AssertionError("Comparator attempted to write a file")
            return io.TextIOWrapper(
                io.BytesIO(self.files[str(path)]),
                encoding=encoding or "utf-8",
                errors=errors,
                newline=newline,
            )

        patcher = patch.object(Path, "open", open_fixture)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_csv(
        self, name: str, header: list[str], rows: list[list[str]], *, bom: bool = False
    ) -> Path:
        path = Path(name)
        handle = io.StringIO(newline="")
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
        data = handle.getvalue().encode("utf-8")
        self.files[str(path)] = (b"\xef\xbb\xbf" + data) if bom else data
        return path

    def write_mapping(self, mapping: dict[str, str]) -> Path:
        path = Path("mapping.json")
        self.files[str(path)] = json.dumps(mapping).encode("utf-8")
        return path

    def test_ignores_row_order_and_handles_bom_quoting_multiline_and_duplicates(self) -> None:
        row = ["material, one", 'first "quoted" line\nsecond line']
        left = self.write_csv("left.csv", ["Material", "Note"], [row, ["two", "é"], row])
        right = self.write_csv("right.csv", ["Material", "Note"], [["two", "é"], row, row], bom=True)

        report = compare_csvs(left, right)

        self.assertEqual(report["status"], "match")
        self.assertEqual((report["left_rows"], report["right_rows"], report["matched_rows"]), (3, 3, 3))
        self.assertEqual(report["left_only_examples"], [])

    def test_same_names_in_different_column_order_compare_by_name(self) -> None:
        left = self.write_csv("left.csv", ["Material", "Value"], [["M1", "V1"]])
        right = self.write_csv("right.csv", ["Value", "Material"], [["V1", "M1"]])
        self.assertEqual(compare_csvs(left, right)["status"], "match")

    def test_duplicate_difference_reports_counts_and_bounded_digests_only(self) -> None:
        left = self.write_csv("left.csv", ["Material"], [["SECRET_LEFT"], ["SECRET_LEFT"]])
        right = self.write_csv("right.csv", ["Material"], [["SECRET_LEFT"], ["SECRET_RIGHT"]])

        report = compare_csvs(left, right, max_examples=1)
        encoded = json.dumps(report)

        self.assertEqual(report["status"], "mismatch")
        self.assertEqual(report["matched_rows"], 1)
        self.assertEqual(report["left_only_rows"], 1)
        self.assertEqual(report["right_only_rows"], 1)
        self.assertEqual(len(report["left_only_examples"]), 1)
        self.assertEqual(report["left_only_examples"][0]["count"], 1)
        self.assertRegex(report["left_only_examples"][0]["sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn("SECRET_LEFT", encoded)
        self.assertNotIn("SECRET_RIGHT", encoded)

    def test_mapping_is_required_for_renames_and_must_cover_both_headers(self) -> None:
        left = self.write_csv("left.csv", ["Material", "Value"], [["M1", "V1"]])
        right = self.write_csv("right.csv", ["MaterialName", "Reading"], [["M1", "V1"]])
        with self.assertRaisesRegex(ValueError, "mapping"):
            compare_csvs(left, right)

        mapping = self.write_mapping({"Material": "MaterialName", "Value": "Reading"})
        self.assertEqual(compare_csvs(left, right, mapping_path=mapping)["status"], "match")

        self.write_mapping({"Material": "MaterialName"})
        with self.assertRaisesRegex(ValueError, "every column"):
            compare_csvs(left, right, mapping_path=mapping)
        self.write_mapping({"Material": "MaterialName", "Value": "MaterialName"})
        with self.assertRaisesRegex(ValueError, "every column"):
            compare_csvs(left, right, mapping_path=mapping)

    def test_rejects_duplicate_header_and_wrong_row_width(self) -> None:
        valid = self.write_csv("valid.csv", ["A", "B"], [["1", "2"]])
        duplicate_header = self.write_csv("duplicate.csv", ["A", "A"], [["1", "2"]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            compare_csvs(duplicate_header, valid)

        bad_width = self.write_csv("bad_width.csv", ["A", "B"], [["1"]])
        with self.assertRaisesRegex(ValueError, "different column count"):
            compare_csvs(bad_width, valid)

    def test_example_limit_and_cli_exit_status(self) -> None:
        left = self.write_csv("left.csv", ["A"], [["secret-a"], ["secret-b"], ["secret-c"]])
        right = self.write_csv("right.csv", ["A"], [])
        report = compare_csvs(left, right, max_examples=1)
        self.assertEqual(report["left_only_rows"], 3)
        self.assertEqual(len(report["left_only_examples"]), 1)

        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main([str(left), str(right), "--max-examples", "1"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue())["status"], "mismatch")
        self.assertNotIn("secret-a", stdout.getvalue())

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(left), str(left)]), 0)

    def test_rejects_excessive_example_limit(self) -> None:
        left = self.write_csv("left.csv", ["A"], [])
        with self.assertRaisesRegex(ValueError, "max_examples"):
            compare_csvs(left, left, max_examples=21)


if __name__ == "__main__":
    unittest.main()
