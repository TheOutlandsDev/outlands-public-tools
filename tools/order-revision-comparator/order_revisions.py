"""Report additions, removals and changed fields between saved order snapshots."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PTLAOrderRecord(BaseModel):
    """One saved customer or panel order."""

    source_sheet: Literal["C", "P"]
    source_row: int = Field(ge=4, le=500)
    order_date: date | None = None
    part_number: str = Field(min_length=1, max_length=40)
    customer_or_oracle_po: str | None = Field(default=None, max_length=80)
    po_line: str | None = Field(default=None, max_length=30)
    quantity: int = Field(gt=0)
    ngb_etd_or_oracle_rsd: date | None = None
    organization: str | None = Field(default=None, max_length=20)
    flex_ptl_commit_date: date
    ship_quantity: int | None = Field(default=None, ge=0)
    ship_date: date | None = None
    shipment_number: str | None = Field(default=None, max_length=80)
    checked_by: str | None = Field(default=None, max_length=40)
    dock_date: date | None = None
    lot_ids: str | None = Field(default=None, max_length=2000)
    lot_quantities: str | None = Field(default=None, max_length=2000)
    work_request_flow: str | None = Field(default=None, max_length=256)
    carrier: str | None = Field(default=None, max_length=80)
    tracking_number: str | None = Field(default=None, max_length=120)
    customer_notes: str | None = Field(default=None, max_length=4000)
    ptl_notes: str | None = Field(default=None, max_length=4000)
    lead_time_calculation: date | str | None = None
    admin_1_open: str | None = Field(default=None, max_length=40)
    admin_2_used: str | None = Field(default=None, max_length=40)
    admin_3_used: str | None = Field(default=None, max_length=40)

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrderChange(BaseModel):
    key: str
    changed_fields: tuple[str, ...] = ()
    model_config = ConfigDict(frozen=True)


class RevisionComparison(BaseModel):
    added_count: int = Field(ge=0)
    removed_count: int = Field(ge=0)
    changed_count: int = Field(ge=0)
    added: tuple[OrderChange, ...]
    removed: tuple[OrderChange, ...]
    changed: tuple[OrderChange, ...]
    truncated: bool
    model_config = ConfigDict(frozen=True)


class OrderIdentityError(ValueError):
    """The saved snapshot has an ambiguous order identity."""


def _order_key(order: PTLAOrderRecord) -> str:
    values = (
        order.source_sheet,
        order.part_number,
        order.customer_or_oracle_po or "",
        order.po_line or "",
        order.flex_ptl_commit_date.isoformat(),
    )
    if any("|" in value for value in values):
        raise OrderIdentityError("Order identity fields may not contain a pipe")
    return "|".join(values)


def _order_map(orders: tuple[PTLAOrderRecord, ...]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for order in orders:
        key = _order_key(order)
        if key in mapped:
            raise OrderIdentityError("Duplicate order identity in a snapshot")
        mapped[key] = order.model_dump(mode="json", exclude={"source_row"})
    return mapped


def compare_orders(
    active: tuple[PTLAOrderRecord, ...],
    candidate: tuple[PTLAOrderRecord, ...],
    *,
    limit: int = 100,
) -> RevisionComparison:
    left = _order_map(active)
    right = _order_map(candidate)
    added_keys = sorted(right.keys() - left.keys())
    removed_keys = sorted(left.keys() - right.keys())
    changed: list[OrderChange] = []
    for key in sorted(left.keys() & right.keys()):
        fields = tuple(sorted(field for field in left[key] if left[key][field] != right[key][field]))
        if fields:
            changed.append(OrderChange(key=key, changed_fields=fields))
    total = len(added_keys) + len(removed_keys) + len(changed)
    return RevisionComparison(
        added_count=len(added_keys),
        removed_count=len(removed_keys),
        changed_count=len(changed),
        added=tuple(OrderChange(key=key) for key in added_keys[:limit]),
        removed=tuple(OrderChange(key=key) for key in removed_keys[:limit]),
        changed=tuple(changed[:limit]),
        truncated=total > limit,
    )


class SavedSnapshot(BaseModel):
    orders: tuple[PTLAOrderRecord, ...] = Field(max_length=1000)

    model_config = ConfigDict(extra="forbid")


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
    parser.add_argument("active", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--limit", type=int, default=100, help="Maximum details per category, from 0 to 1000")
    args = parser.parse_args()
    if not 0 <= args.limit <= 1000:
        parser.error("--limit must be between 0 and 1000")
    try:
        active = SavedSnapshot.model_validate(_read_json(args.active))
        candidate = SavedSnapshot.model_validate(_read_json(args.candidate))
        report = compare_orders(active.orders, candidate.orders, limit=args.limit)
    except OrderIdentityError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValueError:
        print("Invalid or unreadable order snapshot", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((report.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
