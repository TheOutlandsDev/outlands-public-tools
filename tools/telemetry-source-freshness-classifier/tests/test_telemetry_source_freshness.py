"""Original stale-source warning assertions with a fictional snapshot."""

from telemetry_source_freshness import classify_source_freshness


def test_stale_source_is_a_bounded_warning() -> None:
    snapshot = {
        "source_health": {
            "demo_inventory": {
                "state": "stale",
                "collected_at": "2030-01-12T18:00:00+00:00",
                "age_seconds": 75.0,
                "used_fallback": True,
                "error": "Fictional inventory read failed",
            }
        },
        "system": {
            "cpu_percent": 10,
            "memory_percent": 20,
            "disks": [],
            "errors": [],
            "hardware_events": [],
        },
        "gpus": [],
        "servers": [],
        "network": {"health": [], "services": [], "warnings": []},
        "ai": {
            "demo_ai_service": {"healthy": False, "expected_state": "planned_off"},
            "thermal_guard": {},
        },
        "components": [],
    }
    incident = next(
        item
        for item in classify_source_freshness(snapshot)
        if item.source == "collector:demo_inventory"
    )
    assert incident.code == "freshness"
    assert incident.severity == "warning"
    assert "last valid value is cached" in incident.summary
    assert "unrelated collectors remain current" in incident.evidence["impact"]
