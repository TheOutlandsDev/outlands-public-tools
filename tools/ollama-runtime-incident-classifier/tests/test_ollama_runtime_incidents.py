"""Original Ollama assertion from the mixed planned-off test."""

from ollama_runtime_incidents import classify_ollama_runtime


def test_planned_off_ollama_is_not_an_incident() -> None:
    snapshot = {
        "system": {
            "cpu_percent": 10,
            "memory_percent": 20,
            "disks": [],
            "errors": [],
            "hardware_events": [],
        },
        "gpus": [],
        "servers": [
            {
                "id": "demo",
                "name": "Demo Server",
                "status": "planned_off",
                "runtime_status": "planned_off",
                "observed_runtime_status": "down",
                "expected_state": "planned_off",
                "automation_issues": [],
                "issues": [],
            }
        ],
        "network": {
            "health": [],
            "services": [
                {
                    "id": "demo-public",
                    "server_id": "demo",
                    "name": "Demo public service",
                    "planned_off": True,
                    "optional": False,
                    "listener": "planned_off",
                    "firewall": "allowed",
                    "external": "unverified",
                }
            ],
            "warnings": [],
        },
        "ai": {
            "ollama": {
                "healthy": False,
                "expected_state": "planned_off",
                "operational_state": "planned_off",
            },
            "thermal_guard": {},
        },
        "components": [],
    }
    incidents = classify_ollama_runtime(snapshot)
    assert not any(item.source == "ai:ollama" for item in incidents)
