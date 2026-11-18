from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


from crash_telemetry.report import summarize


class CrashTelemetryTests(unittest.TestCase):
    def test_reads_existing_sources_without_hardware_polling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "snapshot.db"
            sensors = root / "sensors.json"
            thermal = root / "thermal.json"
            quarantine = root / "quarantine.json"

            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE snapshots("
                "id INTEGER PRIMARY KEY, captured_at TEXT, payload_json TEXT)"
            )
            payload = {
                "generated": "2040-01-02T20:54:00+00:00",
                "overall_status": "warning",
                "server_summary": {"healthy": 5, "down": 1},
                "system": {
                    "cpu_percent": 37,
                    "memory_percent": 20,
                    "uptime_seconds": 1000,
                },
                "gpus": [
                    {
                        "index": 0,
                        "uuid": "fictional-gpu-a",
                        "name": "Fictional GPU",
                        "temperature_c": 30,
                    },
                    {
                        "index": 1,
                        "uuid": "fictional-gpu-b",
                        "name": "Fictional GPU",
                        "temperature_c": 31,
                    },
                ],
            }
            connection.execute(
                "INSERT INTO snapshots(captured_at,payload_json) VALUES (?,?)",
                ("2040-01-02T20:54:00+00:00", json.dumps(payload)),
            )
            connection.commit()
            connection.close()

            sensors.write_text(
                json.dumps(
                    {
                        "generated": "2040-01-02T16:54:00-04:00",
                        "sensors": [
                            {
                                "hardware": "CPU 0",
                                "sensor_type": "Temperature",
                                "name": "CPU Package",
                                "value": 49,
                            },
                            {
                                "hardware": "CPU 1",
                                "sensor_type": "Temperature",
                                "name": "CPU Package",
                                "value": 48,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            thermal.write_text(
                json.dumps({"status": "armed", "maximum_temperature_c": 31}),
                encoding="utf-8",
            )
            quarantine.write_text(
                json.dumps({"latched": False, "task_registered": False}),
                encoding="utf-8",
            )

            result = summarize(
                database,
                sensors,
                thermal,
                quarantine,
                datetime(2040, 1, 2, 20, 55, tzinfo=timezone.utc),
            )

            self.assertEqual(result["gpus"]["count"], 2)
            self.assertEqual(result["gpus"]["maximum_temperature_c"], 31)
            self.assertEqual(
                result["temperatures"]["maximum_cpu_temperature_c"], 49
            )
            self.assertEqual(result["source"], (
                "saved telemetry snapshots and JSON records"
            ))
            self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
