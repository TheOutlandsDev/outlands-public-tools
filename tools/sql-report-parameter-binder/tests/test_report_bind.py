"""Offline checks for the fictional report parameter binder."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from queries.report_detail.bind import (
    _product_placeholders,
    build_detail_query,
)


class RefurbBindTests(unittest.TestCase):
    def test_returns_original_query_shape_and_positional_parameters(self) -> None:
        start = date(2026, 9, 24)
        end = datetime(2026, 9, 25, 16, 30)
        products = ["DEMO-61", "DEMO-11"]

        sql, params = build_detail_query(
            start_date=start,
            end_date=end,
            selected_products=products,
            product_options={"DEMO-11", "DEMO-61"},
        )

        self.assertEqual(params, (start, end, *products))
        self.assertIn("DECLARE @StartDate datetime = ?;", sql)
        self.assertIn("DECLARE @EndDate datetime = ?;", sql)
        self.assertIn("PR.Name IN (?, ?)", sql)
        self.assertIn("obs.ObservationId BETWEEN @FirstObservationId AND @LastObservationId", sql)
        self.assertIn("obs.Label NOT LIKE '%Comment%'", sql)
        self.assertNotIn("/*PRODUCT_PARAMETERS*/", sql)
        self.assertNotIn(products[0], sql)
        self.assertNotIn(products[1], sql)

    def test_same_calendar_day_is_valid(self) -> None:
        sql, params = build_detail_query(
            start_date=datetime(2026, 9, 24, 20),
            end_date=datetime(2026, 9, 24, 8),
            selected_products=["A"],
            product_options={"A"},
        )
        self.assertIn("PR.Name IN (?)", sql)
        self.assertEqual(len(params), 3)

    def test_rejects_reversed_dates_and_non_date_input(self) -> None:
        args = dict(selected_products=["A"], product_options={"A"})
        with self.assertRaisesRegex(ValueError, "end_date"):
            build_detail_query(start_date=date(2026, 9, 25), end_date=date(2026, 9, 24), **args)
        with self.assertRaisesRegex(TypeError, "start_date"):
            build_detail_query(start_date="2026-09-24", end_date=date(2026, 9, 25), **args)

    def test_rejects_empty_duplicate_or_unknown_selection(self) -> None:
        dates = dict(start_date=date(2026, 9, 24), end_date=date(2026, 9, 25))
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_detail_query(selected_products=[], product_options={"A"}, **dates)
        with self.assertRaisesRegex(ValueError, "unique"):
            build_detail_query(selected_products=["A", "A"], product_options={"A"}, **dates)
        with self.assertRaisesRegex(ValueError, "absent"):
            build_detail_query(selected_products=["B"], product_options={"A"}, **dates)

    def test_rejects_strings_as_product_collections(self) -> None:
        dates = dict(start_date=date(2026, 9, 24), end_date=date(2026, 9, 25))
        with self.assertRaisesRegex(TypeError, "selected_products"):
            build_detail_query(selected_products="A", product_options={"A"}, **dates)
        with self.assertRaisesRegex(TypeError, "product_options"):
            build_detail_query(selected_products=["A"], product_options="A", **dates)

    def test_enforces_sql_server_parameter_ceiling(self) -> None:
        products = [f"P{i}" for i in range(2_099)]
        with self.assertRaisesRegex(ValueError, "2098"):
            build_detail_query(
                start_date=date(2026, 9, 24),
                end_date=date(2026, 9, 25),
                selected_products=products,
                product_options=set(products),
            )

    def test_requires_exactly_one_product_marker(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly once"):
            _product_placeholders("SELECT 1", 1)
        with self.assertRaisesRegex(ValueError, "exactly once"):
            _product_placeholders("/*PRODUCT_PARAMETERS*/ /*PRODUCT_PARAMETERS*/", 1)


if __name__ == "__main__":
    unittest.main()
