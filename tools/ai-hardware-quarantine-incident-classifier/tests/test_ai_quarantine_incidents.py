"""Original latch-state assertions with fictional telemetry."""

from ai_quarantine_incidents import classify_hardware_quarantine


def _snapshot(*, latched: bool) -> dict:
    return {
        "system": {
            "cpu_percent": 1,
            "memory_percent": 1,
            "disks": [],
            "errors": [],
            "hardware_events": [],
        },
        "network": {"health": [], "required_services": []},
        "gpus": [],
        "servers": [
            {
                "id": "demo-game",
                "name": "Fictional game service",
                "status": "healthy",
                "runtime_status": "online",
                "expected_state": "online",
            }
        ],
        "ai": {
            "demo_ai_service": {
                "healthy": False,
                "expected_state": "planned_off",
            },
            "thermal_guard": {"status": "armed"},
            "hardware_quarantine": {
                "latched": latched,
                "status": (
                    "Hardware degraded / AI quarantined"
                    if latched
                    else "Hardware monitoring active"
                ),
                "reasons": [
                    {
                        "kind": "corrected_hardware_burst",
                        "detail": "Three fictional corrected events in 30 minutes",
                    }
                ],
            },
        },
        "components": [],
    }


def test_latched_quarantine_is_ai_only_critical_incident() -> None:
    incidents = classify_hardware_quarantine(_snapshot(latched=True))

    quarantine = [
        incident
        for incident in incidents
        if incident.source == "safety:hardware_quarantine"
    ]
    assert len(quarantine) == 1
    assert quarantine[0].severity == "critical"
    assert "Hardware degraded / AI quarantined" in quarantine[0].summary
    assert quarantine[0].evidence["impact"] == (
        "AI compute blocked; game servers remain online"
    )
    assert not any(incident.source.startswith("server:") for incident in incidents)


def test_unlatched_quarantine_has_no_incident() -> None:
    incidents = classify_hardware_quarantine(_snapshot(latched=False))
    assert not any(
        incident.source == "safety:hardware_quarantine"
        for incident in incidents
    )
