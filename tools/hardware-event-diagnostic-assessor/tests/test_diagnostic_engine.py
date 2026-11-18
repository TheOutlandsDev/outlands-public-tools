from __future__ import annotations

from datetime import datetime

from sentinel_monitor.diagnostic_engine import DiagnosticEngine
from sentinel_monitor.models import GpuReading, HardwareEvent, SystemSnapshot


def _gpu(replays: int) -> GpuReading:
    return GpuReading(
        index=0,
        uuid="demo-gpu-01",
        name="Demo GPU 8GB",
        temperature_c=40.0,
        utilization_percent=0.0,
        memory_utilization_percent=0.0,
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
        pcie_replays_since_reset=replays,
    )


def _snapshot(
    timestamp: datetime,
    *,
    replays: int = 0,
    events: list[HardwareEvent] | None = None,
    diagnostics_status: str = "Active: Windows System log",
) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=timestamp,
        cpu_percent=10.0,
        per_cpu_percent=[10.0],
        cpu_frequency_mhz=2500.0,
        memory_total_bytes=1000,
        memory_used_bytes=500,
        memory_available_bytes=500,
        memory_percent=50.0,
        swap_total_bytes=0,
        swap_used_bytes=0,
        swap_percent=0.0,
        disks=[],
        disk_read_bps=0.0,
        disk_write_bps=0.0,
        network_receive_bps=0.0,
        network_send_bps=0.0,
        gpus=[_gpu(replays)],
        hardware_sensors=[],
        processes=[],
        uptime_seconds=100.0,
        source_status={
            "Windows diagnostics": diagnostics_status,
            "SQLite storage": "Active: SQLite WAL",
        },
        hardware_events=events or [],
    )


def _event(
    timestamp: datetime,
    *,
    record_id: int,
    category: str,
    provider: str,
    event_id: int,
) -> HardwareEvent:
    return HardwareEvent(
        channel="System",
        record_id=record_id,
        timestamp=timestamp,
        category=category,
        severity="critical",
        provider=provider,
        event_id=event_id,
        message="Diagnostic evidence",
    )


def test_historical_restart_auto_clears_after_verified_samples() -> None:
    session_start = datetime.fromisoformat("2040-03-13T09:30:00-04:00")
    event_time = datetime.fromisoformat("2040-03-12T17:20:45-04:00")
    sample_time = datetime.fromisoformat("2040-03-13T09:30:30-04:00")
    engine = DiagnosticEngine(auto_clear_samples=2, session_started=session_start)
    event = _event(
        event_time,
        record_id=41,
        category="Unexpected restart",
        provider="Microsoft-Windows-Kernel-Power",
        event_id=41,
    )

    first = engine.evaluate(_snapshot(sample_time, events=[event]))
    assert first.status == "monitoring"
    assert first.severity == "warning"
    assert "Historical unexpected restart" in first.title

    second = engine.evaluate(_snapshot(sample_time))
    assert second.status == "resolved"
    assert second.severity == "normal"
    assert second.auto_cleared is True
    assert "current checks clean" in second.title


def test_new_whea_event_stays_visible_until_recovery_is_verified() -> None:
    session_start = datetime.fromisoformat("2040-03-13T09:30:00-04:00")
    sample_time = datetime.fromisoformat("2040-03-13T09:31:00-04:00")
    engine = DiagnosticEngine(auto_clear_samples=2, session_started=session_start)
    event = _event(
        sample_time,
        record_id=17,
        category="WHEA PCIe",
        provider="Microsoft-Windows-WHEA-Logger",
        event_id=17,
    )

    active = engine.evaluate(_snapshot(sample_time, events=[event]))
    assert active.status == "active"
    assert active.severity == "critical"
    assert active.confidence == "High"

    checking = engine.evaluate(_snapshot(sample_time))
    assert checking.status == "monitoring"
    assert "1/2" in checking.verification

    resolved = engine.evaluate(_snapshot(sample_time))
    assert resolved.status == "resolved"
    assert resolved.auto_cleared is True


def test_replay_increase_is_a_high_confidence_active_fault() -> None:
    start = datetime.fromisoformat("2040-03-13T09:30:00-04:00")
    engine = DiagnosticEngine(auto_clear_samples=2, session_started=start)
    engine.evaluate(_snapshot(start, replays=0))

    assessment = engine.evaluate(_snapshot(start, replays=1))

    assert assessment.status == "active"
    assert assessment.severity == "critical"
    assert assessment.confidence == "High"
    assert "0 -> 1" in assessment.evidence[0]


def test_collector_error_retries_and_can_be_acknowledged() -> None:
    start = datetime.fromisoformat("2040-03-13T09:30:00-04:00")
    engine = DiagnosticEngine(auto_clear_samples=2, session_started=start)

    failed = engine.evaluate(
        _snapshot(start, diagnostics_status="Read error: TimeoutExpired")
    )
    assert failed.severity == "warning"
    assert failed.automatic_action_taken is True
    assert "retrying" in failed.recommended_action.lower()

    acknowledged = engine.acknowledge()
    assert acknowledged.status == "acknowledged"
    assert acknowledged.severity == "normal"
