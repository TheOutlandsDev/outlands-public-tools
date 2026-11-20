"""Rank production follow-up from saved allocation and readiness reports."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
import sys
from typing import Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from order_needs import OrderNeedsResult, _read_json
from shipment_readiness import ShipmentReadinessResult


class InternalPanelFlexLotState(BaseModel):
    lot_id: str
    row_version: int = Field(gt=0)
    last_event_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_modality: str
    display_modality: str
    assembly: str
    quantity: int = Field(gt=0)
    lifecycle_state: Literal[
        "IN_PRODUCTION",
        "COMPLETE_AWAITING_HLA_TRANSFER",
        "TRANSFERRED_TO_HLA",
    ]
    completed_at: datetime | None
    transferred_at: datetime | None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str

    model_config = ConfigDict(frozen=True)


class FlexPriorityItem(BaseModel):
    """One actionable exception with a single owning workspace."""

    rank: int = Field(ge=1, le=25)
    urgency: Literal["PAST_DUE", "CONFIGURATION_REQUIRED", "ACTION_REQUIRED"]
    title: str = Field(min_length=1, max_length=180)
    reason: str = Field(min_length=1, max_length=300)
    due_date: date | None = None
    owner_workspace: Literal[
        "Order Needs",
        "Lot Starts",
        "Living O&S",
        "Logistics Handoff",
        "Panel Flex & HLA",
    ]
    href: str = Field(pattern=r"^/labs/flex/")

    model_config = ConfigDict(frozen=True, extra="forbid")


class FlexPrioritiesResult(BaseModel):
    """Bounded action list derived from current governed planning state."""

    queue_scope: Literal["OPERATOR", "PTL"]
    generated_at: datetime
    source_filename: str = Field(min_length=1, max_length=240)
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_revision_role: Literal["living-os"] = "living-os"
    source_ids: tuple[
        Literal[
            "living-os",
            "accepted-wip",
            "logistics-handoff-workflow",
            "panel-flex-workflow",
        ],
        ...,
    ]
    total_action_count: int = Field(ge=0)
    items: tuple[FlexPriorityItem, ...]
    database_writes: Literal[False] = False

    model_config = ConfigDict(frozen=True, extra="forbid")


def build_flex_priorities(
    order_needs: OrderNeedsResult,
    *,
    as_of: date | None = None,
    limit: int = 8,
) -> FlexPrioritiesResult:
    """Reduce governed planning exceptions to the operator-owned queue."""

    if not 1 <= limit <= 25:
        raise ValueError("priority limit must be between 1 and 25")
    current_date = as_of or order_needs.generated_at.date()
    earliest_due: dict[tuple[str, str], date] = {}
    for row in order_needs.rows:
        key = (row.part_number, row.modality)
        earliest_due[key] = min(row.due_date, earliest_due.get(key, row.due_date))

    candidates: list[tuple[tuple[int, date, str, str], dict[str, object]]] = []
    for product in order_needs.products:
        if product.remaining_demand == 0 or product.planning_status == "CLEAR":
            continue
        key = (product.part_number, product.modality)
        if key not in earliest_due:
            raise ValueError("Actionable products require due-date rows from an unfiltered allocation report")
        if product.planning_status == "FAIL_CLOSED":
            due_date = earliest_due[key]
            urgency = (
                "PAST_DUE" if due_date < current_date else "CONFIGURATION_REQUIRED"
            )
            candidates.append(
                (
                    (
                        0 if urgency == "PAST_DUE" else 1,
                        due_date,
                        product.modality,
                        product.part_number,
                    ),
                    {
                        "urgency": urgency,
                        "title": (
                            f"Planning configuration required for {product.modality}"
                        ),
                        "reason": (
                            f"{product.remaining_demand:,} circuits for "
                            f"{product.part_number} remain outside approved planning "
                            "scope, so coverage and start calculations are blocked."
                        ),
                        "due_date": due_date,
                        "owner_workspace": "Order Needs",
                        "href": "/labs/flex/order-needs?"
                        + urlencode({"part_number": product.part_number}),
                    },
                )
            )
        elif product.planning_status == "STARTS_REQUIRED":
            due_date = product.recommended_start_by or earliest_due[key]
            urgency = "PAST_DUE" if due_date < current_date else "ACTION_REQUIRED"
            lot_count = product.recommended_lot_count or 0
            candidates.append(
                (
                    (
                        0 if urgency == "PAST_DUE" else 2,
                        due_date,
                        product.modality,
                        product.part_number,
                    ),
                    {
                        "urgency": urgency,
                        "title": (
                            f"Start {lot_count} {product.modality} "
                            f"lot{'s' if lot_count != 1 else ''}"
                        ),
                        "reason": (
                            f"{product.uncovered_after_wip or 0:,} circuits for "
                            f"{product.part_number} remain uncovered after accepted WIP."
                        ),
                        "due_date": due_date,
                        "owner_workspace": "Lot Starts",
                        "href": "/labs/flex/lot-starts",
                    },
                )
            )

    return _priority_result(
        queue_scope="OPERATOR",
        generated_at=order_needs.generated_at,
        source_filename=order_needs.source.filename,
        source_revision_sha256=order_needs.source.revision_sha256,
        source_ids=("living-os", "accepted-wip"),
        candidates=candidates,
        limit=limit,
    )


def build_ptl_priorities(
    shipment_readiness: ShipmentReadinessResult,
    *,
    panel_flex_lots: Sequence[InternalPanelFlexLotState] = (),
    as_of: date | None = None,
    limit: int = 8,
) -> FlexPrioritiesResult:
    """Build O&S evidence and handoff actions owned by program leadership."""

    if not 1 <= limit <= 25:
        raise ValueError("priority limit must be between 1 and 25")
    current_date = as_of or shipment_readiness.generated_at.date()
    candidates: list[tuple[tuple[int, date, str, str], dict[str, object]]] = []

    for row in shipment_readiness.rows:
        if (
            row.readiness_state == "LOT_EVIDENCE_REQUIRED"
            and row.production_remaining_quantity > 0
        ):
            due_date = date.fromisoformat(row.commit_date)
            urgency = "PAST_DUE" if due_date < current_date else "ACTION_REQUIRED"
            candidates.append(
                (
                    (
                        0 if urgency == "PAST_DUE" else 1,
                        due_date,
                        row.modality,
                        row.row_id,
                    ),
                    {
                        "urgency": urgency,
                        "title": (
                            "Complete O&S lot evidence for PO "
                            f"{row.customer_or_oracle_po or row.row_id}"
                        ),
                        "reason": (
                            f"{row.order_reference}: "
                            f"{row.production_remaining_quantity:,} docked circuits "
                            f"cannot be cleared until {', '.join(row.missing_fields) or 'lot IDs and quantities'} "
                            "are recorded and validated."
                        ),
                        "due_date": due_date,
                        "owner_workspace": "Living O&S",
                        "href": "/labs/flex/ptl-suite#ptl-os",
                    },
                )
            )
            continue
        if not row.can_mark_ready:
            continue
        due_date = date.fromisoformat(row.commit_date)
        urgency = "PAST_DUE" if due_date < current_date else "ACTION_REQUIRED"
        uncleared_lot_count = sum(
            lot.lifecycle_state != "READY_FOR_LOGISTICS" for lot in row.lots
        )
        candidates.append(
            (
                (
                    0 if urgency == "PAST_DUE" else 2,
                    due_date,
                    row.modality,
                    row.row_id,
                ),
                {
                    "urgency": urgency,
                    "title": (
                        f"Clear {uncleared_lot_count} {row.modality} "
                        f"lot{'s' if uncleared_lot_count != 1 else ''} for Logistics"
                    ),
                    "reason": (
                        f"{row.order_reference}: "
                        f"{row.production_remaining_quantity:,} circuits are on the dock "
                        "and remain assigned to Flex production."
                    ),
                    "due_date": due_date,
                    "owner_workspace": "Logistics Handoff",
                    "href": f"/labs/flex/ptl-suite#flex-handoff-{row.row_id}",
                },
            )
        )

    awaiting_hla = tuple(
        lot
        for lot in panel_flex_lots
        if lot.lifecycle_state == "COMPLETE_AWAITING_HLA_TRANSFER"
    )
    if awaiting_hla:
        oldest_completion = min(
            lot.completed_at or lot.updated_at for lot in awaiting_hla
        )
        modalities = sorted({lot.display_modality for lot in awaiting_hla})
        candidates.append(
            (
                (2, oldest_completion.date(), "Panel Flex", "HLA"),
                {
                    "urgency": "ACTION_REQUIRED",
                    "title": (
                        f"Transfer {len(awaiting_hla)} completed Panel Flex "
                        f"lot{'s' if len(awaiting_hla) != 1 else ''} to HLA"
                    ),
                    "reason": (
                        f"{sum(lot.quantity for lot in awaiting_hla):,} circuits across "
                        f"{', '.join(modalities)} await the controlled PTL handoff record."
                    ),
                    "due_date": None,
                    "owner_workspace": "Panel Flex & HLA",
                    "href": "/labs/flex/ptl-suite#ptl-panel-flex",
                },
            )
        )

    return _priority_result(
        queue_scope="PTL",
        generated_at=shipment_readiness.generated_at,
        source_filename=shipment_readiness.source_revision_filename,
        source_revision_sha256=shipment_readiness.source_revision_sha256,
        source_ids=(
            "living-os",
            "logistics-handoff-workflow",
            "panel-flex-workflow",
        ),
        candidates=candidates,
        limit=limit,
    )


def _priority_result(
    *,
    queue_scope: Literal["OPERATOR", "PTL"],
    generated_at: datetime,
    source_filename: str,
    source_revision_sha256: str,
    source_ids: tuple[
        Literal[
            "living-os",
            "accepted-wip",
            "logistics-handoff-workflow",
            "panel-flex-workflow",
        ],
        ...,
    ],
    candidates: list[tuple[tuple[int, date, str, str], dict[str, object]]],
    limit: int,
) -> FlexPrioritiesResult:
    """Rank one audience's candidates without crossing role boundaries."""

    selected = sorted(candidates, key=lambda candidate: candidate[0])[:limit]
    items = tuple(
        FlexPriorityItem(rank=rank, **values)
        for rank, (_sort_key, values) in enumerate(selected, start=1)
    )
    return FlexPrioritiesResult(
        queue_scope=queue_scope,
        generated_at=generated_at,
        source_filename=source_filename,
        source_revision_sha256=source_revision_sha256,
        source_ids=source_ids,
        total_action_count=len(candidates),
        items=items,
    )

_PANEL_LOTS = TypeAdapter(tuple[InternalPanelFlexLotState, ...])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scope", choices=("operator", "program-lead"))
    parser.add_argument("input", type=Path, help="Saved JSON report from the matching upstream tool")
    parser.add_argument("--panel-lots", type=Path, help="Optional JSON array of saved panel lot states")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    if args.panel_lots is not None and args.scope != "program-lead":
        parser.error("--panel-lots requires program-lead scope")
    try:
        saved = _read_json(args.input)
        if args.scope == "operator":
            result = build_flex_priorities(
                OrderNeedsResult.model_validate(saved), as_of=args.as_of, limit=args.limit,
            )
        else:
            panel = _PANEL_LOTS.validate_python(_read_json(args.panel_lots)) if args.panel_lots else ()
            result = build_ptl_priorities(
                ShipmentReadinessResult.model_validate(saved), panel_flex_lots=panel,
                as_of=args.as_of, limit=args.limit,
            )
    except (ValueError, TypeError):
        print("Invalid follow-up input. Check the report, scope, date and limit.", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((result.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
