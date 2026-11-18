from datetime import datetime, timezone
import json

import pytest

from sentinel_monitor.event_payload import parse_event_payload
from sentinel_monitor.models import HardwareEvent


def test_parse_event_payload_skips_invalid_rows_in_input_order() -> None:
    fields = {
        "provider": "Fictional Sensor",
        "event_id": 1,
        "timestamp": "2035-01-02T12:00:00+00:00",
    }
    payload = json.dumps(
        [
            dict(fields, record_id=9),
            None,
            "invalid row",
            dict(fields),
            dict(fields, record_id="invalid integer"),
            dict(fields, record_id=4, timestamp="invalid timestamp"),
            dict(fields, record_id="overflow-number"),
            dict(fields, record_id=3, event_id="overflow-number"),
            dict(fields, record_id=2),
        ]
    ).replace('"overflow-number"', "1e400")

    events = parse_event_payload(payload)

    assert [event.record_id for event in events] == [9, 2]


def test_parse_event_payload_accepts_bom_and_cleans_single_record() -> None:
    payload = "\ufeff" + json.dumps(
        {
            "channel": None,
            "record_id": "12",
            "timestamp": "2035-01-02T12:00:00+00:00",
            "provider": "Display",
            "event_id": "4101",
            "level": " wArNiNg ",
            "message": "\u2066Fictional\u2069\t display \n  reset",
        }
    )

    assert parse_event_payload(payload) == [
        HardwareEvent(
            channel="System",
            record_id=12,
            timestamp=datetime(2035, 1, 2, 12, 0, tzinfo=timezone.utc),
            category="Display reset",
            severity="warning",
            provider="Display",
            event_id=4101,
            message="Fictional display reset",
        )
    ]


def test_parse_event_payload_distinguishes_empty_from_invalid_json() -> None:
    assert parse_event_payload("\ufeff\n   ") == []
    assert parse_event_payload("[]") == []

    with pytest.raises(json.JSONDecodeError):
        parse_event_payload("[")
