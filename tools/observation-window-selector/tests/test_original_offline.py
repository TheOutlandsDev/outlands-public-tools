"""Retained observation discovery cases with fictional dates and explicit bounds."""

from datetime import date, datetime, timedelta, timezone
import unittest

import observation_window as helper


START = datetime.fromisoformat("2042-08-26T00:00:00")
END = datetime.fromisoformat("2042-09-25T00:00:00")
BOUNDS = {"start": START, "end": END}


class TestObservationDiscoveryTests(unittest.TestCase):
    def test_rows_preserve_descending_millisecond_timestamps_and_duplicates(self):
        newest = datetime(2042, 9, 20, 12, 30, 40, 997000)
        rows = [(newest,), (newest,), (datetime(2042, 8, 26),)]
        self.assertEqual(helper.validate_rows(rows, **BOUNDS), rows)
        self.assertEqual(helper.validate_rows([], **BOUNDS), [])
        self.assertEqual(len(helper.validate_rows([(newest,)] * 100, **BOUNDS)), 100)

    def test_rows_reject_bad_shapes_null_types_aware_or_excess_precision(self):
        cases = (None, "2042-09-20", [(None,)], [(date(2042, 9, 20),)],
                 [("2042-09-20T00:00:00",)], [(123,)],
                 [(datetime(2042, 9, 20, tzinfo=timezone.utc),)],
                 [(datetime(2042, 9, 20, microsecond=123456),)],
                 [(datetime(2042, 9, 20), None)], [()],
                 [(datetime(2042, 9, 20),)] * 101)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(helper.ValidationError) as caught:
                helper.validate_rows(rows, **BOUNDS)
            self.assertEqual(caught.exception.category, "result_shape")

    def test_rows_enforce_start_inclusive_end_exclusive_and_descending(self):
        lower, upper = START, END
        self.assertEqual(helper.validate_rows([(lower,)], **BOUNDS), [(lower,)])
        self.assertEqual(
            helper.validate_rows([(upper - timedelta(milliseconds=3),)], **BOUNDS)[0][0],
            upper - timedelta(milliseconds=3),
        )
        for rows in ([(upper,)], [(lower - timedelta(milliseconds=3),)],
                     [(datetime(2042, 9, 20),), (datetime(2042, 9, 21),)]):
            with self.assertRaises(helper.ValidationError):
                helper.validate_rows(rows, **BOUNDS)

    def test_select_case_uses_latest_returned_day_with_whole_second_midnights(self):
        rows = [(datetime(2042, 9, 19, 23, 59, 59, 997000),), (datetime(2042, 9, 17),)]
        self.assertEqual(
            helper.select_case(rows, **BOUNDS),
            ("2042-09-19T00:00:00", "2042-09-20T00:00:00"),
        )
        self.assertEqual(
            helper.select_case([(datetime(2042, 9, 24, 1),)], **BOUNDS),
            ("2042-09-24T00:00:00", "2042-09-25T00:00:00"),
        )
        self.assertEqual(
            helper.select_case([(datetime(2042, 8, 26),)], **BOUNDS),
            ("2042-08-26T00:00:00", "2042-08-27T00:00:00"),
        )

    def test_select_case_returns_none_for_empty_and_revalidates_input(self):
        self.assertIsNone(helper.select_case([], **BOUNDS))
        with self.assertRaises(helper.ValidationError):
            helper.select_case([(datetime(2042, 9, 25),)], **BOUNDS)
        with self.assertRaises(helper.ValidationError):
            helper.select_case([(datetime(2042, 9, 20),), (datetime(2042, 9, 21),)], **BOUNDS)


if __name__ == "__main__":
    unittest.main()
