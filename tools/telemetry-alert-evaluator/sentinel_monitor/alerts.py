from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from .models import AlertEvent, SystemSnapshot, is_live_temperature_sensor


@dataclass(slots=True)
class _Candidate:
    key: str
    label: str
    value: float
    threshold_name: str
    unit: str


@dataclass(slots=True)
class _AlertState:
    severity: str = "normal"
    consecutive: int = 0
    last_emitted: datetime | None = None


class AlertEngine:
    def __init__(self, config: dict[str, Any]) -> None:
        self.thresholds = config["thresholds"]
        self.sustain_samples = max(1, int(config["alert_sustain_samples"]))
        self.repeat_after = timedelta(minutes=float(config["alert_repeat_minutes"]))
        self.states: dict[str, _AlertState] = {}
        self.active: dict[str, AlertEvent] = {}

    def evaluate(self, snapshot: SystemSnapshot) -> list[AlertEvent]:
        now = snapshot.timestamp
        emitted: list[AlertEvent] = []
        observed: set[str] = set()
        for candidate in self._candidates(snapshot):
            observed.add(candidate.key)
            thresholds = self.thresholds[candidate.threshold_name]
            severity = self._severity(candidate.value, thresholds)
            state = self.states.setdefault(candidate.key, _AlertState())
            state.consecutive = state.consecutive + 1 if severity != "normal" else 0

            if severity == "normal":
                state.severity = "normal"
                self.active.pop(candidate.key, None)
                continue
            if state.consecutive < self.sustain_samples:
                continue

            threshold = float(thresholds[severity])
            event = AlertEvent(
                timestamp=now,
                severity=severity,
                key=candidate.key,
                label=candidate.label,
                value=candidate.value,
                threshold=threshold,
                unit=candidate.unit,
                message=(
                    f"{candidate.label} is {candidate.value:.1f}{candidate.unit}; "
                    f"{severity} starts at {threshold:.1f}{candidate.unit}"
                ),
            )
            self.active[candidate.key] = event
            should_emit = (
                severity != state.severity
                or state.last_emitted is None
                or now - state.last_emitted >= self.repeat_after
            )
            state.severity = severity
            if should_emit:
                state.last_emitted = now
                emitted.append(event)

        for key in set(self.active) - observed:
            self.active.pop(key, None)
            self.states.pop(key, None)
        return emitted

    def overall_severity(self) -> str:
        severities = {event.severity for event in self.active.values()}
        if "critical" in severities:
            return "critical"
        if "warning" in severities:
            return "warning"
        return "normal"

    @staticmethod
    def _severity(value: float, thresholds: dict[str, float]) -> str:
        if value >= float(thresholds["critical"]):
            return "critical"
        if value >= float(thresholds["warning"]):
            return "warning"
        return "normal"

    def _candidates(self, snapshot: SystemSnapshot) -> Iterable[_Candidate]:
        yield _Candidate("cpu:usage", "CPU usage", snapshot.cpu_percent, "cpu_usage_percent", "%")
        yield _Candidate(
            "memory:usage", "Memory usage", snapshot.memory_percent, "memory_usage_percent", "%"
        )
        for disk in snapshot.disks:
            yield _Candidate(
                f"disk:{disk.mountpoint}",
                f"Disk {disk.mountpoint} usage",
                disk.percent,
                "disk_usage_percent",
                "%",
            )
        for gpu in snapshot.gpus:
            if gpu.temperature_c is not None:
                yield _Candidate(
                    f"gpu:{gpu.uuid}:temperature",
                    f"GPU {gpu.index} temperature",
                    gpu.temperature_c,
                    "gpu_temperature_c",
                    "°C",
                )
        for sensor in snapshot.hardware_sensors:
            if not is_live_temperature_sensor(sensor):
                continue
            category = _temperature_category(sensor.hardware, sensor.name)
            if category is None:
                continue
            yield _Candidate(
                f"sensor:{sensor.identifier}",
                f"{sensor.hardware} / {sensor.name}",
                sensor.value,
                category,
                "°C",
            )


def _temperature_category(hardware: str, name: str) -> str | None:
    text = f"{hardware} {name}".lower()
    if any(token in text for token in ("ssd", "hdd", "nvme", "storage", "drive")):
        return "storage_temperature_c"
    if any(token in text for token in ("cpu", "package", "core", "xeon")):
        return "cpu_temperature_c"
    return None

