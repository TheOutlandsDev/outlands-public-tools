from __future__ import annotations

from dataclasses import dataclass


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
