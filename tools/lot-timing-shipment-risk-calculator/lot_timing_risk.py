"""Calculate timing, schedule slack, and shipment risk from saved lot allocations."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

MAX_INPUT_BYTES = 1024 * 1024


def calendar_date(value):
    if type(value) is date:
        return value
    if isinstance(value, str) and len(value) == 10:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    raise ValueError("Expected a calendar date in YYYY-MM-DD format")


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]
KanbanKey = Literal["1", "2", "3", "4", "5", "6", "7"]


class PlanningValidationError(ValueError):
    """The saved input does not meet the timing and priority contract."""


class PriorityRuleConfiguration(BaseModel):
    """Explicit replacement for the legacy priority thresholds."""

    severe_schedule_lateness_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_min_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_max_days: int = Field(gt=0, le=365)
    future_shipment_rank_limit: int = Field(ge=2, le=8)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "PriorityRuleConfiguration":
        if (
            self.moderate_schedule_lateness_min_days
            > self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("moderate schedule-lateness thresholds are reversed")
        if (
            self.severe_schedule_lateness_days
            <= self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("severe lateness must exceed the moderate range")
        return self


class TimingException(BaseModel):
    """One explicit product/operation timing override, if later approved."""

    exception_id: str = Field(min_length=1, max_length=100)
    operation: str | None = Field(default=None, min_length=1, max_length=256)
    lot_prefix: str | None = Field(default=None, min_length=1, max_length=40)
    days_remaining_override: int = Field(ge=0, le=365)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_selector(self) -> "TimingException":
        if self.operation is None and self.lot_prefix is None:
            raise ValueError("timing exception requires an operation or lot prefix")
        return self


class LotAllocationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lot_id: str = Field(min_length=1, max_length=120)
    operation: str = Field(min_length=1, max_length=256)
    kanban: int = Field(strict=True, ge=1, le=7)


class OrderInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order_id: str = Field(min_length=1, max_length=120)
    due_date: CalendarDate
    sequence: int = Field(default=1, strict=True, ge=1)
    allocations: tuple[LotAllocationInput, ...] = Field(max_length=1000)

    @model_validator(mode="after")
    def unique_allocations(self):
        if len({lot.lot_id for lot in self.allocations}) != len(self.allocations):
            raise ValueError("Lot IDs must be unique within an order")
        return self


class TimingRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    planning_date: CalendarDate
    kanban_days_remaining: dict[KanbanKey, Annotated[int, Field(strict=True, ge=0)]]
    priority_rules: PriorityRuleConfiguration
    timing_exceptions: tuple[TimingException, ...] = Field(default=(), max_length=1000)
    orders: tuple[OrderInput, ...] = Field(max_length=2000)

    @model_validator(mode="after")
    def validate_configuration(self):
        if set(self.kanban_days_remaining) != set("1234567"):
            raise ValueError("Kanban days must cover K1 through K7")
        if len({item.exception_id for item in self.timing_exceptions}) != len(self.timing_exceptions):
            raise ValueError("Timing exception IDs must be unique")
        if len({order.order_id for order in self.orders}) != len(self.orders):
            raise ValueError("Order IDs must be unique")
        return self


def _days_remaining(
    product: TimingRequest,
    lot: LotAllocationInput,
) -> int:
    matches = [
        item
        for item in product.timing_exceptions
        if (item.operation is None or item.operation == lot.operation)
        and (item.lot_prefix is None or lot.lot_id.startswith(item.lot_prefix))
    ]
    if len(matches) > 1:
        raise PlanningValidationError(
            "Multiple timing exceptions match a saved lot"
        )
    if matches:
        return matches[0].days_remaining_override
    return product.kanban_days_remaining[str(lot.kanban)]


def _priority_result(
    *,
    planning_date: date,
    due_date: date,
    days_remaining: int,
    future_due_dates: tuple[date, ...],
    rules: PriorityRuleConfiguration,
) -> tuple[int, str, str, str, int, int]:
    """Return the priority and day differences for a saved allocation."""

    days_until_due = (due_date - planning_date).days
    schedule_delta = days_until_due - days_remaining
    if days_until_due < 0:
        return (
            1,
            "Rank 1",
            "Past due",
            "The required ship date is before the fixed planning date.",
            days_until_due,
            schedule_delta,
        )
    if schedule_delta <= -rules.severe_schedule_lateness_days:
        return (
            2,
            "Rank 1",
            "Severe process risk",
            "Configured days remaining exceed available days by at least "
            f"{rules.severe_schedule_lateness_days} days.",
            days_until_due,
            schedule_delta,
        )
    if future_due_dates and due_date == future_due_dates[0]:
        return (
            3,
            "Rank 1",
            "Next shipment",
            "The lot is allocated to the earliest non-past-due shipment.",
            days_until_due,
            schedule_delta,
        )
    if (
        -rules.moderate_schedule_lateness_max_days
        <= schedule_delta
        <= -rules.moderate_schedule_lateness_min_days
    ):
        return (
            4,
            "Rank 1",
            "Moderate process risk",
            "Configured days remaining exceed available days within the "
            "reviewed moderate-risk range.",
            days_until_due,
            schedule_delta,
        )
    if due_date in future_due_dates:
        shipment_number = future_due_dates.index(due_date) + 1
        if 2 <= shipment_number <= rules.future_shipment_rank_limit:
            return (
                shipment_number + 3,
                f"Rank {shipment_number}",
                f"Future shipment {shipment_number}",
                "The lot is currently on schedule for a later reviewed shipment.",
                days_until_due,
                schedule_delta,
            )
    return (
        9,
        "Unranked",
        "Outside configured ranking horizon",
        "The due date is outside the configured future-shipment ranking horizon.",
        days_until_due,
        schedule_delta,
    )


PRIORITY_FIELDS = ("priority_sort", "priority_label", "risk_category", "risk_reason",
                   "days_until_due", "schedule_delta")


def calculate_timing(request: TimingRequest) -> dict:
    ordered = sorted(request.orders, key=lambda order: (order.due_date, order.sequence, order.order_id))
    future_due_dates = tuple(sorted({order.due_date for order in ordered
                                     if order.due_date >= request.planning_date}))
    results = []
    for order in ordered:
        allocations = []
        for lot in order.allocations:
            days_remaining = _days_remaining(request, lot)
            priority = _priority_result(
                planning_date=request.planning_date,
                due_date=order.due_date,
                days_remaining=days_remaining,
                future_due_dates=future_due_dates,
                rules=request.priority_rules,
            )
            allocations.append({
                **lot.model_dump(),
                "legacy_days_remaining": days_remaining,
                **dict(zip(PRIORITY_FIELDS, priority, strict=True)),
            })
        if allocations:
            highest = min(allocations, key=lambda item: (item["priority_sort"], item["lot_id"]))
            order_priority = {key: highest[key] for key in PRIORITY_FIELDS[:4]}
            priority_lot_id = highest["lot_id"]
        else:
            order_priority = {
                "priority_sort": 9,
                "priority_label": "Unranked",
                "risk_category": "No allocated WIP",
                "risk_reason": "No WIP lot was allocated to this order.",
            }
            priority_lot_id = None
        results.append({
            "order_id": order.order_id,
            "sequence": order.sequence,
            "due_date": order.due_date.isoformat(),
            **order_priority,
            "priority_lot_id": priority_lot_id,
            "allocations": allocations,
        })
    return {
        "status": "PASS",
        "planning_date": request.planning_date.isoformat(),
        "future_due_dates": [value.isoformat() for value in future_due_dates],
        "orders": results,
    }


def unique_fields(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ValueError("Duplicate JSON field")
    return result


def read_request(path: Path) -> TimingRequest:
    if not path.is_file():
        raise PlanningValidationError("Expected a saved JSON file")
    with path.open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise PlanningValidationError("JSON exceeds the 1 MiB input limit")
    try:
        fields = json.loads(content.decode("utf-8-sig"), object_pairs_hook=unique_fields)
        return TimingRequest.model_validate(fields)
    except (ValueError, RecursionError) as exc:
        raise PlanningValidationError("Invalid lot timing input JSON") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        report = calculate_timing(read_request(args.input))
    except PlanningValidationError as exc:
        print(f"Lot timing: {exc}", file=sys.stderr)
        return 2
    except OSError:
        print("Lot timing: cannot read saved JSON", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
