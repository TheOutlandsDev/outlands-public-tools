from __future__ import annotations

import json

from sentinel_monitor.event_payload import _parse_event_payload


def test_storage_providers_are_classified_for_guardian_gating() -> None:
    payload = json.dumps(
        [
            {
                "channel": "System",
                "record_id": 1501,
                "timestamp": "2035-01-02T22:15:00-04:00",
                "provider": "stornvme",
                "event_id": 129,
                "level": "Warning",
                "message": "Fictional storage reset.",
            },
            {
                "channel": "System",
                "record_id": 1502,
                "timestamp": "2035-01-02T22:15:01-04:00",
                "provider": "Disk",
                "event_id": 7,
                "level": "Error",
                "message": "Fictional bad block.",
            },
        ]
    )
    events = _parse_event_payload(payload)
    assert [(item.category, item.severity) for item in events] == [
        ("Storage", "warning"),
        ("Storage", "critical"),
    ]
