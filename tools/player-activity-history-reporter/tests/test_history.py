import copy
from datetime import date
import json
from pathlib import Path
import unittest

from player_activity_history import ReportError, build_report


REPORT_DATE = "2040-07-28"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "history.json"


def active(server_id="sample-lobby", *, kind="players", baseline=0, days=(), states=()):
    return {
        "server_id": server_id,
        "metric_kind": kind,
        "baseline_hours": baseline,
        "daily": [{"date": day, "activity_seconds": seconds} for day, seconds in days],
        "states": [{"observed_at": when, "state": state} for when, state in states],
    }


def archived(server_id="sample-garden"):
    return {
        "server_id": server_id,
        "metric_kind": "players",
        "baseline_hours": 2,
        "observed_activity_seconds": 3600,
    }


class HistoryReportTests(unittest.TestCase):
    def test_distinct_metric_units_and_no_mixed_total(self):
        document = json.loads(EXAMPLE.read_bytes())
        report = build_report(document, REPORT_DATE, "-04:00")
        self.assertEqual(set(report["totals"]), {"players", "connections"})
        self.assertEqual(
            report["totals"]["players"],
            {
                "baseline_hours": 14.0,
                "observed_7d_hours": 0.03,
                "observed_30d_hours": 0.03,
                "observed_lifetime_hours": 1.03,
                "active_lifetime_hours": 10.03,
                "archived_lifetime_hours": 5.0,
                "lifetime_hours": 15.03,
                "seeded_7d_hours": 14.03,
                "seeded_30d_hours": 14.03,
            },
        )
        self.assertEqual(
            report["totals"]["connections"],
            {
                "baseline_hours": 20.0,
                "observed_7d_hours": 0.05,
                "observed_30d_hours": 0.05,
                "observed_lifetime_hours": 0.05,
                "active_lifetime_hours": 20.05,
                "archived_lifetime_hours": 0.0,
                "lifetime_hours": 20.05,
                "seeded_7d_hours": 20.05,
                "seeded_30d_hours": 20.05,
            },
        )

    def test_report_windows_and_cumulative_across_missing_days(self):
        recent = active(
            baseline=1,
            days=(
                ("2040-07-28", 1800),
                ("2040-06-28", 14400),
                ("2040-07-22", 3600),
                ("2040-07-21", 7200),
                ("2040-06-29", 10800),
            ),
        )
        report = build_report({"active": [recent], "archived": []}, REPORT_DATE)
        server = report["servers"][0]
        totals = server["totals"]
        self.assertEqual(totals["observed_7d_hours"], 1.5)
        self.assertEqual(totals["observed_30d_hours"], 6.5)
        self.assertEqual(totals["observed_lifetime_hours"], 10.5)
        self.assertEqual(totals["seeded_7d_hours"], 2.5)
        self.assertEqual(totals["seeded_30d_hours"], 7.5)
        self.assertEqual(totals["lifetime_hours"], 11.5)
        rows = server["daily_30d"]
        self.assertEqual(len(rows), 30)
        self.assertEqual(rows[0], {"date": "2040-06-29", "activity_hours": 3.0, "cumulative_hours": 8.0})
        self.assertEqual(rows[1], {"date": "2040-06-30", "activity_hours": 0.0, "cumulative_hours": 8.0})
        self.assertEqual(rows[-1], {"date": REPORT_DATE, "activity_hours": 0.5, "cumulative_hours": 11.5})
        weeks = server["weekly_lifetime"]
        self.assertEqual(weeks[0], {"date": "2040-06-28", "activity_hours": 0.0, "cumulative_hours": 1.0})
        self.assertTrue(all(date.fromisoformat(row["date"]).weekday() == 6 for row in weeks[1:-1]))
        self.assertEqual(weeks[-1]["date"], REPORT_DATE)
        self.assertEqual(weeks[-1]["cumulative_hours"], 11.5)
        self.assertEqual(sum(row["activity_hours"] for row in weeks), 10.5)

    def test_duplicate_ids_across_and_within_active_and_archive_refused(self):
        cases = (
            {"active": [active(), active(kind="connections")], "archived": []},
            {"active": [], "archived": [archived(), archived()]},
            {"active": [active()], "archived": [archived("sample-lobby")]},
        )
        for number, document in enumerate(cases):
            with self.subTest(number=number), self.assertRaises(ReportError):
                build_report(document, REPORT_DATE)

    def test_duplicate_daily_rows_and_state_instants_refused(self):
        records = (
            active(days=((REPORT_DATE, 3600), (REPORT_DATE, 7200))),
            active(states=((f"{REPORT_DATE}T12:00:00Z", "online"), (f"{REPORT_DATE}T08:00:00-04:00", "offline"))),
        )
        for number, record in enumerate(records):
            with self.subTest(number=number), self.assertRaises(ReportError):
                build_report({"active": [record], "archived": []}, REPORT_DATE)

    def test_transitions_use_fixed_offset_and_leading_state(self):
        monitor = active(
            kind="availability_only",
            states=(
                ("2040-07-29T03:59:59Z", "degraded"),
                ("2040-06-29T05:00:00Z", "offline"),
                ("2040-06-29T03:59:59Z", "online"),
            ),
        )
        report = build_report({"active": [monitor], "archived": []}, REPORT_DATE, "-04:00")
        self.assertEqual(report["display_offset"], "-04:00")
        self.assertEqual(
            report["events"],
            [
                {
                    "server_id": "sample-lobby",
                    "observed_at": "2040-07-28T23:59:59-04:00",
                    "from_state": "offline",
                    "to_state": "degraded",
                },
                {
                    "server_id": "sample-lobby",
                    "observed_at": "2040-06-29T01:00:00-04:00",
                    "from_state": "online",
                    "to_state": "offline",
                },
            ],
        )

    def test_transitions_are_latest_first_and_capped(self):
        states = tuple(
            (f"{REPORT_DATE}T12:{minute:02d}:00Z", "offline" if minute % 2 else "online")
            for minute in range(46)
        )
        report = build_report(
            {"active": [active("z-sample", states=states), active("a-sample", states=states)], "archived": []},
            REPORT_DATE,
        )
        events = report["events"]
        self.assertEqual(len(events), 40)
        self.assertEqual(events[0]["server_id"], "a-sample")
        self.assertEqual(events[1]["server_id"], "z-sample")
        self.assertEqual(events[0]["observed_at"], f"{REPORT_DATE}T12:45:00+00:00")
        self.assertEqual(events[-1]["observed_at"], f"{REPORT_DATE}T12:26:00+00:00")
        self.assertEqual(
            [event["observed_at"] for event in events],
            sorted((event["observed_at"] for event in events), reverse=True),
        )

    def test_malformed_or_future_rows_refused(self):
        records = (
            active(kind="other"),
            active(baseline=True),
            active(baseline=-1),
            active(days=((REPORT_DATE, "3600"),)),
            active(days=(("2040-07-29", 60),)),
            active(states=(("2040-07-29T04:00:00Z", "online"),)),
            active(states=((f"{REPORT_DATE}T12:00:00", "online"),)),
            active(states=((f"{REPORT_DATE}T12:00:00Z", "other"),)),
        )
        for number, record in enumerate(records):
            with self.subTest(number=number), self.assertRaises(ReportError):
                build_report({"active": [record], "archived": []}, REPORT_DATE, "-04:00")
        for value in ("2040-7-28", "2040-02-30", "0001-01-29"):
            with self.subTest(as_of=value), self.assertRaises(ReportError):
                build_report({"active": [], "archived": []}, value)

    def test_report_is_repeatable_without_mutating_input(self):
        document = json.loads(EXAMPLE.read_bytes())
        before = copy.deepcopy(document)
        first = build_report(document, REPORT_DATE, "-04:00")
        second = build_report(document, REPORT_DATE, "-04:00")
        self.assertEqual(first, second)
        self.assertEqual(document, before)
