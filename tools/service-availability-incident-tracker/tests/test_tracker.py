from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from availability_tracker import tracker


class TrackerTests(unittest.TestCase):
    def test_optional_checks_do_not_override_successful_required_checks(self) -> None:
        checks = [{"ok": True}, {"required": False, "ok": False}]
        self.assertEqual(tracker.determine_overall(checks), "online")
        self.assertEqual(
            tracker.determine_overall([{"required": False, "ok": True}]),
            "degraded",
        )
        self.assertEqual(tracker.determine_overall([]), "offline")

    def test_incident_retains_worst_state_until_recovery(self) -> None:
        start = datetime(2040, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=2)))
        state, completed = tracker.apply_transition({}, "degraded", start)
        self.assertIsNone(completed)
        state, completed = tracker.apply_transition(
            state, "offline", start + timedelta(minutes=1)
        )
        self.assertIsNone(completed)
        state, completed = tracker.apply_transition(
            state, "degraded", start + timedelta(minutes=2)
        )
        self.assertIsNone(completed)
        state, completed = tracker.apply_transition(
            state, "online", start + timedelta(minutes=3)
        )
        self.assertIsNone(state["activeIncident"])
        self.assertEqual(
            completed,
            {
                "startedAt": "2040-01-02T01:04:05Z",
                "initialState": "degraded",
                "worstState": "offline",
                "recoveredAt": "2040-01-02T01:07:05Z",
                "durationSeconds": 180,
            },
        )

    def test_failed_atomic_replace_preserves_existing_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "state.json"
            tracker.write_json_atomic(target, {"previousOverall": "offline"})
            before = target.read_bytes()

            def fail_replace(temporary: Path, destination: Path) -> None:
                self.assertEqual(destination, target)
                self.assertEqual(temporary.parent, target.parent)
                self.assertNotEqual(temporary, target)
                self.assertEqual(
                    tracker.read_json(temporary, None),
                    {"previousOverall": "online"},
                )
                raise PermissionError("fictional replace failure")

            with patch.object(tracker.os, "replace", side_effect=fail_replace):
                with self.assertRaises(PermissionError):
                    tracker.write_json_atomic(target, {"previousOverall": "online"})

            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(list(root.iterdir()), [target])
