"""Project operator lot allocations from saved Order Needs, WIP, and planning rules."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


MAX_INPUT_BYTES = 16 * 1024 * 1024
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Part = Annotated[str, Field(min_length=1, max_length=80)]
Quantity = Annotated[StrictInt, Field(ge=0)]
Model = TypeVar("Model", bound=BaseModel)


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


class ReviewStatus(str, Enum):
    """Manufacturing-authority status for a controlled planning value."""

    DRAFT_LEGACY_SOURCE = "DRAFT_LEGACY_SOURCE"


class ParameterProvenance(BaseModel):
    """Traceability attached to one reviewed group of planning values."""

    source: str = Field(min_length=1, max_length=256)
    review_status: ReviewStatus
    reviewed_by: str = Field(min_length=1, max_length=120)
    reviewed_on: date

    model_config = ConfigDict(frozen=True)


class PriorityRuleConfiguration(BaseModel):
    """Explicit replacement for the legacy priority thresholds."""

    severe_schedule_lateness_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_min_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_max_days: int = Field(gt=0, le=365)
    future_shipment_rank_limit: int = Field(ge=2, le=8)

    model_config = ConfigDict(frozen=True)

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
    provenance: ParameterProvenance

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_selector(self) -> "TimingException":
        if self.operation is None and self.lot_prefix is None:
            raise ValueError("timing exception requires an operation or lot prefix")
        return self


class OrderNeedsRow(BaseModel):
    due_date: date
    iso_year: int = Field(ge=2020, le=2100)
    iso_week: int = Field(ge=1, le=53)
    part_number: str
    modality: str
    order_line_count: int = Field(gt=0)
    ordered_quantity: int = Field(gt=0)
    accepted_ship_quantity: int = Field(ge=0)
    ready_for_logistics_quantity: int = Field(default=0, ge=0)
    remaining_demand: int = Field(gt=0)
    configured: bool
    planning_status: Literal[
        "COVERED", "PARTIALLY_COVERED", "UNCOVERED", "FAIL_CLOSED"
    ]
    eligible_wip_before: int | None = Field(default=None, ge=0)
    covered_by_wip: int | None = Field(default=None, ge=0)
    uncovered_after_wip: int | None = Field(default=None, ge=0)
    eligible_wip_after: int | None = Field(default=None, ge=0)
    lot_size: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_conservation(self) -> "OrderNeedsRow":
        if self.ordered_quantity != (
            self.accepted_ship_quantity
            + self.ready_for_logistics_quantity
            + self.remaining_demand
        ):
            raise ValueError("order-row demand conservation failed")
        planning_values = (
            self.eligible_wip_before,
            self.covered_by_wip,
            self.uncovered_after_wip,
            self.eligible_wip_after,
            self.lot_size,
        )
        if not self.configured:
            if self.planning_status != "FAIL_CLOSED" or any(
                value is not None for value in planning_values
            ):
                raise ValueError("unconfigured demand must fail closed")
            return self
        if any(value is None for value in planning_values):
            raise ValueError("configured demand is missing planning values")
        if self.remaining_demand != self.covered_by_wip + self.uncovered_after_wip:
            raise ValueError("coverage conservation failed")
        if self.eligible_wip_before != self.covered_by_wip + self.eligible_wip_after:
            raise ValueError("WIP conservation failed")
        return self


class OrderNeedsSource(BaseModel):
    revision_sha256: Digest
    wip_source_sha256: Digest


class OrderRow(BaseModel):
    part_number: Part


class ProductSummary(OrderRow):
    eligible_wip: Quantity
    configured: StrictBool


class ActiveRevision(BaseModel):
    sha256: Digest


class VerifiedSource(BaseModel):
    sha256: Digest
    wip_sha256: Digest


class OrderNeedsSnapshot(BaseModel):
    generated_at: datetime
    source: OrderNeedsSource
    rows: tuple[OrderNeedsRow, ...]
    products: tuple[ProductSummary, ...]

    @model_validator(mode="after")
    def validate_keys(self):
        order_keys = {(row.due_date, row.part_number, row.modality) for row in self.rows}
        if len(order_keys) != len(self.rows):
            raise ValueError("The snapshot contains duplicate grouped orders.")
        if len({row.part_number for row in self.products}) != len(self.products):
            raise ValueError("The snapshot contains duplicate product summaries.")
        return self


class AssignedWIPRecord(BaseModel):
    lot_id: str = Field(min_length=1, max_length=80)
    source_product: Part
    canonical_product: Part
    current_step: str = Field(min_length=1, max_length=256)
    kanban: int = Field(ge=1, le=6)
    total_parts: Quantity
    quantity_in_process: Quantity
    parts_completed: Quantity
    yield_percent: float = Field(ge=0, allow_inf_nan=False)


class OperationsSnapshot(BaseModel):
    active_revision: ActiveRevision
    wip_source_sha256: Digest
    wip_rows: tuple[AssignedWIPRecord, ...]

    @model_validator(mode="after")
    def validate_lot_ids(self):
        if len({row.lot_id for row in self.wip_rows}) != len(self.wip_rows):
            raise ValueError("The WIP snapshot contains duplicate lot IDs.")
        return self


class ProductPlanningRules(BaseModel):
    part_number: Part
    operation_to_kanban: dict[str, Annotated[int, Field(ge=1, le=7)]]
    kanban_days_remaining: dict[int, Quantity]
    timing_exceptions: tuple[TimingException, ...]
    priority_rules: PriorityRuleConfiguration

    @model_validator(mode="after")
    def validate_timing_coverage(self):
        if not set(range(1, 7)).issubset(self.kanban_days_remaining):
            raise ValueError("The planning rules must provide timing for Kanban steps 1 to 6.")
        return self


class PlanningRules(BaseModel):
    products: tuple[ProductPlanningRules, ...]

    @model_validator(mode="after")
    def validate_product_keys(self):
        if len({row.part_number for row in self.products}) != len(self.products):
            raise ValueError("The planning rules contain duplicate products.")
        return self


class InputSummary(BaseModel):
    open_orders: int
    open_demand: int


class AllocationSummary(BaseModel):
    demand: int
    covered: int
    uncovered: int
    recommended_starts: int


class AllocationReport(BaseModel):
    source_mode: Literal["Authoritative current O&S and accepted WIP"] = (
        "Authoritative current O&S and accepted WIP"
    )
    source: VerifiedSource
    current_inputs: InputSummary
    planning: AllocationSummary
    orders: tuple[OperatorOrderRow, ...]
    actions: tuple[OperatorActionRow, ...]
    wip_rows: tuple[OperatorWipRow, ...]
    available_risks: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def _is_verification(row: AssignedWIPRecord) -> bool:
    product = row.source_product.upper()
    return (
        row.source_product != row.canonical_product
        or row.lot_id.upper().startswith("V")
        or product.endswith("V")
        or product.endswith("-V")
    )


def _authoritative_days_remaining(product: Any, row: Any, kanban: int) -> int:
    matches = [
        item
        for item in product.timing_exceptions
        if (item.operation is None or item.operation == row.current_step)
        and (item.lot_prefix is None or row.lot_id.startswith(item.lot_prefix))
    ]
    if len(matches) > 1:
        raise OperatorWorkCenterError(
            f"multiple timing exceptions match current lot {row.lot_id}"
        )
    return (
        matches[0].days_remaining_override
        if matches
        else product.kanban_days_remaining[kanban]
    )


def _unallocated_priority(
    *,
    due_date: date,
    planning_date: date,
    configured: bool,
    uncovered: int,
) -> tuple[int, str, str, str]:
    if not configured:
        return (
            1,
            "Configuration required",
            "Planning blocked",
            "This current O&S demand is outside approved planning configuration.",
        )
    if uncovered:
        return (
            1 if due_date < planning_date else 2,
            "Start required",
            "Uncovered demand",
            "Current eligible WIP does not fully cover this production demand.",
        )
    if due_date < planning_date:
        return (
            1,
            "Past due",
            "Past due",
            "The current production commit date is before today.",
        )
    return (
        5,
        "Scheduled",
        "Current production demand",
        "No individual allocation determines this order group's priority.",
    )


def _display_risk(category: str, reason: str) -> tuple[str, str]:
    """Use operator-facing language without changing the planning contract."""

    if category == "Outside configured ranking horizon":
        return (
            "Scheduled later",
            "The due date is beyond the currently ranked future-shipment window.",
        )
    return category, reason


def _priority_result(
    *,
    planning_date: date,
    due_date: date,
    days_remaining: int,
    future_due_dates: tuple[date, ...],
    rules: PriorityRuleConfiguration,
) -> tuple[int, str, str, str, int, int]:
    """Return the deterministic reviewed interpretation of planning priority ordering."""

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


def project_allocations(
    order_needs: OrderNeedsSnapshot,
    operations: OperationsSnapshot,
    planning_configuration: PlanningRules,
) -> AllocationReport:
    source_sha256 = operations.active_revision.sha256
    wip_sha256 = operations.wip_source_sha256
    if source_sha256 != order_needs.source.revision_sha256:
        raise OperatorWorkCenterError(
            "The operator O&S revision does not match authoritative Order Needs."
        )
    if wip_sha256 != order_needs.source.wip_source_sha256:
        raise OperatorWorkCenterError(
            "The operator WIP revision does not match authoritative Order Needs."
        )

    current_products = tuple(sorted({row.part_number for row in order_needs.rows}))
    eligible_wip = tuple(
        row
        for row in operations.wip_rows
        if row.canonical_product in current_products and not _is_verification(row)
    )
    expected_wip_by_product = {
        row.part_number: row.eligible_wip
        for row in order_needs.products
        if row.part_number in current_products and row.configured
    }
    actual_wip_by_product = {
        part_number: sum(
            row.total_parts
            for row in eligible_wip
            if row.canonical_product == part_number
        )
        for part_number in expected_wip_by_product
    }
    if actual_wip_by_product != expected_wip_by_product:
        raise OperatorWorkCenterError(
            "Current lot-level WIP does not reconcile with authoritative coverage."
        )
    product_configuration = {row.part_number: row for row in planning_configuration.products}
    if any(row.configured != (row.part_number in product_configuration)
           for row in order_needs.rows):
        raise OperatorWorkCenterError("Planning rules disagree with the configured Order Needs scope.")
    expected_products = {row.part_number for row in order_needs.rows if row.configured}
    if set(expected_wip_by_product) != expected_products:
        raise OperatorWorkCenterError("Configured current products need matching Order Needs summaries.")

    planning_date = order_needs.generated_at.date()
    future_due_dates = tuple(sorted({
        row.due_date for row in order_needs.rows if row.due_date >= planning_date
    }))
    remaining = {row.lot_id: row.total_parts for row in eligible_wip}
    order_rows: list[OperatorOrderRow] = []
    action_rows: list[OperatorActionRow] = []
    for need in order_needs.rows:
        order_id = "|".join(
            (need.due_date.isoformat(), need.part_number, need.modality)
        )
        configuration = product_configuration.get(need.part_number)
        uncovered = need.uncovered_after_wip or 0
        allocations: list[OperatorActionRow] = []
        quantity_needed = need.remaining_demand
        if configuration is not None:
            for current_kanban in range(6, 0, -1):
                candidates = sorted(
                    (
                        row
                        for row in eligible_wip
                        if row.canonical_product == need.part_number
                        and configuration.operation_to_kanban.get(
                            row.current_step, row.kanban
                        )
                        == current_kanban
                        and remaining[row.lot_id] > 0
                    ),
                    key=lambda row: (remaining[row.lot_id], row.lot_id),
                )
                for candidate in candidates:
                    if quantity_needed == 0:
                        break
                    allocated = min(quantity_needed, remaining[candidate.lot_id])
                    days_remaining = _authoritative_days_remaining(
                        configuration,
                        candidate,
                        current_kanban,
                    )
                    priority = _priority_result(
                        planning_date=planning_date,
                        due_date=need.due_date,
                        days_remaining=days_remaining,
                        future_due_dates=future_due_dates,
                        rules=configuration.priority_rules,
                    )
                    risk_category, risk_reason = _display_risk(
                        priority[2],
                        priority[3],
                    )
                    identity = {
                        "source_revision_sha256": source_sha256,
                        "wip_source_sha256": wip_sha256,
                        "part_number": need.part_number,
                        "order_id": order_id,
                        "lot_id": candidate.lot_id,
                        "kanban": current_kanban,
                        "operation": candidate.current_step,
                    }
                    action = OperatorActionRow(
                        action_id=sha256(
                            json.dumps(
                                identity,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest(),
                        modality=need.modality,
                        part_number=need.part_number,
                        order_id=order_id,
                        lot_id=candidate.lot_id,
                        due_date=need.due_date,
                        kanban=current_kanban,
                        operation=candidate.current_step,
                        allocated_quantity=allocated,
                        days_remaining=days_remaining,
                        days_until_due=priority[4],
                        schedule_delta=priority[5],
                        priority_label=priority[1],
                        priority_sort=priority[0],
                        risk_category=risk_category,
                        risk_reason=risk_reason,
                    )
                    allocations.append(action)
                    action_rows.append(action)
                    remaining[candidate.lot_id] -= allocated
                    quantity_needed -= allocated

        covered = need.remaining_demand - quantity_needed
        if need.configured and (
            covered != need.covered_by_wip or quantity_needed != uncovered
        ):
            raise OperatorWorkCenterError(
                "Current lot allocation does not conserve authoritative demand."
            )
        representative = min(
            allocations,
            key=lambda row: (row.priority_sort, row.lot_id),
            default=None,
        )
        if representative is None:
            priority_sort, priority_label, risk_category, risk_reason = (
                _unallocated_priority(
                    due_date=need.due_date,
                    planning_date=planning_date,
                    configured=need.configured,
                    uncovered=quantity_needed,
                )
            )
        else:
            priority_sort = representative.priority_sort
            priority_label = representative.priority_label
            risk_category = representative.risk_category
            risk_reason = representative.risk_reason
        order_rows.append(
            OperatorOrderRow(
                modality=need.modality,
                part_number=need.part_number,
                order_id=order_id,
                due_date=need.due_date,
                demand=need.remaining_demand,
                covered=covered,
                uncovered=quantity_needed,
                recommended_start=(quantity_needed if need.configured else 0),
                recommended_lots=(
                    (quantity_needed + need.lot_size - 1) // need.lot_size
                    if need.configured and quantity_needed and need.lot_size
                    else 0
                ),
                allocation_count=len(allocations),
                order_line_count=need.order_line_count,
                priority_label=priority_label,
                priority_sort=priority_sort,
                risk_category=risk_category,
                risk_reason=risk_reason,
            )
        )

    demand = sum(row.demand for row in order_rows)
    return AllocationReport(
        source=VerifiedSource(sha256=source_sha256, wip_sha256=wip_sha256),
        current_inputs=InputSummary(
            open_orders=sum(row.order_line_count for row in order_rows),
            open_demand=demand,
        ),
        planning=AllocationSummary(
            demand=demand,
            covered=sum(row.covered for row in order_rows),
            uncovered=sum(row.uncovered for row in order_rows),
            recommended_starts=sum(row.recommended_start for row in order_rows),
        ),
        orders=tuple(sorted(order_rows, key=lambda row: (
            row.priority_sort, row.due_date, row.part_number, row.order_id,
        ))),
        actions=tuple(sorted(action_rows, key=lambda row: (
            row.priority_sort, row.due_date, row.days_remaining, row.part_number, row.lot_id,
        ))),
        wip_rows=tuple(
            OperatorWipRow(
                lot_id=row.lot_id,
                product=row.canonical_product,
                operation=row.current_step,
                kanban=row.kanban,
                in_process=row.quantity_in_process,
                completed=row.parts_completed,
                total=row.total_parts,
                yield_percent=row.yield_percent,
            )
            for row in operations.wip_rows
        ),
        available_risks=tuple(sorted({row.risk_category for row in (*order_rows, *action_rows)})),
    )


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise OperatorWorkCenterError("A snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def _nonfinite(_value):
    raise OperatorWorkCenterError("A snapshot contains a nonfinite JSON number.")


def read_snapshot(path: Path, model: type[Model]) -> Model:
    if not path.is_file():
        raise OperatorWorkCenterError("A snapshot must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise OperatorWorkCenterError("A snapshot is empty or exceeds its size limit.")
    payload = json.loads(
        raw.decode("utf-8"), object_pairs_hook=_unique_fields, parse_constant=_nonfinite,
    )
    return model.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("order_needs", type=Path)
    parser.add_argument("operations", type=Path)
    parser.add_argument("planning_rules", type=Path)
    args = parser.parse_args(argv)
    try:
        report = project_allocations(
            read_snapshot(args.order_needs, OrderNeedsSnapshot),
            read_snapshot(args.operations, OperationsSnapshot),
            read_snapshot(args.planning_rules, PlanningRules),
        )
    except OperatorWorkCenterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: A saved input is unreadable or invalid.", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
