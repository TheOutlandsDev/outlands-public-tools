from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime

from sentinel_monitor.models import (
    AlertEvent,
    DiskReading,
    GpuReading,
    HardwareEvent,
    HardwareSensor,
    ProcessReading,
    SystemSnapshot,
)
from sentinel_monitor.storage import SqliteStore


def _snapshot(timestamp: datetime) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=timestamp,
        cpu_percent=25.0,
        per_cpu_percent=[20.0, 30.0],
        cpu_frequency_mhz=2800.0,
        memory_total_bytes=1024,
        memory_used_bytes=512,
        memory_available_bytes=512,
        memory_percent=50.0,
        swap_total_bytes=0,
        swap_used_bytes=0,
        swap_percent=0.0,
        disks=[
            DiskReading(
                device="demo-disk",
                mountpoint="/virtual/demo",
                label="System",
                total_bytes=1000,
                used_bytes=400,
                free_bytes=600,
                percent=40.0,
            )
        ],
        disk_read_bps=100.0,
        disk_write_bps=200.0,
        network_receive_bps=300.0,
        network_send_bps=400.0,
        gpus=[
            GpuReading(
                index=0,
                uuid="demo-gpu-01",
                name="Demo GPU 8GB",
                temperature_c=42.0,
                utilization_percent=5.0,
                memory_utilization_percent=1.0,
                memory_used_mb=9.0,
                memory_total_mb=8192.0,
                power_draw_w=23.0,
                power_limit_w=140.0,
                fan_percent=None,
                pstate="P5",
                graphics_clock_mhz=500.0,
                memory_clock_mhz=2500.0,
                pci_bus_id="00000000:2A:00.0",
                driver_version="900.00",
                driver_model_current="WDDM",
                pcie_replays_since_reset=0,
            )
        ],
        hardware_sensors=[
            HardwareSensor(
                identifier="/virtual/demo/temp/0",
                hardware="SSD",
                sensor_type="Temperature",
                name="Composite",
                value=40.0,
                unit="°C",
            )
        ],
        processes=[
            ProcessReading(
                pid=42,
                name="demo-worker",
                cpu_percent=2.0,
                memory_percent=1.0,
                memory_bytes=100,
            )
        ],
        uptime_seconds=600.0,
        hardware_events=[
            HardwareEvent(
                channel="System",
                record_id=123,
                timestamp=timestamp,
                category="WHEA PCIe",
                severity="warning",
                provider="Microsoft-Windows-WHEA-Logger",
                event_id=17,
                message="Corrected hardware error",
            )
        ],
    )


def test_sqlite_store_persists_one_transaction_and_clean_session(tmp_path) -> None:
    path = tmp_path / "sentinel.db"
    boot_time = datetime.fromisoformat("2040-03-13T09:00:00-04:00")
    timestamp = datetime.fromisoformat("2040-03-13T10:00:00-04:00")
    store = SqliteStore(path, retention_days=30)
    diagnostic = store.start_session(boot_time)
    assert diagnostic.previous_unclean is False

    alert = AlertEvent(
        timestamp=timestamp,
        severity="warning",
        key="gpu:0:temperature",
        label="GPU 0",
        value=82.0,
        threshold=80.0,
        unit="°C",
        message="GPU temperature warning",
    )
    store.log_snapshot(_snapshot(timestamp), [alert])
    store.close(clean_exit=True)

    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert connection.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM gpu_metrics").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM hardware_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
        assert connection.execute(
            "SELECT clean_exit FROM sessions"
        ).fetchone()[0] == 1


def test_sqlite_store_detects_previous_unclean_session(tmp_path) -> None:
    path = tmp_path / "sentinel.db"
    boot_time = datetime.fromisoformat("2040-03-13T09:00:00-04:00")
    first = SqliteStore(path)
    first.start_session(boot_time)
    first.close(clean_exit=False)

    second = SqliteStore(path)
    diagnostic = second.start_session(boot_time)
    assert diagnostic.previous_unclean is True
    assert "application interruption" in diagnostic.message
    second.close(clean_exit=True)
