"""Original tampering and replay checks with fictional saved snapshots."""

from datetime import UTC, datetime
import json
from pathlib import Path
import unittest

from game_event_statistics import ComputeBackend
from telemetry_snapshot_replay import TelemetryExportError, replay_snapshot, validate_snapshot


FIXED_NOW = datetime(2030, 7, 27, 23, 0, tzinfo=UTC)
PROGRAMS = ("rust", "dayz", "main_spt", "modern_warfare", "zomboid")
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _snapshot(program):
    return json.loads((EXAMPLES / f"{program}.json").read_bytes())


class TelemetryExporterTests(unittest.TestCase):
    def test_tampered_snapshot_is_rejected(self) -> None:
        snapshot = _snapshot("dayz")
        snapshot["records"][0]["event"] = "tampered"
        with self.assertRaises(TelemetryExportError):
            validate_snapshot(snapshot)

    def test_offline_replay_runs_compute_without_model_gpu_or_writes(self) -> None:
        for program in PROGRAMS:
            snapshot = _snapshot(program)
            replay = replay_snapshot(
                snapshot,
                backend=ComputeBackend(now=lambda: FIXED_NOW),
            )
            self.assertEqual(replay["program"], program)
            self.assertEqual(replay["record_count"], snapshot["record_count"])
            self.assertFalse(replay["runtime"]["model_used"])
            self.assertFalse(replay["runtime"]["gpu_used"])
            self.assertFalse(replay["runtime"]["network_used"])
            self.assertFalse(replay["runtime"]["server_action_performed"])
            self.assertFalse(replay["runtime"]["write_performed"])
            self.assertTrue(replay["features"]["audit"]["read_only"])
