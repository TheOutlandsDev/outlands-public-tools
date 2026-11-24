"""Filter saved operator work-center orders, actions, and WIP rows."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_INPUT_BYTES = 16 * 1024 * 1024


class OperatorWorkCenterError(ValueError):
    """Raised when the snapshot-driven work-center contract cannot be proven."""


class OperatorOrderRow(BaseModel):
    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    due_date: date
    demand: int = Field(gt=0)
    covered: int = Field(ge=0)
    uncovered: int = Field(ge=0)
    recommended_start: int = Field(ge=0)
    recommended_lots: int = Field(ge=0)
    allocation_count: int = Field(ge=0, le=100)
    order_line_count: int = Field(default=1, ge=1, le=100)
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True)


class OperatorActionRow(BaseModel):
    action_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    lot_id: str = Field(min_length=1, max_length=80)
    due_date: date
    kanban: int = Field(ge=1, le=6)
    operation: str = Field(min_length=1, max_length=256)
    allocated_quantity: int = Field(gt=0)
    days_remaining: int = Field(ge=0)
    days_until_due: int
    schedule_delta: int
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True)


class OperatorQueueRow(BaseModel):
    """One order-level decision row with its complete lot-allocation trace."""

    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    order_id: str = Field(min_length=1, max_length=80)
    due_date: date
    demand: int = Field(gt=0)
    covered: int = Field(ge=0)
    uncovered: int = Field(ge=0)
    recommended_start: int = Field(ge=0)
    recommended_lots: int = Field(ge=0)
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)
    allocations: tuple[OperatorActionRow, ...] = Field(max_length=100)
    allocation_count: int = Field(ge=0, le=100)
    allocated_quantity: int = Field(ge=0)
    order_line_count: int = Field(default=1, ge=1, le=100)

    model_config = ConfigDict(frozen=True)


class OperatorWipRow(BaseModel):
    lot_id: str = Field(min_length=1, max_length=80)
    product: str = Field(min_length=1, max_length=80)
    operation: str = Field(min_length=1, max_length=256)
    kanban: int = Field(ge=1, le=6)
    in_process: int = Field(ge=0)
    completed: int = Field(ge=0)
    total: int = Field(ge=0)
    yield_percent: float = Field(ge=0, allow_inf_nan=False)

    model_config = ConfigDict(frozen=True)


class WorkCenterSnapshot(BaseModel):
    orders: tuple[OperatorOrderRow, ...]
    actions: tuple[OperatorActionRow, ...]
    wip_rows: tuple[OperatorWipRow, ...]

    @model_validator(mode="after")
    def validate_identity_links(self):
        order_keys = {(row.part_number, row.order_id) for row in self.orders}
        if len(order_keys) != len(self.orders):
            raise ValueError("The saved report contains duplicate order identities.")
        if len({row.action_id for row in self.actions}) != len(self.actions):
            raise ValueError("The saved report contains duplicate action IDs.")
        if any((row.part_number, row.order_id) not in order_keys for row in self.actions):
            raise ValueError("An action refers to an order missing from the saved report.")
        return self


class FilteredWorkCenter(BaseModel):
    orders: tuple[OperatorOrderRow, ...]
    actions: tuple[OperatorActionRow, ...]
    queue_rows: tuple[OperatorQueueRow, ...]
    wip_rows: tuple[OperatorWipRow, ...]


def filter_work_center(
    snapshot: WorkCenterSnapshot,
    *,
    product: str | None = None,
    kanban: int | None = None,
    risk: str | None = None,
) -> FilteredWorkCenter:
    order_rows = snapshot.orders
    action_rows = snapshot.actions
    actions_by_order = {(row.part_number, row.order_id): [] for row in order_rows}
    for row in action_rows:
        actions_by_order[(row.part_number, row.order_id)].append(row)

    available_risks = tuple(
        sorted(
            {row.risk_category for row in order_rows}
            | {row.risk_category for row in action_rows}
        )
    )
    if risk and risk not in available_risks:
        raise OperatorWorkCenterError("selected risk is not available")
    filtered_orders = tuple(
        row
        for row in order_rows
        if (not product or row.part_number == product)
        and (not risk or row.risk_category == risk)
    )
    filtered_actions = tuple(
        row
        for row in action_rows
        if (not product or row.part_number == product)
        and (not kanban or row.kanban == kanban)
        and (not risk or row.risk_category == risk)
    )
    filtered_action_ids = {row.action_id for row in filtered_actions}
    queue_rows = []
    for order in filtered_orders:
        allocations = tuple(
            row
            for row in actions_by_order[(order.part_number, order.order_id)]
            if row.action_id in filtered_action_ids
        )
        if kanban is not None and not allocations:
            continue
        queue_rows.append(
            OperatorQueueRow(
                **order.model_dump(mode="python"),
                allocations=allocations,
                allocated_quantity=sum(
                    row.allocated_quantity for row in allocations
                ),
            )
        )

    visible_wip_rows = tuple(
        row
        for row in snapshot.wip_rows
        if (not product or row.product == product)
        and (not kanban or row.kanban == kanban)
    )
    return FilteredWorkCenter(
        orders=tuple(sorted(filtered_orders, key=lambda row: (
            row.priority_sort, row.due_date, row.part_number, row.order_id,
        ))),
        actions=tuple(sorted(filtered_actions, key=lambda row: (
            row.priority_sort, row.due_date, row.days_remaining, row.part_number, row.lot_id,
        ))),
        queue_rows=tuple(sorted(queue_rows, key=lambda row: (
            row.priority_sort, row.due_date, row.part_number, row.order_id,
        ))),
        wip_rows=visible_wip_rows,
    )


def _unique_fields(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise OperatorWorkCenterError("The report contains duplicate JSON fields.")
        output[key] = value
    return output


def _nonfinite(_value):
    raise OperatorWorkCenterError("The report contains a nonfinite JSON number.")


def read_snapshot(path: Path) -> WorkCenterSnapshot:
    if not path.is_file():
        raise OperatorWorkCenterError("The report must be a regular file.")
    with path.open("rb") as stream:
        data = stream.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise OperatorWorkCenterError("The report is empty or exceeds its size limit.")
    payload = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_nonfinite,
    )
    return WorkCenterSnapshot.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--product", help="Exact part number")
    parser.add_argument("--kanban", type=int, choices=range(1, 7))
    parser.add_argument("--risk", help="Exact risk category for orders and actions")
    args = parser.parse_args(argv)
    try:
        report = filter_work_center(
            read_snapshot(args.snapshot), product=args.product, kanban=args.kanban, risk=args.risk,
        ).model_dump_json(indent=2)
    except OperatorWorkCenterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved report is unreadable or invalid.", file=sys.stderr)
        return 2
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
