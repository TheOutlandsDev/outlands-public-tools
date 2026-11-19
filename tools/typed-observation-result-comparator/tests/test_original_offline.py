"""Ported offline row-validation and comparison cases with fictional values."""

from datetime import date, datetime, timezone
import json
import unittest

import typed_observation_compare as helper


def row():
    return (
        "Fictional sensor",
        "Synthetic reading",
        '001,quoted"\nvalue',
        datetime(2042, 9, 24, 1, 2, 3, 456789),
        datetime(2042, 9, 24, 1, 0, 0, 123456),
    )


class TestObservationComparisonTests(unittest.TestCase):
    def test_typed_rows_preserve_nulls_text_and_both_microsecond_values(self):
        original = row()
        nullable = (None, "", None, None, None)
        self.assertEqual(helper.validate_rows([original, nullable]), [original, nullable])
        self.assertEqual(original[3].microsecond, 456789)
        self.assertEqual(original[4].microsecond, 123456)
        self.assertTrue(original[2].startswith("001"))

    def test_typed_rows_reject_wrong_types_aware_timestamps_and_cap(self):
        for index, value in ((0, 1), (2, 1.5), (3, "2042-09-24"), (4, date(2042, 9, 24)),
                             (3, datetime(2042, 9, 24, tzinfo=timezone.utc)), (4, datetime(2042, 9, 24, tzinfo=timezone.utc))):
            changed = list(row())
            changed[index] = value
            with self.assertRaises(helper.ValidationError):
                helper.validate_rows([changed])
        with self.assertRaises(helper.ValidationError):
            helper.validate_rows([row()] * (helper.MAX_ROWS + 1))
        with self.assertRaises(helper.ValidationError):
            helper.validate_rows([row()[:-1]])

    def test_comparison_uses_all_five_fields_and_retains_duplicates(self):
        original = row()
        different = list(original)
        different[0] = "Alternate fictional sensor"
        rows = [original, tuple(different), original]
        result = helper.compare_rows(rows, list(reversed(rows)))
        self.assertTrue(result["all_values_match"])
        self.assertEqual(result["columns_compared"], 5)
        self.assertEqual(result["matched_rows"], 3)
        self.assertEqual(helper.compare_rows(rows, rows[:-1])["expected_only_rows"], 1)
        for index in range(5):
            changed = list(original)
            changed[index] = datetime(2042, 9, 24, 1, 2, 3, 456788) if index in (3, 4) else "ROW-SENTINEL"
            result = helper.compare_rows([original], [changed])
            self.assertFalse(result["all_values_match"])
            self.assertNotIn("ROW-SENTINEL", json.dumps(result))

    def test_comparison_distinguishes_null_empty_and_leading_zeros(self):
        left = list(row())
        right = left.copy()
        left[2], right[2] = None, ""
        self.assertFalse(helper.compare_rows([left], [right])["all_values_match"])
        left[2], right[2] = "001", "1"
        self.assertFalse(helper.compare_rows([left], [right])["all_values_match"])
        self.assertTrue(helper.compare_rows([], [])["all_values_match"])
