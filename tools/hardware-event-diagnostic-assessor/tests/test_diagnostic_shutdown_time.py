from __future__ import annotations

from datetime import datetime

from sentinel_monitor.diagnostic_engine import DiagnosticEngine
from sentinel_monitor.models import HardwareEvent


def test_reported_shutdown_time_uses_event_6008_message() -> None:
    event = HardwareEvent(
        channel="System",
        record_id=6008,
        timestamp=datetime.fromisoformat("2040-03-12T17:20:55-04:00"),
        category="Unexpected shutdown",
        severity="critical",
        provider="EventLog",
        event_id=6008,
        message=(
            "The previous system shutdown at 5:05:30 PM on "
            "3/12/2040 was unexpected."
        ),
    )

    reported = DiagnosticEngine._reported_shutdown_time([event])

    assert reported == datetime.fromisoformat("2040-03-12T17:05:30-04:00")
