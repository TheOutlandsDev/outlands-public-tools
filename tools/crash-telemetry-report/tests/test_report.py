import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from crash_telemetry.report import summarize


NOW = datetime(2040, 1, 2, 12, tzinfo=timezone.utc)


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.database = self.root / "snapshot #1.db"
        self.sensors = self.root / "sensors.json"
        self.thermal = self.root / "thermal.json"
        self.quarantine = self.root / "quarantine.json"
        for path in (self.sensors, self.thermal, self.quarantine):
            path.write_text("{}", encoding="utf-8")

    def write_snapshots(self, rows: list[tuple[str, str]]) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "CREATE TABLE snapshots("
                "id INTEGER PRIMARY KEY, captured_at TEXT, payload_json TEXT)"
            )
            connection.executemany(
                "INSERT INTO snapshots(captured_at,payload_json) VALUES (?,?)", rows
            )
            connection.commit()
        finally:
            connection.close()

    def report(self, at: datetime = NOW) -> dict:
        return summarize(self.database, self.sensors, self.thermal, self.quarantine, at)

    def test_latest_snapshot_and_freshness_boundary(self) -> None:
        self.write_snapshots([
            ((NOW - timedelta(minutes=1)).isoformat(), '{"overall_status":"previous"}'),
            ((NOW - timedelta(minutes=3)).isoformat(), '{"overall_status":"latest"}'),
        ])
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}

        current = self.report()["cac_snapshot"]
        self.assertEqual(current["overall_status"], "latest")
        self.assertEqual(current["age_seconds"], 180.0)
        self.assertTrue(current["fresh"])
        older = self.report(NOW + timedelta(milliseconds=1))["cac_snapshot"]
        self.assertEqual(older["age_seconds"], 180.001)
        self.assertFalse(older["fresh"])

        self.assertEqual({path.name: path.read_bytes() for path in self.root.iterdir()}, before)

    def test_handles_missing_and_malformed_inputs(self) -> None:
        self.sensors.unlink()
        self.thermal.write_bytes(b"\xff")
        self.quarantine.write_text("[]", encoding="utf-8")
        expected_json_errors = [
            "sensor snapshot: file is missing",
            "thermal guard: invalid UTF-8 JSON",
            "hardware quarantine: expected a JSON object",
        ]
        self.assertEqual(self.report()["errors"], [
            "snapshot database: file is missing", *expected_json_errors
        ])

        self.write_snapshots([(NOW.isoformat(), "{malformed")])
        before = self.database.read_bytes()
        self.assertEqual(self.report()["errors"], [
            "snapshot database: invalid UTF-8 JSON in latest snapshot", *expected_json_errors
        ])
        self.assertEqual(self.database.read_bytes(), before)

        sidecar = self.database.with_name(self.database.name + "-wal")
        sidecar.write_bytes(b"fictional sidecar")
        self.assertEqual(self.report()["errors"], [
            "snapshot database: expected a closed rollback-journal SQLite file",
            *expected_json_errors,
        ])
        self.assertEqual(sidecar.read_bytes(), b"fictional sidecar")

        sidecar.unlink()
        self.database.unlink()
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "CREATE VIEW snapshots AS "
                "SELECT 1 AS id, '' AS captured_at, '{}' AS payload_json"
            )
            connection.commit()
        finally:
            connection.close()
        self.assertEqual(self.report()["errors"], [
            "snapshot database: expected a snapshots table", *expected_json_errors
        ])

    def test_filters_invalid_readings_and_shapes(self) -> None:
        self.write_snapshots([(
            NOW.isoformat(),
            '{"system":["wrong shape"],"gpus":'
            '[null,{"temperature_c":NaN},{"temperature_c":1e999},'
            '{"temperature_c":true},{"temperature_c":37}]}',
        )])
        self.sensors.write_text(json.dumps({"sensors": [
            "invalid row",
            {"hardware": "CPU", "sensor_type": "Temperature", "name": "CPU Package",
             "value": 10 ** 400},
            {"hardware": "CPU", "sensor_type": "Temperature", "value": True},
            {"hardware": "CPU", "sensor_type": "Temperature", "value": 42},
            {"hardware": "SSD", "sensor_type": "Temperature", "value": 31},
        ]}), encoding="utf-8")
        self.thermal.write_text('{"maximum_temperature_c":Infinity}', encoding="utf-8")

        result = self.report()

        self.assertEqual(result["errors"], [])
        self.assertIsNone(result["system"]["cpu_percent"])
        self.assertEqual(result["gpus"]["count"], 4)
        self.assertEqual([row["temperature_c"] for row in result["gpus"]["items"]], [
            None, None, None, 37,
        ])
        self.assertEqual(result["gpus"]["maximum_temperature_c"], 37)
        self.assertEqual(result["temperatures"]["maximum_cpu_temperature_c"], 42)
        self.assertEqual(result["temperatures"]["maximum_storage_temperature_c"], 31)
        self.assertEqual(result["temperatures"]["cpu_packages"], [{"hardware": "CPU", "value_c": None}])
        self.assertIsNone(result["thermal_guard"]["maximum_temperature_c"])
        json.dumps(result, allow_nan=False)
