from __future__ import annotations

import json

from sentinel_monitor.event_payload import _parse_event_payload

def test_parse_event_payload_classifies_whea_and_nvidia() -> None:
    payload = json.dumps(
        [
            {
                "channel": "System",
                "record_id": 1010,
                "timestamp": "2035-01-02T09:00:00-04:00",
                "provider": "Microsoft-Windows-WHEA-Logger",
                "event_id": 17,
                "level": "Warning",
                "message": "Fictional corrected hardware error",
            },
            {
                "channel": "System",
                "record_id": 1011,
                "timestamp": "2035-01-02T09:01:00-04:00",
                "provider": "Microsoft-Windows-WHEA-Logger",
                "event_id": 47,
                "level": "Warning",
                "message": "Fictional corrected system memory error",
            },
            {
                "channel": "System",
                "record_id": 1012,
                "timestamp": "2035-01-02T09:02:00-04:00",
                "provider": "nvlddmkm",
                "event_id": 14,
                "level": "Error",
                "message": "Fictional driver event",
            },
            {
                "channel": "System",
                "record_id": 1013,
                "timestamp": "2035-01-02T09:03:00-04:00",
                "provider": "Microsoft-Windows-WHEA-Logger",
                "event_id": 19,
                "level": "Warning",
                "message": "Fictional corrected processor interconnect error",
            },
            {
                "channel": "Application",
                "record_id": 1014,
                "timestamp": "2035-01-02T09:04:00-04:00",
                "provider": "Application Error",
                "event_id": 1000,
                "level": "Error",
                "message": "Fictional application error",
            },
        ]
    )
    events = _parse_event_payload(payload)
    assert [(event.category, event.severity) for event in events] == [
        ("WHEA PCIe", "warning"),
        ("WHEA Memory", "warning"),
        ("NVIDIA driver", "critical"),
        ("WHEA Corrected Hardware", "warning"),
        ("Application crash", "critical"),
    ]
