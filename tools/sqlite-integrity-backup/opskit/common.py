"""Shared error and reporting helpers retained from Portable OpsKit."""

import datetime as dt
from pathlib import Path


class OpsKitError(Exception):
    """An expected, user-facing OpsKit failure."""

    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def path_display(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)
