from __future__ import annotations

from types import SimpleNamespace

import sentinel_monitor.collectors.nvidia as nvidia_module
from sentinel_monitor.collectors.nvidia import NvidiaCollector


def test_collect_parses_driver_and_pci_metadata(monkeypatch) -> None:
    values = [
        "0",
        "GPU-DEMO-01",
        "Example GPU",
        "42",
        "10",
        "2",
        "100",
        "24576",
        "50.5",
        "250",
        "[N/A]",
        "P8",
        "324",
        "3304",
        "DEMO-01",
        "00000000:A1:00.0",
        "999.01",
        "TCC",
        "TCC",
    ]

    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout=", ".join(values))

    monkeypatch.setattr(nvidia_module.subprocess, "run", fake_run)
    collector = NvidiaCollector()
    collector.executable = "nvidia-smi"

    readings, status = collector.collect()

    assert len(readings) == 1
    assert readings[0].pci_bus_id == "00000000:A1:00.0"
    assert readings[0].serial == "DEMO-01"
    assert readings[0].driver_version == "999.01"
    assert readings[0].driver_model_current == "TCC"
    assert readings[0].driver_model_pending == "TCC"
    assert status == "Active: 1 NVIDIA GPU(s) | driver 999.01 | TCC"
