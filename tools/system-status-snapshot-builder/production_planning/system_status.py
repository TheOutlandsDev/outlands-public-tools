"""Environment, version, server-time, and ingestion-freshness presentation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo


NEW_YORK = ZoneInfo("America/New_York")


def environment_label(environment: str) -> str:
    """Return the controlled user-facing environment label."""

    normalized = environment.strip().lower()
    if normalized in {"dev", "development", "test"}:
        return "Development Environment"
    return "Production Environment"


def new_york_time(value: datetime) -> dict[str, str]:
    """Normalize one timestamp and expose ISO and New York display values."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    eastern = value.astimezone(NEW_YORK)
    return {
        "iso": eastern.isoformat(timespec="seconds"),
        "display": eastern.strftime("%b %d, %Y · %I:%M:%S %p %Z"),
        "timezone": eastern.tzname() or "ET",
    }


def build_system_status(
    *,
    app_version: str,
    app_environment: str,
    latest_ingestion_at: datetime | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the shared header/API payload without inventing freshness data."""

    current = new_york_time(now or datetime.now(UTC))
    ingestion = (
        new_york_time(latest_ingestion_at)
        if latest_ingestion_at is not None
        else None
    )
    return {
        "environment": environment_label(app_environment),
        "environment_key": app_environment.strip().lower(),
        "version": app_version,
        "server_time": current,
        "last_ingestion": ingestion,
        "last_ingestion_status": "AVAILABLE" if ingestion else "UNAVAILABLE",
        "last_ingestion_scope": "PLATFORM_REFERENCE_DATA",
    }
