from __future__ import annotations

import unittest

from availability_evidence.exporter import build_safety, build_signal


class AvailabilityExportTests(unittest.TestCase):
    def test_safety_projects_only_bounded_guardian_fields(self) -> None:
        snapshot = {
            "source_health": {"system": {"state": "fresh"}},
            "system": {
                "disks": [{"percent": 60.0}, {"percent": 80.0}],
                "hardware_sensors": [
                    {
                        "sensor_type": "Temperature",
                        "hardware": "Fictional CPU Package",
                        "name": "Core Max",
                        "value": 74.0,
                    }
                ],
                "hardware_events": [
                    {"category": "Storage", "severity": "critical"},
                    {"category": "Application crash", "severity": "critical"},
                ],
                "source_status": {
                    "Windows diagnostics": (
                        "Active: Windows event logs | 1 new | storage coverage"
                    )
                },
            },
            "gpus": [{"temperature_c": 71.0}],
            "ai": {"hardware_quarantine": {"latched": False}},
        }
        self.assertEqual(build_safety(snapshot), {
            "diskFreePercent": 20.0,
            "hardwareQuarantine": "clear",
            "maximumGpuTemperatureC": 71.0,
            "maximumCpuTemperatureC": 74.0,
            "criticalHardwareEvents": ["storage"],
        })

    def test_signal_contains_only_hash_not_raw_result(self) -> None:
        signal = build_signal(
            "proven",
            "fixture",
            "2040-01-02T03:04:05Z",
            {"pid": 41, "path": r"C:\private-example\fictional-service.exe"},
        )
        self.assertEqual(set(signal), {
            "state",
            "observedAtUtc",
            "method",
            "resultSha256",
        })
        self.assertEqual(len(signal["resultSha256"]), 64)
        self.assertNotIn("private", str(signal).lower())
