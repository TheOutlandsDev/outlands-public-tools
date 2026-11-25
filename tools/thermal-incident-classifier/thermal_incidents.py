"""Classify CPU, storage and GPU thermal incidents in a saved telemetry snapshot."""

import argparse
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any


MAX_SNAPSHOT_BYTES = 1024 * 1024
DEFAULT_THRESHOLDS = {
    "cpu_warning_c": 75.0, "cpu_critical_c": 85.0,
    "storage_warning_c": 75.0, "storage_critical_c": 85.0,
    "gpu_warning_c": 75.0, "gpu_critical_c": 88.0,
}


@dataclass(frozen=True, slots=True)
class IncidentCandidate:
    source: str
    code: str
    severity: str
    summary: str
    evidence: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        raw = f"{self.source}|{self.code}|{self.summary}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


def _candidate(
    source: str,
    code: str,
    severity: str,
    summary: str,
    evidence: dict[str, Any],
) -> IncidentCandidate:
    return IncidentCandidate(source, code, severity, summary[:500], evidence)


def classify_thermal_incidents(snapshot: dict[str, Any], thresholds: dict[str, float]) -> list[IncidentCandidate]:
    """Apply the original category-specific thermal thresholds."""
    incidents: list[IncidentCandidate] = []
    system = snapshot.get("system", {})
    static_temperature_markers = (
        "warning temperature",
        "critical temperature",
        "temperature limit",
        "temperature threshold",
        "trip point",
        "tjmax",
    )
    for sensor in system.get("hardware_sensors", []):
        if str(sensor.get("sensor_type", "")).casefold() != "temperature":
            continue
        name = str(sensor.get("name", "Temperature"))
        if any(marker in name.casefold() for marker in static_temperature_markers):
            continue
        label = f"{sensor.get('hardware', '')} {name}".casefold()
        if any(token in label for token in ("cpu", "xeon", "package", "core")):
            category = "cpu"
        elif any(
            token in label
            for token in ("ssd", "hdd", "nvme", "disk", "storage")
        ):
            category = "storage"
        else:
            continue
        try:
            value = float(sensor["value"])
        except (KeyError, TypeError, ValueError):
            continue
        warning = thresholds.get(f"{category}_warning_c", 75.0)
        critical = thresholds.get(f"{category}_critical_c", 85.0)
        if value < warning:
            continue
        severity = "critical" if value >= critical else "warning"
        incidents.append(
            _candidate(
                f"sensor:{sensor.get('identifier', name)}",
                "temperature",
                severity,
                f"{sensor.get('hardware')} / {name} is {value:.1f} C",
                {
                    "value": value,
                    "warning": warning,
                    "critical": critical,
                    "source": sensor.get("source", "Hardware sensor"),
                },
            )
        )
    for gpu in snapshot.get("gpus", []):
        temperature = gpu.get("temperature_c")
        if temperature is not None:
            value = float(temperature)
            warning = thresholds.get("gpu_warning_c", 75.0)
            critical = thresholds.get("gpu_critical_c", 88.0)
            if value >= warning:
                severity = "critical" if value >= critical else "warning"
                incidents.append(
                    _candidate(
                        f"gpu:{gpu.get('uuid', gpu.get('index'))}",
                        "temperature",
                        severity,
                        f"GPU {gpu.get('index')} temperature is {value:.0f} C",
                        gpu,
                    )
                )
    return incidents


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def finite_float(raw):
    value = float(raw)
    if not isfinite(value):
        raise ValueError("Nonfinite JSON number")
    return value


def read_json(path: Path) -> Any:
    try:
        if not path.is_file():
            raise OSError
        with path.open("rb") as stream:
            payload = stream.read(MAX_SNAPSHOT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the telemetry input.") from None

    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("The telemetry input exceeds the 1 MiB limit.")

    try:
        return json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (ValueError, RecursionError):
        raise ValueError("Invalid telemetry JSON.") from None



def read_snapshot(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("The telemetry snapshot must be an object.")
    system = data.get("system", {})
    if not isinstance(system, dict):
        raise ValueError("System telemetry must be an object.")
    groups = (system.get("hardware_sensors", []), data.get("gpus", []))
    for rows in groups:
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError("Sensor and GPU lists must contain objects.")
    if sum(map(len, groups)) > 1000:
        raise ValueError("The telemetry snapshot exceeds 1000 readings.")
    for gpu in groups[1]:
        temperature = gpu.get("temperature_c")
        if temperature is not None:
            try:
                if not isfinite(float(temperature)):
                    raise ValueError
            except (TypeError, ValueError, OverflowError):
                raise ValueError("Invalid telemetry temperature.") from None
    return data


def read_thresholds(path: Path) -> dict[str, float]:
    values = read_json(path)
    if not isinstance(values, dict) or values.keys() - DEFAULT_THRESHOLDS.keys():
        raise ValueError("Invalid thermal threshold fields.")
    try:
        if any(type(value) not in (int, float) or not isfinite(value) for value in values.values()):
            raise ValueError
    except (ValueError, OverflowError):
        raise ValueError("Thresholds must be finite numbers.") from None
    effective = {**DEFAULT_THRESHOLDS, **values}
    for category in ("cpu", "storage", "gpu"):
        if effective[f"{category}_warning_c"] > effective[f"{category}_critical_c"]:
            raise ValueError("Thermal warning thresholds must not exceed critical thresholds.")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved telemetry snapshot JSON")
    parser.add_argument("--thresholds", type=Path, help="Optional JSON threshold overrides in Celsius")
    args = parser.parse_args()
    try:
        snapshot = read_snapshot(args.snapshot)
        thresholds = read_thresholds(args.thresholds) if args.thresholds is not None else {}
        try:
            candidates = classify_thermal_incidents(snapshot, thresholds)
            if any(item.source.startswith("sensor:") and not isfinite(item.evidence["value"])
                   for item in candidates):
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Invalid telemetry temperature.") from None
        incidents = [
            {
                "code": item.code,
                "evidence": item.evidence,
                "fingerprint": item.fingerprint,
                "severity": item.severity,
                "source": item.source,
                "summary": item.summary,
            }
            for item in candidates
        ]
        report = json.dumps({"incidents": incidents}, indent=2, sort_keys=True, allow_nan=False)
    except (UnicodeError, RecursionError):
        parser.exit(2, "Invalid telemetry text or nesting.\n")
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
