"""Verify saved review events for one order revision and report its latest decision."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class RevisionReviewEvent(BaseModel):
    event_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: str = Field(
        pattern=r"^(AWAITING_REVIEW|ACCEPTED_FOR_ACTIVATION|REJECTED)$"
    )
    reviewer: str = Field(min_length=1, max_length=120)
    comment: str = Field(min_length=3, max_length=500)
    reviewed_at: AwareDatetime
    model_config = ConfigDict(frozen=True, extra="forbid")


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _review_event_id(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: value.isoformat().replace("+00:00", "Z")
        if isinstance(value, datetime)
        else str(value),
    ).encode("utf-8")
    return _digest(canonical)


class SavedReviewLedger(BaseModel):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    events: tuple[RevisionReviewEvent, ...] = Field(max_length=1000)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ReviewLedgerIntegrityError(ValueError):
    """An event does not match its revision or canonical digest."""


class ReviewLedgerReport(BaseModel):
    revision_sha256: str
    verified_event_count: int
    latest_decision: str
    events: tuple[RevisionReviewEvent, ...]

    model_config = ConfigDict(frozen=True)


def verify_review_history(ledger: SavedReviewLedger, *, limit: int = 20) -> ReviewLedgerReport:
    if not 1 <= limit <= 100:
        raise ValueError("Review history limit must be between 1 and 100.")

    for event in ledger.events:
        payload = event.model_dump(mode="json", exclude={"event_id"})
        if event.revision_sha256 != ledger.revision_sha256 or _review_event_id(payload) != event.event_id:
            raise ReviewLedgerIntegrityError("The order review ledger failed integrity validation.")

    events = tuple(
        sorted(ledger.events, key=lambda event: (event.reviewed_at, event.event_id), reverse=True)[:limit]
    )
    return ReviewLedgerReport(
        revision_sha256=ledger.revision_sha256,
        verified_event_count=len(ledger.events),
        latest_decision=events[0].decision if events else "AWAITING_REVIEW",
        events=events,
    )


_MAX_FILE_BYTES = 1024 * 1024


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(_value: str) -> object:
    raise ValueError("Saved input contains an invalid JSON number.")


def _read_json(path: Path) -> object:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise ValueError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_FILE_BYTES:
            raise ValueError("Saved input exceeds the 1 MiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise ValueError("Saved input changed while opening.")
            content = stream.read(_MAX_FILE_BYTES + 1)
    except ValueError:
        raise
    except (OSError, ValueError):
        raise ValueError("Unable to read the saved input.") from None
    if len(content) > _MAX_FILE_BYTES:
        raise ValueError("Saved input exceeds the 1 MiB limit.")

    try:
        return json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
        )
    except ValueError:
        raise
    except (ArithmeticError, ValueError, RecursionError):
        raise ValueError("Saved input must contain valid UTF-8 JSON.") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local UTF-8 JSON containing revision_sha256 and events")
    parser.add_argument("--limit", type=int, default=20, help="Maximum events to display, from 1 to 100")
    args = parser.parse_args()
    try:
        ledger = SavedReviewLedger.model_validate(_read_json(args.input))
        report = verify_review_history(ledger, limit=args.limit)
    except ReviewLedgerIntegrityError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValueError:
        print("Invalid or unreadable review ledger input", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((report.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
