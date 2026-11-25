"""Original thermal assertions with fictional CPU and GPU readings."""

from thermal_incidents import classify_thermal_incidents


def test_live_cpu_temperature_uses_cpu_thresholds() -> None:
    snapshot = {
        "system": {
            "cpu_percent": 10,
            "memory_percent": 20,
            "disks": [],
            "errors": [],
            "hardware_events": [],
            "hardware_sensors": [
                {
                    "identifier": "demo-cpu-package",
                    "hardware": "Fictional CPU",
                    "sensor_type": "Temperature",
                    "name": "CPU Package",
                    "value": 86,
                    "source": "Fictional sensor bridge",
                },
                {
                    "identifier": "demo-cpu-static-limit",
                    "hardware": "Fictional CPU",
                    "sensor_type": "Temperature",
                    "name": "CPU Core #1 Distance to TjMax",
                    "value": 7,
                    "source": "Fictional sensor bridge",
                },
            ],
        },
        "gpus": [],
        "servers": [],
        "ai": {"demo_ai_service": {"healthy": True}, "thermal_guard": {}},
        "components": [],
    }
    incidents = classify_thermal_incidents(
        snapshot,
        {"cpu_warning_c": 75, "cpu_critical_c": 85},
    )
    temperature_incidents = [
        item for item in incidents if item.code == "temperature"
    ]
    assert len(temperature_incidents) == 1
    assert temperature_incidents[0].severity == "critical"


def test_hot_gpu_is_reported() -> None:
    """Retain the thermal assertion from the original GPU and server test."""
    snapshot = {
        "gpus": [
            {
                "index": 0,
                "uuid": "demo-hot-gpu",
                "temperature_c": 89,
                "pcie_replays_since_reset": 0,
            }
        ]
    }
    incidents = classify_thermal_incidents(
        snapshot,
        {"gpu_warning_c": 75, "gpu_critical_c": 88},
    )
    assert any(item.code == "temperature" and item.severity == "critical" for item in incidents)
