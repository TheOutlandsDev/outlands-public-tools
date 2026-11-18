"""Fail-closed invariants for the automatic lot-start queue."""

from __future__ import annotations

from collections.abc import Iterable
from math import ceil
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class AutomaticLotStartQueueValidationError(ValueError):
    """Raised when persisted queue values disagree with the governed formula."""


class AutomaticLotStartQueueView(Protocol):
    modality: str
    part_number: str
    lot_prefix: str
    start_quantity: int
    remaining_demand: int
    eligible_wip: int
    uncovered_demand: int
    recommended_lot_count: int
    queue_status: Literal["ACTIVE", "CLEAR"]
    wip_source_sha256: str | None


class AutomaticLotStartQueueSummary(BaseModel):
    configured_modalities: int = Field(ge=0, le=20)
    open_order_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    covered_by_wip: int = Field(ge=0)
    coverage_surplus: int = Field(ge=0)
    uncovered_after_wip: int = Field(ge=0)
    starts_required: int = Field(ge=0)
    wip_source_sha256: str | None
    formula: Literal["MAX(0, OPEN_ORDER_DEMAND - ELIGIBLE_WIP)"] = (
        "MAX(0, OPEN_ORDER_DEMAND - ELIGIBLE_WIP)"
    )

    model_config = ConfigDict(frozen=True)


def validate_and_summarize_automatic_queue(
    queue: Iterable[AutomaticLotStartQueueView],
) -> AutomaticLotStartQueueSummary:
    """Validate each product row before producing aggregate display values."""

    rows = tuple(queue)
    modalities = [row.modality for row in rows]
    parts = [row.part_number for row in rows]
    prefixes = [row.lot_prefix for row in rows]
    for label, values in (
        ("modality", modalities),
        ("part number", parts),
        ("lot prefix", prefixes),
    ):
        if len(values) != len(set(values)):
            raise AutomaticLotStartQueueValidationError(
                f"The automatic queue contains a duplicate {label}."
            )

    source_hashes = {row.wip_source_sha256 for row in rows}
    if rows and (None in source_hashes or len(source_hashes) != 1):
        raise AutomaticLotStartQueueValidationError(
            "The automatic queue does not reference one accepted WIP snapshot."
        )

    open_order_demand = 0
    eligible_wip = 0
    covered_by_wip = 0
    coverage_surplus = 0
    uncovered_after_wip = 0
    starts_required = 0
    for row in rows:
        expected_uncovered = max(0, row.remaining_demand - row.eligible_wip)
        expected_lots = (
            ceil(expected_uncovered / row.start_quantity)
            if expected_uncovered
            else 0
        )
        expected_status = "ACTIVE" if expected_lots else "CLEAR"
        if row.uncovered_demand != expected_uncovered:
            raise AutomaticLotStartQueueValidationError(
                f"The {row.modality} uncovered-demand value is inconsistent."
            )
        if row.recommended_lot_count != expected_lots:
            raise AutomaticLotStartQueueValidationError(
                f"The {row.modality} lot recommendation is inconsistent."
            )
        if row.queue_status != expected_status:
            raise AutomaticLotStartQueueValidationError(
                f"The {row.modality} queue status is inconsistent."
            )
        open_order_demand += row.remaining_demand
        eligible_wip += row.eligible_wip
        covered_by_wip += min(row.remaining_demand, row.eligible_wip)
        coverage_surplus += max(0, row.eligible_wip - row.remaining_demand)
        uncovered_after_wip += row.uncovered_demand
        starts_required += row.recommended_lot_count

    return AutomaticLotStartQueueSummary(
        configured_modalities=len(rows),
        open_order_demand=open_order_demand,
        eligible_wip=eligible_wip,
        covered_by_wip=covered_by_wip,
        coverage_surplus=coverage_surplus,
        uncovered_after_wip=uncovered_after_wip,
        starts_required=starts_required,
        wip_source_sha256=(next(iter(source_hashes)) if source_hashes else None),
    )
