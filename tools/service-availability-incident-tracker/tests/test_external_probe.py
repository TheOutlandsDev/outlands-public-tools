from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from availability_tracker import tracker as external_probe


class ExternalProbeTests(unittest.TestCase):
    def test_overall_states(self) -> None:
        self.assertEqual(
            external_probe.determine_overall([{"required": True, "ok": True}]),
            "online",
        )
        self.assertEqual(
            external_probe.determine_overall(
                [
                    {"required": True, "ok": False},
                    {"required": True, "ok": True},
                ]
            ),
            "degraded",
        )
        self.assertEqual(
            external_probe.determine_overall([{"required": True, "ok": False}]),
            "offline",
        )

    def test_incident_open_and_recovery(self) -> None:
        started = datetime(2040, 1, 2, 3, 4, tzinfo=timezone.utc)
        state, completed = external_probe.apply_transition({}, "offline", started)
        self.assertIsNone(completed)
        self.assertEqual(state["activeIncident"]["worstState"], "offline")
        state, completed = external_probe.apply_transition(
            state, "online", started + timedelta(minutes=7)
        )
        self.assertIsNone(state["activeIncident"])
        self.assertEqual(completed["durationSeconds"], 420)

    def test_atomic_json_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "latest.json"
            external_probe.write_json_atomic(path, {"ok": True})
            self.assertEqual(external_probe.read_json(path, {}), {"ok": True})


if __name__ == "__main__":
    unittest.main()
