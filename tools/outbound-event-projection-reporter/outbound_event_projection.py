"""Project unseen outbound events from saved shipment data into a field allowlist."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import re
import sys
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError


MAX_SOURCE_EVENTS = 500
HISTORY_COLUMNS = (
    "event_identity",
    "revision_sha256",
    "row_id",
    "order_row_version",
    "part_number",
    "modality",
    "order_quantity",
    "transacted_quantity",
    "lot_count",
    "lifecycle_state",
    "transacted_at",
    "projected_at",
    "projection_run_id",
)
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class OutboundProjectionError(ValueError):
    """The snapshot does not satisfy the offline projection contract."""


class OutboundTransactionConflict(OutboundProjectionError):
    """The lot allocation evidence is ambiguous."""


class OutboundTransactionState(BaseModel):
    revision_sha256: Digest
    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    event_identity: Digest
    order_row_version: int = Field(gt=0)
    part_number: str
    modality: str
    quantity: int = Field(gt=0)
    transacted_quantity: int = Field(gt=0)
    lot_ids: str
    lot_quantities: str
    carrier: str | None = None
    tracking_number: str | None = None
    lifecycle_state: Literal["TRANSACTED_FROM_FLEX"]
    transacted_at: AwareDatetime
    transacted_by: str | None = None
    transaction_comment: str | None = None

    model_config = ConfigDict(frozen=True, strict=True)


class SavedProjection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    events: tuple[OutboundTransactionState, ...]
    seen_event_ids: tuple[Digest, ...] = ()
    projected_at: AwareDatetime
    projection_run_id: UUID


class OutboundProjectionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    projection_run_id: UUID
    projected_at: datetime
    source_event_count: int
    new_event_count: int
    replayed_event_count: int
    source_latest_at: datetime | None
    rows: tuple[dict[str, object], ...]


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


def _history_row(
    state: OutboundTransactionState,
    *,
    projected_at: datetime,
    projection_run_id: UUID,
) -> list[object]:
    allocations = parse_lot_allocations(state.lot_ids, state.lot_quantities)
    return [
        state.event_identity,
        state.revision_sha256,
        state.row_id,
        state.order_row_version,
        state.part_number,
        state.modality,
        state.quantity,
        state.transacted_quantity,
        len(allocations),
        state.lifecycle_state,
        state.transacted_at,
        projected_at,
        projection_run_id,
    ]


def project_outbound_events(snapshot: SavedProjection) -> OutboundProjectionReport:
    """Project the unseen event IDs without changing the input or seen set."""
    states = snapshot.events
    if len(states) >= MAX_SOURCE_EVENTS:
        raise OutboundProjectionError("The outbound source reached the bounded projection limit.")
    if len({state.event_identity for state in states}) != len(states):
        raise OutboundProjectionError("The outbound source contains a duplicate event identity.")

    existing = set(snapshot.seen_event_ids)
    missing = [state for state in states if state.event_identity not in existing]
    projected = snapshot.projected_at.astimezone(UTC)
    run_id = snapshot.projection_run_id
    rows = tuple(
        dict(zip(HISTORY_COLUMNS, _history_row(
            state, projected_at=projected, projection_run_id=run_id,
        ), strict=True))
        for state in missing
    )

    return OutboundProjectionReport(
        projection_run_id=run_id,
        projected_at=projected,
        source_event_count=len(states),
        new_event_count=len(missing),
        replayed_event_count=len(states) - len(missing),
        source_latest_at=max((state.transacted_at for state in states), default=None),
        rows=rows,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved events and previously seen IDs in JSON")
    args = parser.parse_args()
    try:
        snapshot = SavedProjection.model_validate_json(args.snapshot.read_bytes())
        report = project_outbound_events(snapshot)
    except OutboundProjectionError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValidationError):
        print("The outbound event snapshot is unreadable or invalid.", file=sys.stderr)
        return 2

    print(report.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
