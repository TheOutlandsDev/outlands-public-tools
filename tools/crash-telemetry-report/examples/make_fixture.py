"""Build an example SQLite export and three JSON files from fictional data."""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    directory = args.destination
    try:
        directory.mkdir()
    except OSError:
        parser.exit(2, "error: select a new directory inside an existing parent\n")

    captured = "2040-01-02T03:04:00Z"
    snapshot = {
        "generated": captured,
        "overall_status": "warning",
        "server_summary": {"healthy": 2, "down": 1},
        "system": {"cpu_percent": 37, "memory_percent": 24},
        "gpus": [
            {"index": 0, "uuid": "Fictional GPU A", "temperature_c": 36},
            {"index": 1, "uuid": "Fictional GPU B", "temperature_c": 41},
        ],
    }
    with closing(sqlite3.connect(directory / "snapshots.db")) as database:
        database.execute("PRAGMA journal_mode=DELETE")
        database.execute("CREATE TABLE snapshots (id INTEGER PRIMARY KEY, captured_at TEXT, payload_json TEXT)")
        database.executemany(
            "INSERT INTO snapshots VALUES (?, ?, ?)",
            [
                (1, "2040-01-02T03:04:05Z", json.dumps({"overall_status": "older row by ID"})),
                (2, captured, json.dumps(snapshot)),
            ],
        )
        database.commit()

    fixtures = {
        "sensors.json": {
            "generated": captured,
            "sensors": [
                {"hardware": "Fictional CPU A", "sensor_type": "Temperature", "name": "CPU Package", "value": 49},
                {"hardware": "Fictional CPU B", "sensor_type": "Temperature", "name": "CPU Package", "value": 46},
                {"hardware": "Fictional NVMe", "sensor_type": "Temperature", "name": "Drive", "value": 32},
            ],
        },
        "thermal-guard.json": {"status": "armed", "maximum_temperature_c": 41},
        "quarantine.json": {"latched": False, "task_registered": False},
    }
    for name, payload in fixtures.items():
        with (directory / name).open("x", encoding="utf-8", newline="\n") as output:
            json.dump(payload, output, indent=2)
            output.write("\n")


if __name__ == "__main__":
    main()
