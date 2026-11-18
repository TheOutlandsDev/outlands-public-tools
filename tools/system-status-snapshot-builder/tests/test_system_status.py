from datetime import UTC, datetime

from production_planning.system_status import build_system_status, environment_label, new_york_time


def test_environment_labels_are_explicit() -> None:
    assert environment_label("development") == "Development Environment"
    assert environment_label("test") == "Development Environment"
    assert environment_label("production") == "Production Environment"


def test_new_york_time_observes_daylight_and_standard_time() -> None:
    summer = new_york_time(datetime(2026, 8, 13, 16, 4, 54, tzinfo=UTC))
    winter = new_york_time(datetime(2026, 1, 13, 17, 4, 54, tzinfo=UTC))

    assert summer == {
        "iso": "2026-08-13T12:04:54-04:00",
        "display": "Aug 13, 2026 · 12:04:54 PM EDT",
        "timezone": "EDT",
    }
    assert winter == {
        "iso": "2026-01-13T12:04:54-05:00",
        "display": "Jan 13, 2026 · 12:04:54 PM EST",
        "timezone": "EST",
    }


def test_status_never_invents_an_ingestion_timestamp() -> None:
    status = build_system_status(
        app_version="0.1.0-dev",
        app_environment="development",
        latest_ingestion_at=None,
        now=datetime(2026, 8, 13, 16, 10, tzinfo=UTC),
    )

    assert status["environment"] == "Development Environment"
    assert status["version"] == "0.1.0-dev"
    assert status["server_time"]["display"] == "Aug 13, 2026 · 12:10:00 PM EDT"
    assert status["last_ingestion"] is None
    assert status["last_ingestion_status"] == "UNAVAILABLE"
    assert status["last_ingestion_scope"] == "PLATFORM_REFERENCE_DATA"
