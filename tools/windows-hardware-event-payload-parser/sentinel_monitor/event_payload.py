"""Parse saved Windows hardware event JSON."""
from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from typing import Any

from .models import HardwareEvent

def _category(provider: str, event_id: int) -> str:
    provider_lower = provider.lower()
    if any(
        token in provider_lower
        for token in ("disk", "storport", "stornvme", "ntfs", "volmgr", "volsnap")
    ):
        return "Storage"
    if provider == "Microsoft-Windows-WHEA-Logger":
        if event_id == 17:
            return "WHEA PCIe"
        if event_id == 47:
            return "WHEA Memory"
        return "WHEA Corrected Hardware"
    if "nvidia" in provider_lower or "nvlddmkm" in provider_lower:
        return "NVIDIA driver"
    if provider == "Display" and event_id == 4101:
        return "Display reset"
    if provider == "Microsoft-Windows-Kernel-Power" and event_id == 41:
        return "Unexpected restart"
    if provider == "EventLog" and event_id == 6008:
        return "Unexpected shutdown"
    if provider == "Microsoft-Windows-WER-SystemErrorReporting" and event_id == 1001:
        return "Bugcheck"
    if provider in {
        "Application Error",
        "Application Hang",
        ".NET Runtime",
        "Windows Error Reporting",
    }:
        return "Application crash"
    return "System hardware"


def _severity(level: str) -> str:
    normalized = level.strip().lower()
    if normalized in {"critical", "error"}:
        return "critical"
    if normalized == "warning":
        return "warning"
    return "info"


def _clean_message(value: object) -> str:
    text = "".join(
        character
        for character in str(value or "")
        if unicodedata.category(character) != "Cf"
    )
    return " ".join(text.split())


def _parse_event_payload(payload: str) -> list[HardwareEvent]:
    cleaned = payload.lstrip("\ufeff").strip()
    if not cleaned:
        return []
    parsed: Any = json.loads(cleaned)
    items = parsed if isinstance(parsed, list) else [parsed]
    events: list[HardwareEvent] = []
    for item in items:
        try:
            provider = str(item["provider"])
            event_id = int(item["event_id"])
            events.append(
                HardwareEvent(
                    channel=str(item.get("channel") or "System"),
                    record_id=int(item["record_id"]),
                    timestamp=datetime.fromisoformat(str(item["timestamp"])),
                    category=_category(provider, event_id),
                    severity=_severity(str(item.get("level") or "Information")),
                    provider=provider,
                    event_id=event_id,
                    message=_clean_message(item.get("message")),
                )
            )
        except (KeyError, OverflowError, TypeError, ValueError):
            continue
    return events


parse_event_payload = _parse_event_payload
