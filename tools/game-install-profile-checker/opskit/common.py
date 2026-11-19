"""Shared OpsKit result conventions for the standalone checker."""

from datetime import UTC, datetime
from typing import Any


class OpsKitError(Exception):
    """An expected, user-facing OpsKit failure."""

    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def make_report(
    command: str,
    data: Any,
    *,
    ok: bool = True,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "command": command,
        "ok": ok,
        "warnings": warnings or [],
        "data": data,
    }
