from __future__ import annotations

import hashlib
import unittest

from availability_evidence.exporter import build_safety, build_signal


OBSERVED_UTC = "2040-01-02T03:04:05Z"


class AvailabilityEvidenceTests(unittest.TestCase):
    def test_stale_system_data_is_suppressed(self) -> None:
        snapshot = {
            "source_health": {"system": {"state": "stale"}},
            "system": {
                "disks": [{"percent": 99.0}],
                "hardware_sensors": [
                    {"sensor_type": "Temperature", "name": "CPU Core", "value": 100}
                ],
                "hardware_events": [{"category": "WHEA Memory", "severity": "critical"}],
                "source_status": {"Windows diagnostics": "Active: storage coverage"},
            },
            "gpus": [{"temperature_c": 94}],
            "ai": {"hardware_quarantine": {"latched": True}},
        }
        self.assertEqual(build_safety(snapshot), {
            "diskFreePercent": None,
            "hardwareQuarantine": "unavailable",
            "maximumGpuTemperatureC": None,
            "maximumCpuTemperatureC": None,
            "criticalHardwareEvents": [],
        })

    def test_hash_is_stable_for_reordered_nested_keys(self) -> None:
        first = {"details": {"b": "caf\u00e9", "a": [1, 2]}, "status": "ok"}
        second = {"status": "ok", "details": {"a": [1, 2], "b": "caf\u00e9"}}
        canonical = '{"details":{"a":[1,2],"b":"caf\u00e9"},"status":"ok"}'.encode("utf-8")
        expected = hashlib.sha256(canonical).hexdigest()
        for result in (first, second):
            with self.subTest(result=result):
                digest = build_signal("proven", "fictional", OBSERVED_UTC, result)
                self.assertEqual(digest["resultSha256"], expected)
        changed = {"status": "ok", "details": {"a": [2, 1], "b": "caf\u00e9"}}
        self.assertNotEqual(
            build_signal("proven", "fictional", OBSERVED_UTC, changed)["resultSha256"],
            expected,
        )

    def test_numeric_bounds_and_malformed_snapshot_sections(self) -> None:
        snapshot = {
            "source_health": {"system": {"state": "FRESH"}},
            "system": {
                "disks": [None, {"percent": "80.1234"}, {"percent": -1}, {"percent": 101},
                          {"percent": float("inf")}, {"percent": 10**400}],
                "hardware_sensors": [
                    {"sensor_type": "Temperature", "name": "CPU Package", "value": 45},
                    {"sensor_type": "Temperature", "name": "GPU Edge", "value": 95},
                    {"sensor_type": "Fan", "name": "CPU Fan", "value": 185},
                ],
            },
            "gpus": [{"temperature_c": 32}, {"temperature_c": 201},
                     {"temperature_c": float("nan")}, {"temperature_c": 10**400}],
        }
        result = build_safety(snapshot)
        self.assertEqual(result["diskFreePercent"], 19.877)
        self.assertEqual(result["maximumGpuTemperatureC"], 32)
        self.assertEqual(result["maximumCpuTemperatureC"], 45)
        self.assertEqual(result["hardwareQuarantine"], "unavailable")
        for malformed in (None, [], {"source_health": []}, {**snapshot, "gpus": {}},
                          {**snapshot, "system": {"disks": None}}):
            with self.subTest(malformed_type=type(malformed)):
                with self.assertRaisesRegex(ValueError, r"must be a JSON (array|object)"):
                    build_safety(malformed)

    def test_rejects_invalid_signal_state_and_nonfinite_results(self) -> None:
        for state in ("unknown", None, []):
            with self.subTest(state=state):
                with self.assertRaisesRegex(ValueError, "state is not allowlisted"):
                    build_signal(state, "fictional", OBSERVED_UTC, {})
        for result in ({"bad": float("inf")}, {"bad": [float("nan")]}, {1, 2}):
            with self.subTest(result=result):
                with self.assertRaisesRegex(ValueError, "result must be finite UTF-8 JSON"):
                    build_signal("failed", "fictional", OBSERVED_UTC, result)
        signal = build_signal("unavailable", "x" * 90, OBSERVED_UTC, [])
        self.assertEqual(signal["method"], "x" * 80)
