"""Check explicit bounds and refusal of ambiguous saved timestamps."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import observation_window as helper


SCRIPT = Path(__file__).resolve().parents[1] / "observation_window.py"


class ObservationWindowTests(unittest.TestCase):
    def test_bounds_reject_equal_reversed_and_aware_ranges(self):
        start = datetime(2044, 2, 29, 10)
        end = datetime(2044, 2, 29, 18)
        invalid = (
            (start, start),
            (end, start),
            (start.replace(tzinfo=timezone.utc), end),
            (start, end.replace(tzinfo=timezone.utc)),
        )
        for lower, upper in invalid:
            with self.subTest(lower=lower, upper=upper):
                with self.assertRaises(helper.ValidationError) as caught:
                    helper.validate_rows([], start=lower, end=upper)
                self.assertEqual(caught.exception.category, "bounds")

    def test_partial_input_bounds_still_select_whole_day(self):
        rows = [(datetime(2044, 2, 29, 12),)]
        result = helper.select_case(
            rows, start=datetime(2044, 2, 29, 10), end=datetime(2044, 2, 29, 18),
        )
        self.assertEqual(result, ("2044-02-29T00:00:00", "2044-03-01T00:00:00"))

    def test_last_representable_day_refuses_overflow(self):
        rows = [(datetime(9999, 12, 31, 12),)]
        with self.assertRaises(helper.ValidationError) as caught:
            helper.select_case(
                rows, start=datetime(9999, 12, 31),
                end=datetime(9999, 12, 31, 23, 59, 59, 999000),
            )
        self.assertEqual(caught.exception.category, "window_overflow")

    def test_cli_refuses_ambiguous_iso_and_withholds_private_values(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fictional-private-label.json"
            command = [
                sys.executable, "-I", "-B", str(SCRIPT), "--input", str(fixture),
                "--start", "2044-02-29T00:00:00", "--end", "2044-03-01T00:00:00",
            ]
            fixture.write_text(json.dumps([["2044-02-29T12:00:00.1"]]), encoding="utf-8")
            accepted = subprocess.run(command, capture_output=True, timeout=15, check=False)
            self.assertEqual(accepted.returncode, 0)
            self.assertEqual(accepted.stderr, b"")
            self.assertEqual(json.loads(accepted.stdout)["count"], 1)

            invalid = (
                "2044-02-29 12:00:00",
                "2044-02-29T12:00:00.1234",
                "2044-02-29T12:00:00+00:00",
                "2044-02-29T12:00:00Z",
                "20440229T120000",
                "fictional-private-value",
            )
            for timestamp in invalid:
                with self.subTest(timestamp=timestamp):
                    fixture.write_text(json.dumps([[timestamp]]), encoding="utf-8")
                    before = fixture.read_bytes()
                    result = subprocess.run(command, capture_output=True, timeout=15, check=False)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, b"")
                    self.assertTrue(result.stderr.strip())
                    self.assertNotIn(timestamp.encode("ascii"), result.stderr)
                    self.assertNotIn(fixture.name.encode("ascii"), result.stderr)
                    self.assertNotIn(b"Traceback", result.stderr)
                    self.assertEqual(fixture.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
