from datetime import datetime

from sentinel_monitor.alerts import AlertEngine
from sentinel_monitor.config import DEFAULT_CONFIG
from sentinel_monitor.models import GpuReading, SystemSnapshot


def snapshot(cpu: float = 10.0, gpu_temp: float = 40.0) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=datetime.now().astimezone(),
        cpu_percent=cpu,
        per_cpu_percent=[cpu],
        cpu_frequency_mhz=2600.0,
        memory_total_bytes=100,
        memory_used_bytes=20,
        memory_available_bytes=80,
        memory_percent=20.0,
        swap_total_bytes=0,
        swap_used_bytes=0,
        swap_percent=0.0,
        disks=[],
        disk_read_bps=0.0,
        disk_write_bps=0.0,
        network_receive_bps=0.0,
        network_send_bps=0.0,
        gpus=[
            GpuReading(
                index=0,
                uuid="gpu-test",
                name="Test GPU",
                temperature_c=gpu_temp,
                utilization_percent=0.0,
                memory_utilization_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=100.0,
                power_draw_w=10.0,
                power_limit_w=100.0,
                fan_percent=None,
                pstate="P8",
                graphics_clock_mhz=100.0,
                memory_clock_mhz=200.0,
            )
        ],
        hardware_sensors=[],
        processes=[],
        uptime_seconds=100.0,
    )


def test_alert_requires_sustained_samples() -> None:
    config = dict(DEFAULT_CONFIG)
    config["alert_sustain_samples"] = 3
    engine = AlertEngine(config)
    assert engine.evaluate(snapshot(cpu=96.0)) == []
    assert engine.evaluate(snapshot(cpu=96.0)) == []
    events = engine.evaluate(snapshot(cpu=96.0))
    assert len(events) == 1
    assert events[0].severity == "critical"
    assert engine.overall_severity() == "critical"


def test_alert_clears_after_normal_sample() -> None:
    config = dict(DEFAULT_CONFIG)
    config["alert_sustain_samples"] = 1
    engine = AlertEngine(config)
    assert engine.evaluate(snapshot(gpu_temp=90.0))
    assert engine.overall_severity() == "critical"
    engine.evaluate(snapshot(gpu_temp=40.0))
    assert engine.overall_severity() == "normal"

