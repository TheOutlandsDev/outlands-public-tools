"""Deterministic, fail-closed production-planning domain engine."""


from __future__ import annotations


from datetime import date


from decimal import Decimal, ROUND_HALF_UP


from enum import Enum


from hashlib import sha256


from pathlib import Path


import json


from pydantic import BaseModel, ConfigDict, Field, model_validator


class PlanningValidationError(ValueError):
    """Raised when planning input cannot be evaluated safely."""


class ReviewStatus(str, Enum):
    """Manufacturing-authority status for a controlled planning value."""

    CALLER_ASSERTED = "CALLER_ASSERTED"


class ParameterProvenance(BaseModel):
    """Traceability attached to one reviewed group of planning values."""

    source: str = Field(min_length=1, max_length=256)
    review_status: ReviewStatus
    reviewed_by: str = Field(min_length=1, max_length=120)
    reviewed_on: date

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class PriorityRuleConfiguration(BaseModel):
    """Explicit replacement for the legacy priority thresholds."""

    severe_schedule_lateness_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_min_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_max_days: int = Field(gt=0, le=365)
    future_shipment_rank_limit: int = Field(ge=2, le=6)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

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

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_selector(self) -> "TimingException":
        if self.operation is None and self.lot_prefix is None:
            raise ValueError("timing exception requires an operation or lot prefix")
        return self


class ProductPlanningConfiguration(BaseModel):
    """Reviewed planning constants for one supported product."""

    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    flow_name: str = Field(min_length=1, max_length=256)
    route_version: int = Field(gt=0)
    expected_lot_start_quantity: int = Field(gt=0)
    uncovered_demand_start_factor: Decimal = Field(ge=Decimal("1"), le=Decimal("2"))
    operation_to_kanban: dict[str, int] = Field(min_length=1)
    kanban_days_remaining: dict[int, int]
    priority_rules: PriorityRuleConfiguration
    timing_exceptions: tuple[TimingException, ...]
    parameter_provenance: dict[str, ParameterProvenance]

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_controlled_mappings(self) -> "ProductPlanningConfiguration":
        if set(self.kanban_days_remaining) != set(range(1, 8)):
            raise ValueError("kanban_days_remaining must define Kanbans 1 through 7")
        if any(value < 0 for value in self.kanban_days_remaining.values()):
            raise ValueError("kanban days remaining must not be negative")
        if any(value not in range(1, 8) for value in self.operation_to_kanban.values()):
            raise ValueError("every operation must map to Kanban 1 through 7")
        required_provenance = {
            "expected_lot_start_quantity",
            "uncovered_demand_start_factor",
            "operation_to_kanban",
            "kanban_days_remaining",
            "priority_rules",
            "timing_exceptions",
        }
        if set(self.parameter_provenance) != required_provenance:
            raise ValueError("parameter provenance keys are incomplete or unexpected")
        exception_ids = [item.exception_id for item in self.timing_exceptions]
        if len(exception_ids) != len(set(exception_ids)):
            raise ValueError("timing exception IDs must be unique")
        return self


class PlanningConfiguration(BaseModel):
    """Versioned collection of reviewed product configurations."""

    configuration_id: str = Field(min_length=1, max_length=100)
    configuration_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    effective_date: date
    source_set: str = Field(min_length=1, max_length=256)
    status: str = Field(pattern=r"^DECLARED_PLAN_ONLY$")
    products: tuple[ProductPlanningConfiguration, ...] = Field(min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "PlanningConfiguration":
        modalities = [product.modality for product in self.products]
        part_numbers = [product.part_number for product in self.products]
        if len(modalities) != len(set(modalities)):
            raise ValueError("product modalities must be unique")
        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError("product part numbers must be unique")
        return self

    def product(self, modality: str, part_number: str) -> ProductPlanningConfiguration:
        matches = [
            product
            for product in self.products
            if product.modality == modality and product.part_number == part_number
        ]
        if len(matches) != 1:
            raise PlanningValidationError(
                f"unsupported product identity: modality={modality!r}, part_number={part_number!r}"
            )
        return matches[0]


class FlexOrder(BaseModel):
    """One bounded synthetic order supplied to the pure planning engine."""

    order_id: str = Field(min_length=1, max_length=80)
    sequence: int = Field(gt=0)
    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    due_date: date
    quantity: int = Field(gt=0)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class FlexWipLot(BaseModel):
    """Available WIP after any separately controlled import normalization."""

    lot_id: str = Field(min_length=1, max_length=80)
    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    operation: str = Field(min_length=1, max_length=256)
    kanban: int = Field(ge=1, le=7)
    quantity: int = Field(gt=0)
    quantity_basis: str = Field(
        pattern=r"^caller_declared_available$"
    )

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class LotAllocation(BaseModel):
    lot_id: str
    kanban: int
    operation: str
    quantity: int = Field(gt=0)
    legacy_days_remaining: int = Field(ge=0)
    days_until_due: int
    schedule_delta: int
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class OrderPlan(BaseModel):
    order_id: str
    due_date: date
    demand_quantity: int = Field(gt=0)
    allocations: tuple[LotAllocation, ...]
    covered_quantity: int = Field(ge=0)
    uncovered_quantity: int = Field(ge=0)
    recommended_start_quantity: int = Field(ge=0)
    priority_label: str = Field(min_length=1, max_length=40)
    priority_sort: int = Field(ge=1, le=9)
    risk_category: str = Field(min_length=1, max_length=80)
    risk_reason: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class PlanningConservation(BaseModel):
    demand_input: int = Field(ge=0)
    covered: int = Field(ge=0)
    uncovered: int = Field(ge=0)
    wip_input: int = Field(ge=0)
    wip_allocated: int = Field(ge=0)
    wip_remaining: int = Field(ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class FlexPlan(BaseModel):
    planning_date: date
    configuration_id: str
    configuration_version: str
    configuration_effective_date: date
    configuration_source_set: str
    modality: str
    part_number: str
    flow_name: str
    route_version: int
    expected_lot_start_quantity: int
    orders: tuple[OrderPlan, ...]
    remaining_wip: dict[str, int]
    conservation: PlanningConservation

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


def _recommended_start(uncovered: int, factor: Decimal) -> int:
    if uncovered == 0:
        return 0
    return int((Decimal(uncovered) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _days_remaining(
    product: ProductPlanningConfiguration,
    lot: FlexWipLot,
) -> int:
    matches = [
        item
        for item in product.timing_exceptions
        if (item.operation is None or item.operation == lot.operation)
        and (item.lot_prefix is None or lot.lot_id.startswith(item.lot_prefix))
    ]
    if len(matches) > 1:
        raise PlanningValidationError(
            f"multiple timing exceptions match lot {lot.lot_id!r}"
        )
    if matches:
        return matches[0].days_remaining_override
    return product.kanban_days_remaining[lot.kanban]


def _priority_result(
    *,
    planning_date: date,
    due_date: date,
    days_remaining: int,
    future_due_dates: tuple[date, ...],
    rules: PriorityRuleConfiguration,
) -> tuple[int, str, str, str, int, int]:
    """Return the deterministic reviewed interpretation of declared priority ordering."""

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


def comparison_result(plan: FlexPlan) -> dict[str, object]:
    """Machine-readable expected result retained by the frozen fixture."""

    return {
        "covered_by_order": [order.covered_quantity for order in plan.orders],
        "uncovered_by_order": [order.uncovered_quantity for order in plan.orders],
        "recommended_start_by_order": [
            order.recommended_start_quantity for order in plan.orders
        ],
        "priority_sort_by_order": [order.priority_sort for order in plan.orders],
        "priority_label_by_order": [order.priority_label for order in plan.orders],
        "allocation_timing": [
            [
                {
                    "lot_id": allocation.lot_id,
                    "days_remaining": allocation.legacy_days_remaining,
                    "days_until_due": allocation.days_until_due,
                    "schedule_delta": allocation.schedule_delta,
                    "priority_sort": allocation.priority_sort,
                    "priority_label": allocation.priority_label,
                    "risk_category": allocation.risk_category,
                }
                for allocation in order.allocations
            ]
            for order in plan.orders
        ],
        **plan.conservation.model_dump(),
    }


def build_flex_plan(
    *,
    planning_date: date,
    modality: str,
    part_number: str,
    orders: list[FlexOrder],
    wip: list[FlexWipLot],
    configuration: PlanningConfiguration,
) -> FlexPlan:
    """Allocate WIP deterministically and prove demand/WIP conservation."""

    product = configuration.product(modality, part_number)
    if not orders:
        raise PlanningValidationError("at least one order is required")

    order_ids = [order.order_id for order in orders]
    sequences = [order.sequence for order in orders]
    lot_ids = [lot.lot_id for lot in wip]
    if len(order_ids) != len(set(order_ids)):
        raise PlanningValidationError("order IDs must be unique")
    if len(sequences) != len(set(sequences)):
        raise PlanningValidationError("order sequences must be unique")
    if len(lot_ids) != len(set(lot_ids)):
        raise PlanningValidationError("WIP lot IDs must be unique")

    for order in orders:
        if (order.modality, order.part_number) != (modality, part_number):
            raise PlanningValidationError("every order must match the selected product")
    for lot in wip:
        if (lot.modality, lot.part_number) != (modality, part_number):
            raise PlanningValidationError("every WIP lot must match the selected product")
        configured_kanban = product.operation_to_kanban.get(lot.operation)
        if configured_kanban is None:
            raise PlanningValidationError(f"unmapped WIP operation: {lot.operation!r}")
        if configured_kanban != lot.kanban:
            raise PlanningValidationError(
                f"WIP operation/Kanban mismatch for lot {lot.lot_id!r}"
            )

    remaining = {lot.lot_id: lot.quantity for lot in wip}
    lot_by_id = {lot.lot_id: lot for lot in wip}
    ordered_orders = sorted(orders, key=lambda order: (order.due_date, order.sequence, order.order_id))
    future_due_dates = tuple(
        sorted({order.due_date for order in ordered_orders if order.due_date >= planning_date})
    )
    plans: list[OrderPlan] = []

    for order in ordered_orders:
        need = order.quantity
        allocations: list[LotAllocation] = []
        for kanban in range(6, 0, -1):
            candidates = sorted(
                (
                    lot
                    for lot in wip
                    if lot.kanban == kanban and remaining[lot.lot_id] > 0
                ),
                key=lambda lot: (remaining[lot.lot_id], lot.lot_id),
            )
            for lot in candidates:
                if need == 0:
                    break
                quantity = min(need, remaining[lot.lot_id])
                if quantity <= 0:
                    continue
                days_remaining = _days_remaining(product, lot)
                (
                    priority_sort,
                    priority_label,
                    risk_category,
                    risk_reason,
                    days_until_due,
                    schedule_delta,
                ) = _priority_result(
                    planning_date=planning_date,
                    due_date=order.due_date,
                    days_remaining=days_remaining,
                    future_due_dates=future_due_dates,
                    rules=product.priority_rules,
                )
                allocations.append(
                    LotAllocation(
                        lot_id=lot.lot_id,
                        kanban=lot.kanban,
                        operation=lot.operation,
                        quantity=quantity,
                        legacy_days_remaining=days_remaining,
                        days_until_due=days_until_due,
                        schedule_delta=schedule_delta,
                        priority_label=priority_label,
                        priority_sort=priority_sort,
                        risk_category=risk_category,
                        risk_reason=risk_reason,
                    )
                )
                need -= quantity
                remaining[lot.lot_id] -= quantity

        covered = order.quantity - need
        if allocations:
            highest_risk = min(
                allocations,
                key=lambda item: (item.priority_sort, item.lot_id),
            )
            order_priority = (
                highest_risk.priority_label,
                highest_risk.priority_sort,
                highest_risk.risk_category,
                highest_risk.risk_reason,
            )
        else:
            order_priority = (
                "Unranked",
                9,
                "No allocated WIP",
                "No WIP lot was allocated to this order.",
            )
        plans.append(
            OrderPlan(
                order_id=order.order_id,
                due_date=order.due_date,
                demand_quantity=order.quantity,
                allocations=tuple(allocations),
                covered_quantity=covered,
                uncovered_quantity=need,
                recommended_start_quantity=_recommended_start(
                    need,
                    product.uncovered_demand_start_factor,
                ),
                priority_label=order_priority[0],
                priority_sort=order_priority[1],
                risk_category=order_priority[2],
                risk_reason=order_priority[3],
            )
        )

    demand_input = sum(order.quantity for order in orders)
    covered = sum(plan.covered_quantity for plan in plans)
    uncovered = sum(plan.uncovered_quantity for plan in plans)
    wip_input = sum(lot.quantity for lot in wip)
    wip_remaining = sum(remaining.values())
    wip_allocated = wip_input - wip_remaining
    if demand_input != covered + uncovered or wip_input != wip_allocated + wip_remaining:
        raise RuntimeError("planning conservation invariant failed")

    return FlexPlan(
        planning_date=planning_date,
        configuration_id=configuration.configuration_id,
        configuration_version=configuration.configuration_version,
        configuration_effective_date=configuration.effective_date,
        configuration_source_set=configuration.source_set,
        modality=product.modality,
        part_number=product.part_number,
        flow_name=product.flow_name,
        route_version=product.route_version,
        expected_lot_start_quantity=product.expected_lot_start_quantity,
        orders=tuple(plans),
        remaining_wip={lot_id: remaining[lot_id] for lot_id in sorted(lot_by_id)},
        conservation=PlanningConservation(
            demand_input=demand_input,
            covered=covered,
            uncovered=uncovered,
            wip_input=wip_input,
            wip_allocated=wip_allocated,
            wip_remaining=wip_remaining,
        ),
    )
