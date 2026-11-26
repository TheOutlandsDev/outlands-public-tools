"""Original normalization and statistics assertions with fictional actors."""

import unittest
from datetime import UTC, datetime

from game_event_statistics import ComputeBackend


FIXED_NOW = datetime(2030, 7, 27, 22, 0, tzinfo=UTC)


class ComputeBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = ComputeBackend(now=lambda: FIXED_NOW)

    def test_normalization_discards_raw_messages_and_maps_game_events(self) -> None:
        payload = {
            "records": [
                {
                    "timestamp": "2030-07-27T20:00:00Z",
                    "event": "PMC kill",
                    "player": "Demo Actor A",
                    "target": "Demo Actor B",
                    "weapon": "rifle",
                    "message": "raw log content must not be retained",
                },
                {"event": "exfil", "actor": "Demo Actor A", "session": "demo-raid-1"},
                {"event": "unmapped custom event", "actor": "Demo Actor B"},
            ]
        }
        result = self.backend.execute("fika", "normalize_events", payload)
        events = result["result"]["events"]
        self.assertEqual([event["event"] for event in events], ["kill", "extract", "other"])
        self.assertNotIn("message", events[0])
        self.assertEqual(events[0]["context"]["weapon"], "rifle")
        self.assertFalse(result["audit"]["write_performed"])
        self.assertFalse(result["audit"]["gpu_used"])

    def test_behavior_features_are_deterministic_and_actor_scoped(self) -> None:
        payload = {
            "records": [
                {"event": "frag", "actor": "Demo Actor C", "target": "Demo Target", "session": "demo-match-1"},
                {"event": "hit", "actor": "Demo Actor C", "value": 75, "session": "demo-match-1"},
                {"event": "assisted", "actor": "Demo Actor C", "session": "demo-match-1"},
                {"event": "died", "actor": "Demo Actor C", "session": "demo-match-1"},
            ]
        }
        first = self.backend.execute("iw4x", "build_behavior_features", payload)
        second = self.backend.execute("iw4x", "build_behavior_features", payload)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertEqual(first["result_sha256"], second["result_sha256"])
        actor = first["result"]["actor_features"][0]
        self.assertEqual(actor["kills"], 1)
        self.assertEqual(actor["deaths"], 1)
        self.assertEqual(actor["assists"], 1)
        self.assertEqual(actor["damage"], 75.0)
        self.assertFalse(first["result"]["behavior_control_generated"])
