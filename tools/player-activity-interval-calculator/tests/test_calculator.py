"""Check fixed-offset buckets, units and bounded validation."""

import unittest

from player_activity_intervals.calculator import calculate_intervals


def _point(**changes):
    return {
        "server_id": "fictional-arena",
        "state": "online",
        "population": 2,
        "metric_kind": "players",
        "start": "2040-01-03T03:30:00Z",
        "end": "2040-01-03T04:30:00Z",
        **changes,
    }


class ActivityIntervalTests(unittest.TestCase):
    def test_splits_at_fixed_offset_midnight(self) -> None:
        rows = calculate_intervals([_point()], display_offset="-04:00")["daily"]
        self.assertEqual([row["day"] for row in rows], ["2040-01-02", "2040-01-03"])
        for row in rows:
            self.assertEqual(row, {
                "day": row["day"],
                "server_id": "fictional-arena",
                "observed_seconds": 1800,
                "online_seconds": 1800,
                "player_hours": 1.0,
                "connection_hours": 0.0,
            })

    def test_keeps_player_and_connection_hours_separate(self) -> None:
        second = _point(
            metric_kind="connections", population=8,
            start="2040-01-03T04:30:00Z", end="2040-01-03T05:00:00Z",
        )
        result = calculate_intervals([second, _point()], display_offset="Z")
        expected = {
            "observed_seconds": 5400,
            "online_seconds": 5400,
            "player_hours": 2.0,
            "connection_hours": 4.0,
        }
        self.assertEqual(result["daily"], [{
            "day": "2040-01-03", "server_id": "fictional-arena", **expected,
        }])
        self.assertEqual(result["totals"], expected)

    def test_availability_only_preserves_time_without_activity(self) -> None:
        availability = _point(metric_kind="availability_only", population=99)
        no_population = _point(server_id="fictional-empty", population=None)
        degraded = _point(server_id="fictional-warning", state="degraded")
        result = calculate_intervals([availability, no_population, degraded], display_offset="Z")
        self.assertEqual(result["totals"], {
            "observed_seconds": 10800,
            "online_seconds": 7200,
            "player_hours": 0.0,
            "connection_hours": 0.0,
        })

    def test_rejects_malformed_and_overlapping_intervals(self) -> None:
        for options in (
            {"state": "Online"},
            {"metric_kind": []},
            {"population": True},
            {"population": -1},
            {"population": 10**400},
            {"start": "2040-01-03T03:30:00"},
            {"start": "2040-01-03T03:30:00.000001Z"},
            {"start": "2040-01-03T03:30:00+00:60"},
            {"end": "2040-01-03T03:30:00Z"},
            {"end": "2042-01-03T03:30:00Z"},
        ):
            with self.subTest(fields=tuple(options)):
                with self.assertRaises(ValueError):
                    calculate_intervals([_point(**options)], display_offset="Z")

        for options in (
            {"start": "0001-01-01T00:00:00+01:00", "end": "0001-01-01T02:00:00+01:00"},
            {"start": "9999-12-31T22:00:00-01:00", "end": "9999-12-31T23:00:00-01:00"},
        ):
            with self.subTest(start=options["start"]):
                with self.assertRaisesRegex(ValueError, "outside the display range"):
                    calculate_intervals([_point(**options)], display_offset="Z")

        overlapping = _point(start="2040-01-03T04:00:00Z", end="2040-01-03T05:00:00Z")
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            calculate_intervals([overlapping, _point()], display_offset="Z")


        with self.assertRaisesRegex(ValueError, "10000 intervals"):
            calculate_intervals([None] * 10001, display_offset="Z")
        long_windows = [
            _point(
                server_id=f"fictional-segment-{index}",
                start="2040-01-01T00:00:00Z", end="2041-01-01T00:00:00Z",
            )
            for index in range(28)
        ]
        with self.assertRaisesRegex(ValueError, "10000 daily segments"):
            calculate_intervals(long_windows, display_offset="Z")
