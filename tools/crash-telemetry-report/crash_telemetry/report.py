"""Summarize saved telemetry files for an offline incident review."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import stat
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_DATABASE_BYTES = 128 * 1024 * 1024
SOURCE = "saved telemetry snapshots and JSON records"


class InputFileError(ValueError):
    """A known input error with a safe public description."""


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _verify_regular_file(path: Path, maximum_bytes: int) -> None:
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise InputFileError("expected a regular file")
    if info.st_size > maximum_bytes:
        raise InputFileError(f"input exceeds {maximum_bytes // (1024 * 1024)} MiB")


def _decode_json(payload: bytes | str) -> object:
    def parse_float(text: str) -> float | None:
        value = float(text)
        return value if math.isfinite(value) else None

    if isinstance(payload, bytes):
        payload = payload.decode("utf-8-sig")
    return json.loads(payload, parse_float=parse_float, parse_constant=lambda _: None)


def read_json(
    path: Path, *, label: str = "JSON input"
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        _verify_regular_file(path, MAX_JSON_BYTES)
        with path.open("rb") as handle:
            data = handle.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise InputFileError("input exceeds 4 MiB")
        value = _decode_json(data)
        if not isinstance(value, dict):
            raise InputFileError("expected a JSON object")
        return value, None
    except FileNotFoundError:
        message = "file is missing"
    except InputFileError as exc:
        message = str(exc)
    except OSError:
        message = "could not read file"
    except (ValueError, RecursionError):
        message = "invalid UTF-8 JSON"
    return None, f"{label}: {message}"


def read_cac_snapshot(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        try:
            database = path.resolve(strict=True)
        except RuntimeError:
            raise InputFileError("could not resolve file") from None
        _verify_regular_file(database, MAX_DATABASE_BYTES)
        with database.open("rb") as handle:
            header = handle.read(100)
        if len(header) != 100 or not header.startswith(b"SQLite format 3\0"):
            raise InputFileError("invalid SQLite header")
        if header[18:20] != b"\x01\x01" or any(
            os.path.lexists(database.with_name(database.name + suffix))
            for suffix in ("-journal", "-wal", "-shm")
        ):
            raise InputFileError("expected a closed rollback-journal SQLite file")

        uri = f"{database.as_uri()}?mode=ro&immutable=1"
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as connection:
            connection.execute("PRAGMA trusted_schema = OFF")
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_JSON_BYTES + 1024)
            table = connection.execute("PRAGMA main.table_list('snapshots')").fetchone()
            if table is None or table[2] != "table":
                raise InputFileError("expected a snapshots table")
            row = connection.execute(
                "SELECT captured_at, payload_json "
                "FROM main.snapshots ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            raise InputFileError("no snapshots were found")
        encoded = row[1]
        if not isinstance(encoded, (str, bytes)):
            raise InputFileError("latest snapshot must contain JSON text")
        size = len(encoded.encode("utf-8") if isinstance(encoded, str) else encoded)
        if size > MAX_JSON_BYTES:
            raise InputFileError("latest snapshot exceeds 4 MiB")
        payload = _decode_json(encoded)
        if not isinstance(payload, dict):
            raise InputFileError("latest snapshot must be a JSON object")
        payload["_captured_at"] = row[0]
        return payload, None
    except FileNotFoundError:
        message = "file is missing"
    except InputFileError as exc:
        message = str(exc)
    except (OSError, sqlite3.Error):
        message = "could not read SQLite snapshot"
    except (ValueError, RecursionError):
        message = "invalid UTF-8 JSON in latest snapshot"
    return None, f"snapshot database: {message}"


def _number(value: object) -> int | float | None:
    if type(value) not in (int, float):
        return None
    try:
        return value if math.isfinite(value) else None
    except OverflowError:
        return None


def _maximum(items: list[dict[str, Any]], key: str) -> float | None:
    values = (float(value) for item in items if (value := _number(item.get(key))) is not None)
    return max(values, default=None)


def summarize(
    database: Path,
    sensors_path: Path,
    thermal_guard_path: Path,
    quarantine_path: Path,
    now: datetime,
) -> dict[str, Any]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    errors: list[str] = []
    snapshot, error = read_cac_snapshot(database)
    if error:
        errors.append(error)
    sensors, error = read_json(sensors_path, label="sensor snapshot")
    if error:
        errors.append(error)
    thermal_guard, error = read_json(thermal_guard_path, label="thermal guard")
    if error:
        errors.append(error)
    quarantine, error = read_json(quarantine_path, label="hardware quarantine")
    if error:
        errors.append(error)

    snapshot = snapshot or {}
    sensor_rows = (sensors or {}).get("sensors", [])
    if not isinstance(sensor_rows, list):
        sensor_rows = []
    sensor_rows = [item for item in sensor_rows if isinstance(item, dict)]

    cpu_rows = [
        item
        for item in sensor_rows
        if item.get("sensor_type") == "Temperature"
        and "cpu" in str(item.get("hardware", "")).lower()
    ]
    cpu_package_rows = [
        item for item in cpu_rows if item.get("name") == "CPU Package"
    ]
    storage_rows = [
        item
        for item in sensor_rows
        if item.get("sensor_type") == "Temperature"
        and any(
            marker in str(item.get("hardware", "")).lower()
            for marker in ("ssd", "nvme", "disk")
        )
    ]

    gpus = snapshot.get("gpus", [])
    if not isinstance(gpus, list):
        gpus = []
    gpu_rows = [
        {
            "index": _number(gpu.get("index")),
            "uuid": gpu.get("uuid"),
            "name": gpu.get("name"),
            "temperature_c": _number(gpu.get("temperature_c")),
            "utilization_percent": _number(gpu.get("utilization_percent")),
            "memory_used_mb": _number(gpu.get("memory_used_mb")),
            "power_draw_w": _number(gpu.get("power_draw_w")),
            "pci_bus_id": gpu.get("pci_bus_id"),
            "driver_version": gpu.get("driver_version"),
            "driver_model_current": gpu.get("driver_model_current"),
            "pcie_replays_since_reset": _number(gpu.get("pcie_replays_since_reset")),
        }
        for gpu in gpus
        if isinstance(gpu, dict)
    ]

    captured = parse_timestamp(
        snapshot.get("_captured_at") or snapshot.get("generated")
    )
    age_seconds = None
    if captured:
        age_seconds = max(0.0, (now - captured).total_seconds())

    system = snapshot.get("system", {})
    if not isinstance(system, dict):
        system = {}

    return {
        "schema_version": 1,
        "generated_utc": now.isoformat(),
        "source": SOURCE,
        "cac_snapshot": {
            "captured_utc": captured.isoformat() if captured else None,
            "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
            "fresh": age_seconds is not None and age_seconds <= 180,
            "overall_status": snapshot.get("overall_status"),
            "server_summary": snapshot.get("server_summary"),
        },
        "system": {
            "cpu_percent": _number(system.get("cpu_percent")),
            "memory_percent": _number(system.get("memory_percent")),
            "disk_read_bps": _number(system.get("disk_read_bps")),
            "disk_write_bps": _number(system.get("disk_write_bps")),
            "network_receive_bps": _number(system.get("network_receive_bps")),
            "network_send_bps": _number(system.get("network_send_bps")),
            "uptime_seconds": _number(system.get("uptime_seconds")),
        },
        "temperatures": {
            "sensor_generated": (sensors or {}).get("generated"),
            "cpu_reading_count": len(cpu_rows),
            "maximum_cpu_temperature_c": _maximum(cpu_rows, "value"),
            "cpu_packages": [
                {
                    "hardware": row.get("hardware"),
                    "value_c": _number(row.get("value")),
                }
                for row in cpu_package_rows
            ],
            "maximum_storage_temperature_c": _maximum(storage_rows, "value"),
        },
        "gpus": {
            "count": len(gpu_rows),
            "maximum_temperature_c": _maximum(gpu_rows, "temperature_c"),
            "items": gpu_rows,
        },
        "thermal_guard": {
            "status": (thermal_guard or {}).get("status"),
            "updated_at": (thermal_guard or {}).get("updated_at"),
            "maximum_temperature_c": _number((thermal_guard or {}).get("maximum_temperature_c")),
            "consecutive_high_samples": (thermal_guard or {}).get(
                "consecutive_high_samples"
            ),
            "consecutive_sensor_failures": (thermal_guard or {}).get(
                "consecutive_sensor_failures"
            ),
        },
        "hardware_quarantine": {
            "latched": (quarantine or {}).get("latched"),
            "last_evaluated_utc": (quarantine or {}).get("last_evaluated_utc"),
            "task_registered": (quarantine or {}).get("task_registered"),
            "reasons": (quarantine or {}).get("reasons", []),
        },
        "errors": errors,
    }
