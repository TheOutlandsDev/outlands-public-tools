from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True, frozen=True)
class DiskReading:
    device: str
    mountpoint: str
    label: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float


@dataclass(slots=True, frozen=True)
class GpuReading:
    index: int
    uuid: str
    name: str
    temperature_c: float | None
    utilization_percent: float | None
    memory_utilization_percent: float | None
    memory_used_mb: float | None
    memory_total_mb: float | None
    power_draw_w: float | None
    power_limit_w: float | None
    fan_percent: float | None
    pstate: str
    graphics_clock_mhz: float | None
    memory_clock_mhz: float | None
    serial: str = ""
    pci_bus_id: str = ""
    driver_version: str = ""
    driver_model_current: str = ""
    driver_model_pending: str = ""
    pcie_replays_since_reset: int | None = None

    @property
    def memory_percent(self) -> float | None:
        if self.memory_used_mb is None or not self.memory_total_mb:
            return None
        return self.memory_used_mb / self.memory_total_mb * 100.0


@dataclass(slots=True, frozen=True)
class HardwareSensor:
    identifier: str
    hardware: str
    sensor_type: str
    name: str
    value: float
    unit: str
    source: str = "LibreHardwareMonitor"


def is_live_temperature_sensor(sensor: HardwareSensor) -> bool:
    """Return False for static limits that some backends expose as temperatures."""
    if sensor.sensor_type != "Temperature":
        return False
    name = sensor.name.lower()
    static_markers = (
        "warning temperature",
        "critical temperature",
        "temperature limit",
        "temperature threshold",
        "trip point",
        "tjmax",
    )
    return not any(marker in name for marker in static_markers)


@dataclass(slots=True, frozen=True)
class ProcessReading:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int


@dataclass(slots=True, frozen=True)
class HardwareEvent:
    channel: str
    record_id: int
    timestamp: datetime
    category: str
    severity: str
    provider: str
    event_id: int
    message: str


@dataclass(slots=True)
class SystemSnapshot:
    timestamp: datetime
    cpu_percent: float
    per_cpu_percent: list[float]
    cpu_frequency_mhz: float | None
    memory_total_bytes: int
    memory_used_bytes: int
    memory_available_bytes: int
    memory_percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float
    disks: list[DiskReading]
    disk_read_bps: float
    disk_write_bps: float
    network_receive_bps: float
    network_send_bps: float
    gpus: list[GpuReading]
    hardware_sensors: list[HardwareSensor]
    processes: list[ProcessReading]
    uptime_seconds: float
    source_status: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    hardware_events: list[HardwareEvent] = field(default_factory=list)

    @property
    def highest_temperature(self) -> tuple[str, float] | None:
        temperatures: list[tuple[str, float]] = []
        for gpu in self.gpus:
            if gpu.temperature_c is not None:
                temperatures.append((f"GPU {gpu.index}", gpu.temperature_c))
        for sensor in self.hardware_sensors:
            if is_live_temperature_sensor(sensor):
                temperatures.append((f"{sensor.hardware} / {sensor.name}", sensor.value))
        return max(temperatures, key=lambda item: item[1]) if temperatures else None


@dataclass(slots=True, frozen=True)
class AlertEvent:
    timestamp: datetime
    severity: str
    key: str
    label: str
    value: float
    threshold: float
    unit: str
    message: str

