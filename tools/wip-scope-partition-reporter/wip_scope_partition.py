"""Partition saved Kanban-assigned work-in-progress by configured lot prefixes."""

from __future__ import annotations

import argparse
import json
from math import isfinite
from pathlib import Path
import sys
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt


MAX_INPUT_BYTES = 16 * 1024 * 1024
Quantity = Annotated[StrictInt, Field(ge=0)]


class PartitionInputError(ValueError):
    """A saved assignment or exclusion prefix is invalid."""


class AssignedRow(BaseModel):
    lot_id: str = Field(min_length=1, max_length=80)
    canonical_product: str = Field(min_length=1, max_length=80)
    kanban: StrictInt = Field(ge=1, le=6)
    total_parts: Quantity
    parts_completed: Quantity

    model_config = ConfigDict(extra="allow")


class SavedAssignment(BaseModel):
    records: tuple[AssignedRow, ...]


class PartitionReport(BaseModel):
    kanban_totals: dict[int, int]
    completed_total: int
    wip_total: int
    wip_rows: tuple[AssignedRow, ...]
    wip_results_truncated: bool
    panel_flex_excluded_lot_count: int
    panel_flex_excluded_quantity: int
    selected_product: str
    selected_kanban: int | None


def report_partition(
    assignment: SavedAssignment,
    exclusion_prefixes: tuple[str, ...],
    *,
    product: str | None = None,
    kanban: int | None = None,
) -> PartitionReport:
    if not exclusion_prefixes or any(
        not prefix or prefix != prefix.strip() or len(prefix) > 80
        for prefix in exclusion_prefixes
    ):
        raise PartitionInputError("Supply nonempty lot prefixes without surrounding whitespace.")
    panel_flex_prefixes = tuple(prefix.upper() for prefix in exclusion_prefixes)
    general_wip_records = tuple(
        row
        for row in assignment.records
        if not row.lot_id.upper().startswith(panel_flex_prefixes)
    )
    panel_flex_records = tuple(
        row
        for row in assignment.records
        if row.lot_id.upper().startswith(panel_flex_prefixes)
    )
    wip_rows = [
        row
        for row in general_wip_records
        if (not product or row.canonical_product == product)
        and (not kanban or row.kanban == kanban)
    ]
    kanban_totals = {
        index: sum(row.total_parts for row in general_wip_records if row.kanban == index)
        for index in range(1, 7)
    }
    return PartitionReport(
        kanban_totals=kanban_totals,
        completed_total=sum(row.parts_completed for row in general_wip_records),
        wip_total=sum(row.total_parts for row in general_wip_records),
        wip_rows=wip_rows[:250],
        wip_results_truncated=len(wip_rows) > 250,
        panel_flex_excluded_lot_count=len(panel_flex_records),
        panel_flex_excluded_quantity=sum(row.total_parts for row in panel_flex_records),
        selected_product=product or "",
        selected_kanban=kanban,
    )


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise PartitionInputError("The assignment contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _reject_nonfinite(_value):
    raise PartitionInputError("The assignment contains a nonfinite JSON number.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _reject_nonfinite(value)
    return number


def read_assignment(path: Path) -> SavedAssignment:
    if not path.is_file():
        raise PartitionInputError("The assignment must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise PartitionInputError("The assignment is empty or exceeds its size limit.")
    payload = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_fields,
        parse_constant=_reject_nonfinite, parse_float=_finite_float,
    )
    return SavedAssignment.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("assignment", type=Path)
    parser.add_argument("--exclude-prefix", action="append", required=True, help="Lot prefix to exclude. May be repeated.")
    parser.add_argument("--product", help="Exact canonical product for the displayed rows")
    parser.add_argument("--kanban", type=int, choices=range(1, 7), help="Kanban step for the displayed rows")
    args = parser.parse_args(argv)
    try:
        result = report_partition(
            read_assignment(args.assignment), tuple(args.exclude_prefix),
            product=args.product, kanban=args.kanban,
        )
        output = result.model_dump_json(indent=2)
    except PartitionInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved assignment is unreadable or invalid.", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
