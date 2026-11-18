"""Data model for a normalized hardware event."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

@dataclass(slots=True, frozen=True)
class HardwareEvent:
    channel: str
    record_id: int
    timestamp: datetime
    category: str
    severity: str
    provider: str
    event_id: int
    message: str
