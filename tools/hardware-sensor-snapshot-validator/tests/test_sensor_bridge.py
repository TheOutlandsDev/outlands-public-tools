from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from sensor_snapshot.validator import validate_snapshot


REFERENCE_TIME = datetime(2032, 3, 5, 9, 12, tzinfo=UTC)


def _payload(generated: datetime, *, administrator: bool = True) -> dict:
    return {
        "schema_version": 1,
        "generated": generated.isoformat(),
        "status": "active",
        "administrator": administrator,
        "sensors": [
            {
                "identifier": "/fictional/cpu/0/temperature",
                "hardware": "Fictional CPU",
                "sensor_type": "Temperature",
                "name": "CPU Package",
                "value": 51,
            },
            {
                "identifier": "/fictional/cpu/1/temperature",
                "hardware": "Fictional CPU",
                "sensor_type": "Temperature",
                "name": "CPU Package",
                "value": 49,
            },
        ],
    }


def _read_fixture(payload: dict) -> tuple[list[dict], str]:
    with TemporaryDirectory() as directory:
        path = Path(directory) / "hardware-sensors.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_snapshot(json.loads(path.read_text(encoding="utf-8")), now=REFERENCE_TIME)


class SensorBridgeTests(unittest.TestCase):
    def test_sensor_bridge_accepts_fresh_elevated_cpu_temperatures(self) -> None:
        sensors, status = _read_fixture(_payload(REFERENCE_TIME))
        self.assertEqual([sensor["value"] for sensor in sensors], [51.0, 49.0])
        self.assertTrue(status.startswith("Active:"))

    def test_sensor_bridge_rejects_stale_output(self) -> None:
        sensors, status = _read_fixture(_payload(REFERENCE_TIME - timedelta(minutes=1)))
        self.assertEqual(sensors, [])
        self.assertIn("stale", status)

    def test_sensor_bridge_rejects_non_admin_output(self) -> None:
        sensors, status = _read_fixture(_payload(REFERENCE_TIME, administrator=False))
        self.assertEqual(sensors, [])
        self.assertIn("administrator", status)
