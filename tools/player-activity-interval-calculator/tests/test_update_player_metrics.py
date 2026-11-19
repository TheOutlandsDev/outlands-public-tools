"""Direct interval assertions from the original PlayerPortal tests."""

import unittest

from player_activity_intervals.calculator import calculate_intervals


class OriginalPlayerIntervalTests(unittest.TestCase):
    def test_eight_online_players_credit_eight_player_hours_per_hour(self) -> None:
        point = {
            "server_id": "fictional-arena",
            "state": "online",
            "population": 8,
            "metric_kind": "players",
            "start": "2040-01-02T00:00:00Z",
            "end": "2040-01-02T01:00:00Z",
        }

        result = calculate_intervals([point], display_offset="Z")["totals"]

        self.assertEqual(result["observed_seconds"], 3600.0)
        self.assertEqual(result["online_seconds"], 3600.0)
        self.assertEqual(result["player_hours"], 8.0)

    def test_offline_population_never_accrues_player_hours(self) -> None:
        point = {
            "server_id": "fictional-arena",
            "state": "offline",
            "population": 8,
            "metric_kind": "players",
            "start": "2040-01-02T00:00:00Z",
            "end": "2040-01-02T01:00:00Z",
        }

        result = calculate_intervals([point], display_offset="Z")["totals"]

        self.assertEqual(result["observed_seconds"], 3600.0)
        self.assertEqual(result["online_seconds"], 0.0)
        self.assertEqual(result["player_hours"], 0.0)
