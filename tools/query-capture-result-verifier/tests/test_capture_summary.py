from __future__ import annotations

import json
import unittest

from query_capture_result_verifier import CaptureContract, summary


CONTRACT = CaptureContract("Example inventory report", "2020-04-01T00:00:00", "2020-04-02T00:00:00", 9, False)


class CaptureSummaryTests(unittest.TestCase):
    def test_summary_requires_full_nonempty_match_without_order_check(self):
        manifest = {"status": "compared_not_validated", "parameters": {"StartDate": CONTRACT.start, "EndDate": CONTRACT.end},
                    "elapsed_seconds": 0.25,
                    "comparison": {"status": "match", "columns_compared": 9, "expected_rows": 2, "actual_rows": 2,
                                   "matched_rows": 2, "expected_only_rows": 0, "actual_only_rows": 0,
                                   "all_values_match": True, "ordered_group_keys_match": None,
                                   "order_check_applicable": False, "sql_metadata_match": True}}
        self.assertEqual(summary(CONTRACT, manifest)["status"], "matched")
        empty = json.loads(json.dumps(manifest))
        empty["comparison"].update(expected_rows=0, actual_rows=0, matched_rows=0)
        self.assertEqual(summary(CONTRACT, empty)["status"], "empty_not_validated")
        wrong_order = json.loads(json.dumps(manifest))
        wrong_order["comparison"]["ordered_group_keys_match"] = True
        self.assertEqual(summary(CONTRACT, wrong_order)["status"], "mismatch")
        failed = summary(CONTRACT, {"status": "failed", "error": {
            "category": "authentication", "sqlstate": "28000", "raw": "EMAIL-SENTINEL"}})
        self.assertEqual(failed["status"], "failed")
        self.assertNotIn("EMAIL-SENTINEL", json.dumps(failed))

    def test_summary_does_not_accept_inconsistent_comparison_status(self):
        for count in (0, 2):
            manifest = {
                "status": "compared_not_validated",
                "parameters": {"StartDate": CONTRACT.start, "EndDate": CONTRACT.end},
                "comparison": {
                    "status": "match", "columns_compared": 9,
                    "expected_rows": count, "actual_rows": count, "matched_rows": count,
                    "expected_only_rows": 0, "actual_only_rows": 0,
                    "all_values_match": True, "ordered_group_keys_match": None,
                    "order_check_applicable": False, "sql_metadata_match": True,
                },
            }
            expected = "empty_not_validated" if count == 0 else "matched"
            self.assertEqual(summary(CONTRACT, manifest)["status"], expected)
            for reported_status in ("mismatch", "unexpected", None):
                altered = json.loads(json.dumps(manifest))
                if reported_status is None:
                    del altered["comparison"]["status"]
                else:
                    altered["comparison"]["status"] = reported_status
                with self.subTest(count=count, reported_status=reported_status):
                    self.assertNotIn(
                        summary(CONTRACT, altered)["status"],
                        ("matched", "empty_not_validated"),
                    )
