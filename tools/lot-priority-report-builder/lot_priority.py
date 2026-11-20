"""Project one saved plan's allocations into a stable lot priority report."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import stat
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_PLAN_BYTES = 2 * 1024 * 1024


class PlanAllocation(BaseModel):
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(strict=True, ge=1, le=9)
    lot_id: str = Field(min_length=1, max_length=80)
    legacy_days_remaining: int = Field(strict=True, ge=0)
    days_until_due: int = Field(strict=True)
    kanban: int = Field(strict=True, ge=1, le=7)
    operation: str = Field(min_length=1, max_length=256)
    quantity: int = Field(strict=True, gt=0)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)


class PlanOrder(BaseModel):
    due_date: date
    allocations: tuple[PlanAllocation, ...] = Field(max_length=250)


class FlexPlan(BaseModel):
    """The saved plan fields consumed by the original projection."""

    modality: str = Field(min_length=1, max_length=40)
    planning_date: date
    orders: tuple[PlanOrder, ...] = Field(max_length=250)

    @model_validator(mode="after")
    def enforce_total_row_limit(self) -> "FlexPlan":
        if sum(len(order.allocations) for order in self.orders) > 250:
            raise ValueError("At most 250 lot allocations are supported.")
        return self


class SavedPlan(BaseModel):
    case_id: str = Field(min_length=1, max_length=100)
    source_status: str = Field(min_length=1, max_length=80)
    plan: FlexPlan

    model_config = ConfigDict(extra="forbid")


class PlanInputError(ValueError):
    """A saved plan could not be read or projected."""


class PriorityLotRow(BaseModel):
    """One display-safe allocation row produced by the planning engine."""

    ranking: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    priority_lot: str = Field(min_length=1, max_length=80)
    modality: str = Field(min_length=1, max_length=40)
    shipment_needed: date
    days_until_complete: int = Field(ge=0)
    days_until_due: int
    current_bin: str = Field(pattern=r"^K[1-7]$")
    current_step: str = Field(min_length=1, max_length=256)
    quantity: int = Field(gt=0)
    yield_percent: None = None
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)
    status_color: Literal["Red", "Orange", "Yellow", "Blue"]
    emphasis: Literal["past-due", "highest", "next-shipment", "standard"]

    model_config = ConfigDict(frozen=True)


class TodaysPrioritiesResult(BaseModel):
    """Bounded priority projection with source and calculation provenance."""

    planning_date: date
    case_id: str = Field(min_length=1, max_length=100)
    source_status: str = Field(min_length=1, max_length=80)
    source_mode: Literal[
        "controlled development case",
        "approved snapshot parity",
    ] = "controlled development case"
    row_count: int = Field(ge=0, le=250)
    rows: tuple[PriorityLotRow, ...] = Field(max_length=250)

    model_config = ConfigDict(frozen=True)


def _emphasis(*, days_until_due: int, risk_category: str) -> str:
    if days_until_due < 0:
        return "past-due"
    if risk_category == "Severe process risk":
        return "highest"
    if risk_category == "Next shipment":
        return "next-shipment"
    return "standard"


def _status_color(priority_sort: int) -> str:
    if priority_sort <= 2:
        return "Red"
    if priority_sort == 3:
        return "Blue"
    if priority_sort == 4:
        return "Orange"
    return "Yellow"


def build_todays_priorities(
    plan: FlexPlan,
    *,
    case_id: str,
    source_status: str,
) -> TodaysPrioritiesResult:
    """Flatten reviewed lot allocations into a stable operator-facing order."""

    rows = [
        PriorityLotRow(
            ranking=allocation.priority_label,
            priority_sort=allocation.priority_sort,
            priority_lot=allocation.lot_id,
            modality=plan.modality,
            shipment_needed=order.due_date,
            days_until_complete=allocation.legacy_days_remaining,
            days_until_due=allocation.days_until_due,
            current_bin=f"K{allocation.kanban}",
            current_step=allocation.operation,
            quantity=allocation.quantity,
            risk_category=allocation.risk_category,
            risk_reason=allocation.risk_reason,
            status_color=_status_color(allocation.priority_sort),
            emphasis=_emphasis(
                days_until_due=allocation.days_until_due,
                risk_category=allocation.risk_category,
            ),
        )
        for order in plan.orders
        for allocation in order.allocations
    ]
    rows.sort(
        key=lambda row: (
            row.priority_sort,
            row.shipment_needed,
            row.days_until_complete,
            row.priority_lot,
        )
    )
    return TodaysPrioritiesResult(
        planning_date=plan.planning_date,
        case_id=case_id,
        source_status=source_status,
        row_count=len(rows),
        rows=tuple(rows),
    )


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise PlanInputError("The saved plan JSON has duplicate fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise PlanInputError("The saved plan JSON has a non-finite number.")


def load_saved_plan(path: Path) -> SavedPlan:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise PlanInputError("The saved plan must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_PLAN_BYTES + 1)
    except OSError as exc:
        raise PlanInputError("The saved plan is unavailable.") from exc
    if not 0 < len(content) <= MAX_PLAN_BYTES:
        raise PlanInputError("The saved plan is empty or exceeds its size limit.")
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        return SavedPlan.model_validate(payload)
    except PlanInputError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PlanInputError("The saved plan schema is invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Saved plan JSON with case ID and source status")
    args = parser.parse_args()
    try:
        saved = load_saved_plan(args.plan)
        result = build_todays_priorities(saved.plan, case_id=saved.case_id, source_status=saved.source_status)
    except PlanInputError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError:
        print("The saved plan does not fit the projection.", file=sys.stderr)
        return 2
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
