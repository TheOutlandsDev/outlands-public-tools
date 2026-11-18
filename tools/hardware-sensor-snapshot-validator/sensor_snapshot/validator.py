"""Offline validation for hardware sensor snapshot JSON."""

import math
from datetime import UTC, datetime
from typing import Any


def _is_cpu_temperature(sensor: dict[str, Any]) -> bool:
    if str(sensor.get("sensor_type", "")).casefold() != "temperature":
        return False
    label = f"{sensor.get('hardware', '')} {sensor.get('name', '')}".casefold()
    return any(token in label for token in ("cpu", "xeon", "package", "core"))


def _label(sensor: dict[str, Any], key: str, default: str, limit: int) -> str:
    value = sensor.get(key)
    return value[:limit] if isinstance(value, str) else default


def validate_snapshot(
    payload: object, *, now: datetime, maximum_age_seconds: float = 20.0
) -> tuple[list[dict[str, Any]], str]:
    """Filter saved readings using the supplied timestamp and declared metadata."""
    if not (
        isinstance(payload, dict)
        and type(payload.get("schema_version")) is int
        and payload["schema_version"] == 1
    ):
        return [], "Unavailable: sensor snapshot schema is missing or invalid"
    if payload.get("administrator") is not True:
        return [], "Unavailable: sensor snapshot does not declare administrator execution"
    status = payload.get("status")
    if not isinstance(status, str) or status.casefold() != "active":
        return [], "Unavailable: sensor snapshot status is inactive"

    try:
        if (
            now.utcoffset() is None
            or isinstance(maximum_age_seconds, bool)
            or not math.isfinite(maximum_age_seconds)
            or maximum_age_seconds < 0
        ):
            return [], "Unavailable: validation time or maximum age is invalid"
        reference_time = now.astimezone(UTC)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return [], "Unavailable: validation time or maximum age is invalid"
    try:
        generated = datetime.fromisoformat(payload["generated"])
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        age = (reference_time - generated.astimezone(UTC)).total_seconds()
    except (KeyError, TypeError, ValueError, OverflowError):
        return [], "Unavailable: sensor snapshot timestamp is invalid"
    if age < -5.0 or age > maximum_age_seconds:
        return [], f"Unavailable: sensor snapshot is stale ({age:.0f}s)"

    sensors = payload.get("sensors")
    if not isinstance(sensors, list):
        return [], "Unavailable: sensor collection is invalid"

    readings: list[dict[str, Any]] = []
    for item in sensors:
        if not isinstance(item, dict):
            continue
        sensor_type = item.get("sensor_type")
        if not isinstance(sensor_type, str) or sensor_type.casefold() != "temperature":
            continue
        value = item.get("value")
        if isinstance(value, bool):
            continue
        try:
            temperature = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(temperature) or not -50.0 <= temperature <= 200.0:
            continue
        readings.append(
            {
                "identifier": _label(item, "identifier", "", 300),
                "hardware": _label(item, "hardware", "Unknown", 200),
                "sensor_type": "Temperature",
                "name": _label(item, "name", "Temperature", 200),
                "value": temperature,
                "unit": "C",
                "source": "Hardware Sensor Bridge",
            }
        )
    cpu_count = sum(_is_cpu_temperature(item) for item in readings)
    if cpu_count < 2:
        return [], "Unavailable: sensor snapshot has fewer than two CPU temperature readings"
    return readings, (
        f"Active: {len(readings)} temperature sensor(s), {cpu_count} CPU reading(s)"
    )
