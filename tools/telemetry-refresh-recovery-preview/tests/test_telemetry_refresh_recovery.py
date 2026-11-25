"""Original refresh-failure assertions with invented error and snapshot records."""

from telemetry_refresh_recovery import _format_collection_error, preview_refresh_recovery


def test_collection_error_text_never_exposes_the_powershell_command() -> None:
    error = RuntimeError(
        "Command ['powershell.exe', '-Command', '$demoTasks = Get-FictionalTasks'] "
        "timed out after 20 seconds"
    )
    assert _format_collection_error(error) == "Windows health inventory timed out"


def test_refresh_error_preserves_last_good_and_schedules_retry() -> None:
    last_good = {"generated": "fictional-last-good-sample", "count": 12}
    error = RuntimeError("Command ['$demoTasks = Get-FictionalTasks'] timed out after 20 seconds")

    preview = preview_refresh_recovery(error, last_good)

    assert preview.last_snapshot is last_good
    assert preview.retry_delay_ms == 10_000
    assert "showing last sample fictional-last-good-sample" in preview.status_text
    assert "$demoTasks" not in preview.status_text
