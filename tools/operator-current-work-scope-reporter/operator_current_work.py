"""Select the current-work or full-schedule view of a saved operator queue."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


MAX_INPUT_BYTES = 16 * 1024 * 1024
Scope = Literal["current", "full"]
Identifier = Annotated[str, Field(min_length=1, max_length=80)]
Quantity = Annotated[StrictInt, Field(ge=0)]


class ScopeInputError(ValueError):
    """A saved operator queue cannot be read."""


class WipReference(BaseModel):
    lot_id: Identifier

    model_config = ConfigDict(extra="allow")


class QueueRow(BaseModel):
    risk_category: Identifier
    uncovered: Quantity
    recommended_lots: Quantity
    allocations: tuple[WipReference, ...]

    model_config = ConfigDict(extra="allow")


class WorkCenterSnapshot(BaseModel):
    queue_rows: tuple[QueueRow, ...]
    wip_rows: tuple[WipReference, ...]


class ScopeReport(WorkCenterSnapshot):
    scope: Scope
    order_count: int
    allocation_count: int
    wip_count: int


def report_scope(work_center: WorkCenterSnapshot, scope: Scope = "current") -> ScopeReport:
    if scope == "full":
        operator_queue_rows = work_center.queue_rows
    else:
        operator_queue_rows = tuple(
            row
            for row in work_center.queue_rows
            if row.risk_category in {"Past due", "Next shipment"}
            or row.uncovered > 0
            or row.recommended_lots > 0
        )
    current_lot_ids = {
        allocation.lot_id
        for row in operator_queue_rows
        for allocation in row.allocations
    }
    operator_wip_rows = (
        work_center.wip_rows
        if scope == "full"
        else tuple(
            row for row in work_center.wip_rows if row.lot_id in current_lot_ids
        )
    )
    return ScopeReport(
        scope=scope,
        order_count=len(operator_queue_rows),
        allocation_count=sum(len(row.allocations) for row in operator_queue_rows),
        wip_count=len(operator_wip_rows),
        queue_rows=operator_queue_rows,
        wip_rows=operator_wip_rows,
    )


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ScopeInputError("The snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _reject_nonfinite(_value):
    raise ScopeInputError("The snapshot contains a nonfinite JSON number.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _reject_nonfinite(value)
    return number


def read_snapshot(path: Path) -> WorkCenterSnapshot:
    if not path.is_file():
        raise ScopeInputError("The snapshot must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise ScopeInputError("The snapshot is empty or exceeds its size limit.")
    payload = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_fields,
        parse_constant=_reject_nonfinite, parse_float=_finite_float,
    )
    return WorkCenterSnapshot.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--scope", choices=("current", "full"), default="current")
    args = parser.parse_args(argv)
    try:
        report = report_scope(read_snapshot(args.snapshot), scope=args.scope)
        output = report.model_dump_json(indent=2)
    except ScopeInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
