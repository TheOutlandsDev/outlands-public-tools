from datetime import datetime

from sentinel_monitor.alerts import AlertEngine
from sentinel_monitor.config import DEFAULT_CONFIG
from sentinel_monitor.models import HardwareSensor, SystemSnapshot


def test_static_temperature_limits_are_not_live_readings() -> None:
    sensors = [
        HardwareSensor(
            identifier="/ssd/0/temp/0",
            hardware="Test SSD",
            sensor_type="Temperature",
            name="Composite Temperature",
            value=42.0,
            unit="°C",
        ),
        HardwareSensor(
            identifier="/ssd/0/temp/5",
            hardware="Test SSD",
            sensor_type="Temperature",
            name="Warning Temperature",
            value=84.0,
            unit="°C",
        ),
        HardwareSensor(
            identifier="/ssd/0/temp/6",
            hardware="Test SSD",
            sensor_type="Temperature",
            name="Critical Temperature",
            value=84.0,
            unit="°C",
        ),
    ]
    snapshot = SystemSnapshot(
        timestamp=datetime.now().astimezone(),
        cpu_percent=10.0,
        per_cpu_percent=[10.0],
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
        gpus=[],
        hardware_sensors=sensors,
        processes=[],
        uptime_seconds=100.0,
    )
    config = dict(DEFAULT_CONFIG)
    config["alert_sustain_samples"] = 1
    engine = AlertEngine(config)

    assert snapshot.highest_temperature == ("Test SSD / Composite Temperature", 42.0)
    assert engine.evaluate(snapshot) == []
