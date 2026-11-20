"""Project shipment readiness from saved order and lot handoff records."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator



class OSGridOrder(BaseModel):
    """Saved order fields consumed by the readiness projection."""

    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    source_sheet: Literal["C", "P"]
    source_row: int = Field(ge=4, le=500)
    part_number: str = Field(min_length=1, max_length=40)
    modality: str = Field(min_length=1, max_length=40)
    quantity: int = Field(gt=0)
    flex_ptl_commit_date: date
    status: str = Field(min_length=1, max_length=80)
    customer_or_oracle_po: str | None = Field(default=None, max_length=80)
    po_line: str | None = Field(default=None, max_length=30)
    ship_quantity: int | None = Field(default=None, ge=0)
    dock_date: date | None = None
    lot_ids: str | None = Field(default=None, max_length=2000)
    lot_quantities: str | None = Field(default=None, max_length=2000)
    row_version: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class FlexLogisticsHandoffLotState(BaseModel):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    lot_id: str
    quantity: int = Field(gt=0)
    lifecycle_state: Literal["READY_FOR_LOGISTICS", "RETURNED_TO_FLEX"]
    state_version: int = Field(gt=0)
    order_row_version: int = Field(gt=0)
    last_event_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    ready_at: datetime
    ready_by: str
    ready_comment: str | None = None
    returned_at: datetime | None = None
    returned_by: str | None = None
    return_reason: str | None = None
    updated_at: datetime

    model_config = ConfigDict(frozen=True, extra="forbid")


class OutboundTransactionConflict(ValueError):
    """Saved lot allocations are ambiguous or invalid."""


def parse_lot_allocations(lot_ids: str, lot_quantities: str) -> tuple[tuple[str, int], ...]:
    """Parse the governed O&S lot columns and reject ambiguous allocation evidence."""

    identifiers = tuple(item for item in re.split(r"[\s,;]+", lot_ids.strip()) if item)
    raw_quantities = tuple(
        item for item in re.split(r"[\s,;]+", lot_quantities.strip()) if item
    )
    if not identifiers or len(identifiers) != len(raw_quantities):
        raise OutboundTransactionConflict(
            "Lot IDs and lot quantities must contain the same non-zero number of values."
        )
    if len({item.casefold() for item in identifiers}) != len(identifiers):
        raise OutboundTransactionConflict("Outbound lot IDs must be unique.")
    try:
        quantities = tuple(int(value) for value in raw_quantities)
    except ValueError as exc:
        raise OutboundTransactionConflict(
            "Every outbound lot quantity must be a whole number."
        ) from exc
    if any(value <= 0 for value in quantities):
        raise OutboundTransactionConflict(
            "Every outbound lot quantity must be greater than zero."
        )
    return tuple(zip(identifiers, quantities, strict=True))


ShipmentReadinessState = Literal[
    "AWAITING_DOCK",
    "LOT_EVIDENCE_REQUIRED",
    "DOCKED_AWAITING_FLEX_CLEARANCE",
    "PARTIALLY_READY_FOR_LOGISTICS",
    "READY_FOR_LOGISTICS",
    "SHIPPING_EVIDENCE_RECORDED",
]

STATE_LABELS: dict[str, str] = {
    "AWAITING_DOCK": "In Flex production",
    "LOT_EVIDENCE_REQUIRED": "Lot evidence required",
    "DOCKED_AWAITING_FLEX_CLEARANCE": "On dock · Flex clearance required",
    "PARTIALLY_READY_FOR_LOGISTICS": "Partially ready for Logistics",
    "READY_FOR_LOGISTICS": "Flex complete · Awaiting Logistics",
    "SHIPPING_EVIDENCE_RECORDED": "Shipping evidence recorded",
}

STATE_ORDER = {
    "DOCKED_AWAITING_FLEX_CLEARANCE": 0,
    "PARTIALLY_READY_FOR_LOGISTICS": 1,
    "LOT_EVIDENCE_REQUIRED": 2,
    "READY_FOR_LOGISTICS": 3,
    "AWAITING_DOCK": 4,
    "SHIPPING_EVIDENCE_RECORDED": 5,
}


class ShipmentReadinessLot(BaseModel):
    lot_id: str
    quantity: int = Field(gt=0)
    lifecycle_state: Literal[
        "NOT_READY", "READY_FOR_LOGISTICS", "RETURNED_TO_FLEX"
    ]
    state_version: int | None = Field(default=None, gt=0)
    ready_at: datetime | None = None
    ready_by: str | None = None
    return_reason: str | None = None

    model_config = ConfigDict(frozen=True)


class ShipmentReadinessRow(BaseModel):
    """One order-level handoff projection with individual lot controls."""

    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    part_number: str
    modality: str
    customer_or_oracle_po: str | None
    po_line: str | None
    source_sheet: Literal["C", "P"]
    source_row: int = Field(ge=4, le=500)
    quantity: int = Field(gt=0)
    unshipped_quantity: int = Field(ge=0)
    ready_for_logistics_quantity: int = Field(ge=0)
    production_remaining_quantity: int = Field(ge=0)
    commit_date: str
    dock_date: str | None
    order_row_version: int | None = Field(default=None, gt=0)
    lots: tuple[ShipmentReadinessLot, ...] = ()
    readiness_state: ShipmentReadinessState
    readiness_label: str
    missing_fields: tuple[str, ...] = ()
    can_mark_ready: bool = False
    can_return_to_flex: bool = False
    priority_eligible: bool
    logistics_mes_status: Literal[
        "NOT_READY_FOR_LOGISTICS",
        "AWAITING_AUTHORITATIVE_MES_EVIDENCE",
        "SHIPPING_RECORDED",
    ]
    mes_transaction_recorded: Literal[False] = False

    model_config = ConfigDict(frozen=True)

    @property
    def order_reference(self) -> str:
        """Identify the O&S line even when its PO or line number is missing."""

        reference = [f"PO {(self.customer_or_oracle_po or '').strip() or 'not recorded'}"]
        if line := (self.po_line or "").strip():
            reference.append(f"Line {line}")
        reference.append(f"O&S {self.source_sheet}:{self.source_row}")
        return " · ".join(reference)


class ShipmentReadinessResult(BaseModel):
    """Bounded Flex-to-Logistics handoff response with source provenance."""

    workflow_status: Literal["DEVELOPMENT_CONTROLLED_HANDOFF"] = (
        "DEVELOPMENT_CONTROLLED_HANDOFF"
    )
    generated_at: datetime
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_revision_filename: str
    source_revision_status: str
    source_row_count: int = Field(ge=0, le=1000)
    filtered_row_count: int = Field(ge=0, le=200)
    selected_search: str
    selected_readiness: str
    readiness_counts: dict[str, int]
    ready_quantity: int = Field(ge=0)
    production_remaining_quantity: int = Field(ge=0)
    rows: tuple[ShipmentReadinessRow, ...] = Field(max_length=200)
    database_writes: Literal[False] = False
    mes_transaction_recorded: Literal[False] = False
    shipment_recorded: Literal[False] = False

    model_config = ConfigDict(frozen=True)


def _project(
    order: OSGridOrder,
    *,
    handoff_states: tuple[FlexLogisticsHandoffLotState, ...],
) -> ShipmentReadinessRow:
    state_by_lot = {state.lot_id.casefold(): state for state in handoff_states}
    missing_fields: tuple[str, ...] = ()
    try:
        allocations = parse_lot_allocations(
            str(order.lot_ids or ""), str(order.lot_quantities or "")
        )
    except OutboundTransactionConflict:
        allocations = ()
        missing_fields = ("matching lot IDs and lot quantities",)

    lots: list[ShipmentReadinessLot] = []
    for lot_id, quantity in allocations:
        state = state_by_lot.get(lot_id.casefold())
        lifecycle = state.lifecycle_state if state is not None else "NOT_READY"
        lots.append(
            ShipmentReadinessLot(
                lot_id=lot_id,
                quantity=quantity,
                lifecycle_state=lifecycle,
                state_version=state.state_version if state is not None else None,
                ready_at=state.ready_at if state is not None else None,
                ready_by=state.ready_by if state is not None else None,
                return_reason=state.return_reason if state is not None else None,
            )
        )

    accepted_ship_quantity = min(order.quantity, order.ship_quantity or 0)
    unshipped_quantity = max(0, order.quantity - accepted_ship_quantity)
    ready_quantity = min(
        unshipped_quantity,
        sum(
            lot.quantity
            for lot in lots
            if lot.lifecycle_state == "READY_FOR_LOGISTICS"
        ),
    )
    production_remaining = max(0, unshipped_quantity - ready_quantity)
    if order.status == "Shipped":
        readiness_state = "SHIPPING_EVIDENCE_RECORDED"
        logistics_mes_status = "SHIPPING_RECORDED"
    elif order.dock_date is None:
        readiness_state = "AWAITING_DOCK"
        logistics_mes_status = "NOT_READY_FOR_LOGISTICS"
    elif not allocations:
        readiness_state = "LOT_EVIDENCE_REQUIRED"
        logistics_mes_status = "NOT_READY_FOR_LOGISTICS"
    elif ready_quantity == 0:
        readiness_state = "DOCKED_AWAITING_FLEX_CLEARANCE"
        logistics_mes_status = "NOT_READY_FOR_LOGISTICS"
    elif production_remaining:
        readiness_state = "PARTIALLY_READY_FOR_LOGISTICS"
        logistics_mes_status = "AWAITING_AUTHORITATIVE_MES_EVIDENCE"
    else:
        readiness_state = "READY_FOR_LOGISTICS"
        logistics_mes_status = "AWAITING_AUTHORITATIVE_MES_EVIDENCE"

    actionable = order.status != "Shipped" and order.dock_date is not None
    return ShipmentReadinessRow(
        row_id=order.row_id,
        part_number=order.part_number,
        modality=order.modality,
        customer_or_oracle_po=order.customer_or_oracle_po,
        po_line=order.po_line,
        source_sheet=order.source_sheet,
        source_row=order.source_row,
        quantity=order.quantity,
        unshipped_quantity=unshipped_quantity,
        ready_for_logistics_quantity=ready_quantity,
        production_remaining_quantity=production_remaining,
        commit_date=order.flex_ptl_commit_date.isoformat(),
        dock_date=order.dock_date.isoformat() if order.dock_date else None,
        order_row_version=order.row_version,
        lots=tuple(lots),
        readiness_state=readiness_state,
        readiness_label=STATE_LABELS[readiness_state],
        missing_fields=missing_fields,
        can_mark_ready=(
            actionable
            and order.row_version is not None
            and bool(allocations)
            and any(lot.lifecycle_state != "READY_FOR_LOGISTICS" for lot in lots)
        ),
        can_return_to_flex=(
            actionable
            and order.row_version is not None
            and any(lot.lifecycle_state == "READY_FOR_LOGISTICS" for lot in lots)
        ),
        priority_eligible=(order.status != "Shipped" and production_remaining > 0),
        logistics_mes_status=logistics_mes_status,
    )


def build_shipment_readiness(
    *,
    orders: tuple[OSGridOrder, ...],
    revision_sha256: str,
    revision_filename: str,
    revision_status: str,
    source_row_count: int,
    search: str | None = None,
    readiness: str | None = None,
    handoff_states: tuple[FlexLogisticsHandoffLotState, ...] = (),
) -> ShipmentReadinessResult:
    """Build the deterministic Flex dock handoff projection without writes."""

    states_by_row: dict[str, list[FlexLogisticsHandoffLotState]] = defaultdict(list)
    for state in handoff_states:
        states_by_row[state.row_id].append(state)
    rows = [
        _project(order, handoff_states=tuple(states_by_row.get(order.row_id, ())))
        for order in orders
        if order.modality.startswith(("COF", "CON"))
    ]
    normalized_search = " ".join((search or "").split()).casefold()
    selected_readiness = (readiness or "").strip().upper()

    if normalized_search:
        rows = [
            row
            for row in rows
            if normalized_search
            in " ".join(
                (
                    row.part_number,
                    row.modality,
                    row.customer_or_oracle_po or "",
                    " ".join(lot.lot_id for lot in row.lots),
                    row.readiness_label,
                )
            ).casefold()
        ]
    if selected_readiness:
        rows = [row for row in rows if row.readiness_state == selected_readiness]

    rows.sort(
        key=lambda row: (
            STATE_ORDER[row.readiness_state],
            row.commit_date,
            row.part_number,
            row.row_id,
        )
    )
    rows = rows[:200]
    readiness_counts = Counter(row.readiness_state for row in rows)
    return ShipmentReadinessResult(
        generated_at=datetime.now(UTC),
        source_revision_sha256=revision_sha256,
        source_revision_filename=revision_filename,
        source_revision_status=revision_status,
        source_row_count=source_row_count,
        filtered_row_count=len(rows),
        selected_search=search or "",
        selected_readiness=selected_readiness,
        readiness_counts=dict(sorted(readiness_counts.items())),
        ready_quantity=sum(row.ready_for_logistics_quantity for row in rows),
        production_remaining_quantity=sum(
            row.production_remaining_quantity for row in rows
        ),
        rows=tuple(rows),
    )

class SavedReadinessInput(BaseModel):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_filename: str = Field(min_length=1, max_length=240)
    revision_status: str = Field(min_length=1, max_length=80)
    source_row_count: int = Field(ge=0, le=1000)
    orders: tuple[OSGridOrder, ...] = Field(max_length=1000)
    handoff_states: tuple[FlexLogisticsHandoffLotState, ...] = Field(default=(), max_length=4000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_snapshot_identity(self) -> "SavedReadinessInput":
        order_ids = {order.row_id for order in self.orders}
        if len(order_ids) != len(self.orders):
            raise ValueError("Order identities must be unique")
        seen: set[tuple[str, str]] = set()
        for state in self.handoff_states:
            identity = (state.row_id, state.lot_id.casefold())
            if state.revision_sha256 != self.revision_sha256 or state.row_id not in order_ids:
                raise ValueError("Handoff state must reference an order in this revision")
            if identity in seen:
                raise ValueError("Handoff state must be unique per order and lot")
            seen.add(identity)
        return self


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
    parser.add_argument("input", type=Path, help="Local JSON with orders and saved lot handoff states")
    parser.add_argument("--search")
    parser.add_argument("--readiness", choices=STATE_ORDER)
    args = parser.parse_args()
    try:
        saved = SavedReadinessInput.model_validate(_read_json(args.input))
        report = build_shipment_readiness(
            orders=saved.orders,
            revision_sha256=saved.revision_sha256,
            revision_filename=saved.revision_filename,
            revision_status=saved.revision_status,
            source_row_count=saved.source_row_count,
            handoff_states=saved.handoff_states,
            search=args.search,
            readiness=args.readiness,
        )
    except ValueError:
        print("Invalid or unreadable readiness snapshot", file=sys.stderr)
        return 2
    sys.stdout.buffer.write((report.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
