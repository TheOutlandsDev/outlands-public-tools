from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta, timezone

from sensor_snapshot.validator import validate_snapshot


NOW = datetime(2032, 3, 5, 9, 12, tzinfo=UTC)


def _temperature(identifier: str, value: object, *, hardware: str = "Fictional CPU") -> dict:
    return {
        "identifier": identifier,
        "hardware": hardware,
        "sensor_type": "temperature",
        "name": "Thermal sample",
        "value": value,
    }


def _snapshot(**overrides: object) -> dict:
    return {
        "schema_version": 1,
        "generated": NOW.isoformat(),
        "status": "active",
        "administrator": True,
        "sensors": [_temperature("demo-1", 17), _temperature("demo-2", 18)],
        **overrides,
    }


class ValidatorTests(unittest.TestCase):
    def test_rejects_malformed_snapshots_without_echoing_payload_errors(self) -> None:
        for malformed in (None, [], 123, _snapshot(schema_version=True)):
            with self.subTest(malformed=malformed):
                readings, status = validate_snapshot(malformed, now=NOW)
                self.assertEqual(readings, [])
                self.assertIn("schema is missing or invalid", status)
        for collection in (None, {}, 123, "malformed"):
            with self.subTest(collection=collection):
                readings, status = validate_snapshot(_snapshot(sensors=collection), now=NOW)
                self.assertEqual(readings, [])
                self.assertIn("sensor collection is invalid", status)
        readings, status = validate_snapshot(
            _snapshot(status="inactive", error="fictional private detail"), now=NOW
        )
        self.assertEqual(readings, [])
        self.assertIn("status is inactive", status)
        self.assertNotIn("fictional private detail", status)

    def test_preserves_freshness_boundaries_with_explicit_reference_time(self) -> None:
        offset = timezone(timedelta(hours=2))
        for age, accepted in ((20, True), (20.001, False), (-5, True), (-5.001, False)):
            with self.subTest(age=age):
                generated = (NOW - timedelta(seconds=age)).astimezone(offset).isoformat()
                readings, status = validate_snapshot(_snapshot(generated=generated), now=NOW)
                self.assertEqual(bool(readings), accepted)
                self.assertIn("Active:" if accepted else "stale", status)
        readings, _ = validate_snapshot(
            _snapshot(generated=NOW.replace(tzinfo=None).isoformat()), now=NOW
        )
        self.assertEqual(len(readings), 2)
        readings, status = validate_snapshot(
            _snapshot(generated="9999-12-31T23:59:59-23:00"), now=NOW
        )
        self.assertEqual(readings, [])
        self.assertIn("timestamp is invalid", status)
        readings, status = validate_snapshot(_snapshot(), now=NOW, maximum_age_seconds=float("nan"))
        self.assertEqual(readings, [])
        self.assertIn("maximum age is invalid", status)

    def test_filters_non_temperature_nonfinite_and_out_of_range_readings(self) -> None:
        sensors = [
            _temperature("lower", "-50"),
            _temperature("board", 27, hardware="Fictional board"),
            _temperature("upper", 200),
            dict(_temperature("load", 30), sensor_type="load"),
            "invalid",
        ]
        for value in (False, -50.01, 200.01, "NaN", float("inf"), 10**400, []):
            sensors.append(_temperature("invalid", value))
        readings, status = validate_snapshot(_snapshot(sensors=sensors), now=NOW)
        self.assertEqual([reading["identifier"] for reading in readings], ["lower", "board", "upper"])
        self.assertEqual([reading["value"] for reading in readings], [-50.0, 27.0, 200.0])
        self.assertTrue(all(reading["unit"] == "C" for reading in readings))
        self.assertIn("2 CPU reading(s)", status)

        readings, status = validate_snapshot(_snapshot(sensors=sensors[1:]), now=NOW)
        self.assertEqual(readings, [])
        self.assertIn("fewer than two CPU temperature readings", status)
