from datetime import UTC, datetime

from scheduled_maintenance import classify_maintenance


def test_recent_running_restart_controller_marks_missing_runtime_as_maintenance() -> None:
    observation = datetime(2020, 1, 2, 8, tzinfo=UTC)
    tasks = [
        {"name": "Example Daily Restart", "enabled": True, "state": "Running",
         "last_run": observation.isoformat(), "last_result": "0x00041301", "next_run": None},
    ]
    result = classify_maintenance(
        observation, "online", ["process missing: example-server", "listener missing: 27015"], tasks,
    )

    assert result["status"] == "warning"
    assert result["runtime_status"] == "maintenance"
    assert result["maintenance_in_progress"] is True
    assert result["runtime_issues"] == []
