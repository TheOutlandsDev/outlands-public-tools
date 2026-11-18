"""Build bounded evidence from supplied telemetry and signal records."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from typing import Any


SIGNAL_STATES = {"proven", "failed", "unavailable"}


def _canonical_hash(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise ValueError("signal result must be finite UTF-8 JSON") from None
    return hashlib.sha256(payload).hexdigest()


def build_signal(
    state: str, method: str, observed_utc: str, result: Any,
) -> dict[str, Any]:
    """Return signal metadata and a digest of the supplied result."""
    if not isinstance(state, str) or state not in SIGNAL_STATES:
        raise ValueError("signal state is not allowlisted")
    if not isinstance(method, str) or not isinstance(observed_utc, str):
        raise ValueError("signal method and timestamp must be strings")
    return {
        "state": state,
        "observedAtUtc": observed_utc,
        "method": method[:80],
        "resultSha256": _canonical_hash(result),
    }


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _rows(value: Any, name: str) -> Iterator[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return (row for row in value if isinstance(row, dict))


def _folded(value: Any) -> str:
    return value.casefold() if isinstance(value, str) else ""


def _maximum(
    values: Iterable[Any], *, minimum: float = -50.0, maximum: float = 200.0,
) -> float | None:
    normalized: list[float] = []
    for value in values:
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if minimum <= number <= maximum:
            normalized.append(number)
    return max(normalized, default=None)


def build_safety(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Project the allowlisted metrics and recorded quarantine status."""
    snapshot = _object(snapshot, "snapshot")
    source_health = _object(snapshot.get("source_health", {}), "source_health")
    system_source = _object(source_health.get("system", {}), "source_health.system")
    system_fresh = _folded(system_source.get("state")) == "fresh"
    system = _object(snapshot.get("system", {}), "system") if system_fresh else {}
    gpus = _rows(snapshot.get("gpus", []), "gpus") if system_fresh else ()
    disks = _rows(system.get("disks", []), "system.disks")
    sensors = _rows(system.get("hardware_sensors", []), "system.hardware_sensors")
    hardware_events = _rows(system.get("hardware_events", []), "system.hardware_events")

    maximum_disk_used = _maximum(
        (disk.get("percent") for disk in disks), minimum=0.0, maximum=100.0,
    )
    gpu_temperature = _maximum(item.get("temperature_c") for item in gpus)
    cpu_temperature = _maximum(
        item.get("value")
        for item in sensors
        if _folded(item.get("sensor_type")) == "temperature"
        and any(
            token in f"{_folded(item.get('hardware'))} {_folded(item.get('name'))}"
            for token in ("cpu", "xeon", "package", "core")
        )
    )

    events: set[str] = set()
    for event in hardware_events:
        category = _folded(event.get("category"))
        severity = _folded(event.get("severity"))
        if severity not in {"warning", "critical"}:
            continue
        if "whea" in category:
            events.add("whea")
        if "nvidia" in category or "display" in category:
            events.add("nvidia")
        if any(token in category for token in ("storage", "disk", "ntfs", "stor")):
            events.add("storage")

    source_status = _object(system.get("source_status", {}), "system.source_status")
    diagnostics_status = _folded(source_status.get("Windows diagnostics"))
    storage_coverage = (
        diagnostics_status.startswith("active:") and "storage coverage" in diagnostics_status
    )
    quarantine_state = "unavailable"
    if storage_coverage:
        ai = _object(snapshot.get("ai", {}), "ai")
        quarantine = _object(ai.get("hardware_quarantine", {}), "ai.hardware_quarantine")
        latched = quarantine.get("latched", False)
        if latched is True:
            quarantine_state = "latched"
        elif latched is False and quarantine.get("available", True) is True:
            quarantine_state = "clear"

    return {
        "diskFreePercent": (
            round(100.0 - maximum_disk_used, 3) if maximum_disk_used is not None else None
        ),
        "hardwareQuarantine": quarantine_state,
        "maximumGpuTemperatureC": gpu_temperature,
        "maximumCpuTemperatureC": cpu_temperature,
        "criticalHardwareEvents": sorted(events),
    }
