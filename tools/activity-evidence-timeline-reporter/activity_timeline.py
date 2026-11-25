"""Report a paginated activity timeline from already-saved evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


MAX_INPUT_BYTES = 16 * 1024 * 1024
ActivityScope = Literal["operational", "developer"]
ActivityDomain = Literal[
    "os",
    "production",
    "lot_starts",
    "panel_flex",
    "logistics",
    "accounts",
    "system",
]
ACTIVITY_DOMAIN_CATALOG = {'os': 'Living O&S',
 'production': 'Production',
 'lot_starts': 'Lot Starts',
 'panel_flex': 'Panel Flex',
 'logistics': 'Logistics',
 'accounts': 'Accounts',
 'system': 'System'}
OPERATIONAL_ACTIVITY_DOMAINS = tuple(ACTIVITY_DOMAIN_CATALOG)[:5]
DEVELOPER_ACTIVITY_DOMAINS = tuple(ACTIVITY_DOMAIN_CATALOG)


class ActivityEvent(BaseModel):
    """One normalized event from an existing append-only evidence table."""

    event_id: str
    domain: ActivityDomain
    occurred_at: AwareDatetime
    actor: str
    action: str
    subject_type: str
    subject_id: str
    result: str
    correlation_id: str
    detail: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ActivityPage(BaseModel):
    """Bounded timeline response with counts from the same filtered evidence."""

    scope: ActivityScope
    read_only: Literal[True] = True
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    page_count: int = Field(ge=1)
    domain_counts: dict[str, int]
    events: tuple[ActivityEvent, ...]

    model_config = ConfigDict(frozen=True, extra="forbid")


class ActivitySnapshot(BaseModel):
    events: tuple[ActivityEvent, ...]


def report_timeline(
    snapshot: ActivitySnapshot,
    *,
    scope: ActivityScope = "operational",
    domain: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> ActivityPage:
    if scope not in {"operational", "developer"}:
        raise ValueError("Unknown activity scope.")
    visible_domains = (
        DEVELOPER_ACTIVITY_DOMAINS
        if scope == "developer"
        else OPERATIONAL_ACTIVITY_DOMAINS
    )
    if domain is not None and domain not in visible_domains:
        raise ValueError("Unknown activity domain for this account.")
    if page < 1 or not 1 <= page_size <= 100:
        raise ValueError("Activity paging is outside the supported range.")

    matched = sorted(
        (event for event in snapshot.events
         if event.domain in visible_domains and (domain is None or event.domain == domain)),
        key=lambda event: (event.occurred_at, event.event_id),
        reverse=True,
    )
    counts = Counter(event.domain for event in matched)
    total = sum(counts.values())
    start = (page - 1) * page_size
    return ActivityPage(
        scope=scope,
        total=total,
        page=page,
        page_size=page_size,
        page_count=max(1, (total + page_size - 1) // page_size),
        domain_counts={value: counts.get(value, 0) for value in visible_domains},
        events=tuple(matched[start:start + page_size]),
    )


class TimelineInputError(ValueError):
    """The saved event snapshot cannot be read."""


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise TimelineInputError("The snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _nonfinite(_value):
    raise TimelineInputError("The snapshot contains a nonfinite JSON number.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _nonfinite(value)
    return number


def read_snapshot(path: Path) -> ActivitySnapshot:
    if not path.is_file():
        raise TimelineInputError("The snapshot must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise TimelineInputError("The snapshot is empty or exceeds its size limit.")
    return ActivitySnapshot.model_validate(json.loads(
        raw.decode("utf-8"), object_pairs_hook=_unique_fields,
        parse_constant=_nonfinite, parse_float=_finite_float,
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--scope", choices=("operational", "developer"), default="operational")
    parser.add_argument("--domain")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=50)
    args = parser.parse_args(argv)
    try:
        snapshot = read_snapshot(args.snapshot)
    except TimelineInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    try:
        output = report_timeline(
            snapshot, scope=args.scope, domain=args.domain or None,
            page=args.page, page_size=args.page_size,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    try:
        print(output.model_dump_json(indent=2))
    except (ValueError, RecursionError):
        print("ERROR: The snapshot cannot be serialized.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
