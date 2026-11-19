"""Shared result conventions for the incident bundle CLI."""

from datetime import UTC, datetime
from typing import Any


SCHEMA_VERSION = "1"


class OpsKitError(Exception):
    """An expected, user-facing OpsKit failure."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def make_report(command: str, data: Any, *, warnings: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "command": command,
        "ok": True,
        "warnings": warnings,
        "data": data,
    }
