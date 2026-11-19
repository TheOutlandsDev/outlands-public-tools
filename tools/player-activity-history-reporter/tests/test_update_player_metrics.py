"""Report-level cases retained from the original player metrics tests."""

import unittest

from player_activity_history import build_report


REPORT_DATE = "2040-07-28"


class OriginalHistoryTests(unittest.TestCase):
    def test_two_layer_baseline_and_archived_totals_balance(self):
        report = build_report(
            {
                "active": [
                    {
                        "server_id": "fictional-arena",
                        "metric_kind": "players",
                        "baseline_hours": 10,
                        "daily": [{"date": REPORT_DATE, "activity_seconds": 120}],
                    },
                    {
                        "server_id": "fictional-relay",
                        "metric_kind": "connections",
                        "baseline_hours": 20,
                        "daily": [{"date": REPORT_DATE, "activity_seconds": 180}],
                    },
                ],
                "archived": [
                    {
                        "server_id": "fictional-garden",
                        "metric_kind": "players",
                        "baseline_hours": 4,
                        "observed_activity_seconds": 3600,
                    }
                ],
            },
            REPORT_DATE,
        )
        players = report["totals"]["players"]
        connections = report["totals"]["connections"]
        self.assertEqual(players["baseline_hours"], 14.0)
        self.assertEqual(connections["baseline_hours"], 20.0)
        self.assertEqual(players["archived_lifetime_hours"], 5.0)
        self.assertEqual(connections["archived_lifetime_hours"], 0.0)
        for totals, lifetime in [(players, 15.03), (connections, 20.05)]:
            self.assertAlmostEqual(
                totals["baseline_hours"] + totals["observed_lifetime_hours"],
                totals["lifetime_hours"],
                delta=0.02,
            )
            self.assertAlmostEqual(
                totals["active_lifetime_hours"] + totals["archived_lifetime_hours"],
                totals["lifetime_hours"],
                delta=0.02,
            )
            self.assertEqual(totals["lifetime_hours"], lifetime)

        servers = {server["server_id"]: server for server in report["servers"]}
        arena = servers["fictional-arena"]
        relay = servers["fictional-relay"]
        arena_totals = arena["totals"]
        self.assertEqual(arena_totals["baseline_hours"], 10.0)
        self.assertEqual(arena_totals["observed_lifetime_hours"], 0.03)
        self.assertEqual(arena_totals["lifetime_hours"], 10.03)
        self.assertEqual(len(arena["daily_30d"]), 30)
        self.assertEqual(arena["daily_30d"][-1]["cumulative_hours"], 10.03)
        self.assertTrue(
            all(row["cumulative_hours"] >= arena_totals["baseline_hours"] for row in arena["daily_30d"])
        )
        self.assertEqual(arena["weekly_lifetime"][-1]["cumulative_hours"], 10.03)
        self.assertEqual(relay["weekly_lifetime"][-1]["cumulative_hours"], 20.05)
        self.assertEqual(arena_totals["seeded_7d_hours"], 10.03)
        self.assertEqual(arena_totals["seeded_30d_hours"], 10.03)
        self.assertAlmostEqual(
            arena_totals["baseline_hours"] + sum(row["activity_hours"] for row in arena["daily_30d"][-7:]),
            arena_totals["seeded_7d_hours"],
            delta=0.02,
        )
        archive = report["archived"][0]
        self.assertEqual(
            (archive["baseline_hours"], archive["observed_lifetime_hours"], archive["lifetime_hours"]),
            (4.0, 1.0, 5.0),
        )
        self.assertAlmostEqual(
            arena_totals["seeded_7d_hours"] + archive["baseline_hours"],
            players["seeded_7d_hours"],
            delta=0.02,
        )
        self.assertEqual(connections["seeded_7d_hours"], relay["totals"]["seeded_7d_hours"])

    def test_availability_only_history_never_becomes_human_playtime(self):
        report = build_report(
            {
                "active": [
                    {
                        "server_id": "fictional-beacon",
                        "metric_kind": "availability_only",
                        "baseline_hours": 90,
                        "daily": [{"date": REPORT_DATE, "activity_seconds": 900}],
                        "states": [
                            {"observed_at": f"{REPORT_DATE}T10:00:00Z", "state": "online"},
                            {"observed_at": f"{REPORT_DATE}T10:01:00Z", "state": "offline"},
                        ],
                    },
                    {
                        "server_id": "fictional-arena",
                        "metric_kind": "players",
                        "baseline_hours": 0,
                        "daily": [{"date": REPORT_DATE, "activity_seconds": 120}],
                        "states": [
                            {"observed_at": f"{REPORT_DATE}T10:00:00Z", "state": "online"},
                            {"observed_at": f"{REPORT_DATE}T10:01:00Z", "state": "online"},
                        ],
                    },
                ],
                "archived": [],
            },
            REPORT_DATE,
        )
        servers = {server["server_id"]: server for server in report["servers"]}
        beacon = servers["fictional-beacon"]
        self.assertFalse(beacon["activity_tracked"])
        self.assertEqual(beacon["totals"]["lifetime_hours"], 0.0)
        self.assertEqual(beacon["totals"]["baseline_hours"], 0.0)
        self.assertEqual(beacon["daily_30d"][-1]["activity_hours"], 0.0)
        self.assertEqual(report["totals"]["players"]["lifetime_hours"], 0.03)
        self.assertEqual(
            report["events"],
            [
                {
                    "server_id": "fictional-beacon",
                    "observed_at": f"{REPORT_DATE}T10:01:00+00:00",
                    "from_state": "online",
                    "to_state": "offline",
                }
            ],
        )
