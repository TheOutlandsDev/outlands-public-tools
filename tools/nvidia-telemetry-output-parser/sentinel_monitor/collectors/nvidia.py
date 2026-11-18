from __future__ import annotations

import csv
import re
import shutil
import subprocess
import time
from io import StringIO

from ..models import GpuReading


FIELDS = (
    "index",
    "uuid",
    "name",
    "temperature.gpu",
    "utilization.gpu",
    "utilization.memory",
    "memory.used",
    "memory.total",
    "power.draw",
    "power.limit",
    "fan.speed",
    "pstate",
    "clocks.current.graphics",
    "clocks.current.memory",
    "serial",
    "pci.bus_id",
    "driver_version",
    "driver_model.current",
    "driver_model.pending",
)


def _number(value: str) -> float | None:
    cleaned = value.strip()
    if not cleaned or cleaned.upper() in {"N/A", "[N/A]", "NOT SUPPORTED"}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_bus_id(value: str) -> str:
    return value.strip().upper()


def _parse_replay_counters(output: str) -> dict[str, int]:
    counters: dict[str, int] = {}
    current_bus = ""
    for line in output.splitlines():
        bus_match = re.search(r"\bBus Id\s*:\s*(\S+)", line, re.IGNORECASE)
        if bus_match:
            current_bus = _normalize_bus_id(bus_match.group(1))
            continue
        replay_match = re.search(
            r"\bReplays Since Reset\s*:\s*(\d+)",
            line,
            re.IGNORECASE,
        )
        if replay_match and current_bus:
            counters[current_bus] = int(replay_match.group(1))
    return counters


def parse_gpu_output(
    csv_output: str, replay_output: str = ""
) -> tuple[list[GpuReading], str]:
    """Parse saved NVIDIA GPU CSV and PCIe replay text."""
    return _parse_gpu_csv(csv_output, _parse_replay_counters(replay_output))


def _parse_gpu_csv(
    csv_output: str, replay_counters: dict[str, int]
) -> tuple[list[GpuReading], str]:
    rows = csv.reader(StringIO(csv_output))
    readings: list[GpuReading] = []
    for row in rows:
        if len(row) != len(FIELDS):
            continue
        try:
            readings.append(
                GpuReading(
                    index=int(row[0].strip()),
                    uuid=row[1].strip(),
                    name=row[2].strip(),
                    temperature_c=_number(row[3]),
                    utilization_percent=_number(row[4]),
                    memory_utilization_percent=_number(row[5]),
                    memory_used_mb=_number(row[6]),
                    memory_total_mb=_number(row[7]),
                    power_draw_w=_number(row[8]),
                    power_limit_w=_number(row[9]),
                    fan_percent=_number(row[10]),
                    pstate=row[11].strip(),
                    graphics_clock_mhz=_number(row[12]),
                    memory_clock_mhz=_number(row[13]),
                    serial=row[14].strip(),
                    pci_bus_id=row[15].strip(),
                    driver_version=row[16].strip(),
                    driver_model_current=row[17].strip(),
                    driver_model_pending=row[18].strip(),
                    pcie_replays_since_reset=replay_counters.get(
                        _normalize_bus_id(row[15])
                    ),
                )
            )
        except (TypeError, ValueError):
            continue
    driver_versions = sorted(
        {reading.driver_version for reading in readings if reading.driver_version}
    )
    driver_models = sorted(
        {
            reading.driver_model_current
            for reading in readings
            if reading.driver_model_current
        }
    )
    details = [f"Active: {len(readings)} NVIDIA GPU(s)"]
    if driver_versions:
        details.append(f"driver {', '.join(driver_versions)}")
    if driver_models:
        details.append("/".join(driver_models))
    replay_details = [
        f"GPU {reading.index}={reading.pcie_replays_since_reset}"
        for reading in readings
        if reading.pcie_replays_since_reset is not None
    ]
    if replay_details:
        details.append(f"PCIe replay {' '.join(replay_details)}")
    return readings, " | ".join(details)


class NvidiaCollector:
    def __init__(self) -> None:
        self.executable = shutil.which("nvidia-smi")

        self._replay_counters: dict[str, int] = {}
        self._last_replay_poll = 0.0
        self._replay_poll_seconds = 30.0

    def collect(self) -> tuple[list[GpuReading], str]:
        if not self.executable:
            return [], "Unavailable: nvidia-smi was not found"
        command = [
            self.executable,
            f"--query-gpu={','.join(FIELDS)}",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return [], f"Unavailable: {type(exc).__name__}"

        self._poll_replay_counters()
        return _parse_gpu_csv(result.stdout, self._replay_counters)

    def _poll_replay_counters(self) -> None:
        if not self.executable:
            return
        now = time.monotonic()
        if (
            self._replay_counters
            and now - self._last_replay_poll < self._replay_poll_seconds
        ):
            return
        try:
            result = subprocess.run(
                [self.executable, "-q"],
                capture_output=True,
                text=True,
                check=True,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            self._last_replay_poll = now
            return
        counters = _parse_replay_counters(result.stdout)
        if counters:
            self._replay_counters = counters
        self._last_replay_poll = now
