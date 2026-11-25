"""Preview the cancellation of a saved lot-start reservation."""

import argparse
import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_INPUT_BYTES = 1024 * 1024


class PreviewError(ValueError):
    """A safe diagnostic for invalid saved input or an invalid transition."""


class LotStartCancellationCommand(BaseModel):
    """Validate the reason for a previewed cancellation."""

    reason: str = Field(min_length=8, max_length=500)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReservedLot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence_in_request: int = Field(strict=True, ge=1, le=100)
    lot_id: str = Field(min_length=1, max_length=40, pattern=r"^\S+$")
    reservation_status: Literal["RESERVED", "FINALIZED", "CANCELLED", "EXPIRED"]


class ReservationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    source_request_key: str = Field(min_length=1, max_length=160)
    request_status: Literal["DRAFT", "RESERVED", "FINALIZED", "CANCELLED"]
    cancellation_reason: str | None = Field(default=None, max_length=500)
    reservations: tuple[ReservedLot, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_reservations(self):
        identities = {row.lot_id.casefold() for row in self.reservations}
        ordinals = {row.sequence_in_request for row in self.reservations}
        if len(identities) != len(self.reservations) or len(ordinals) != len(self.reservations):
            raise ValueError("Lot identities and sequence positions must be unique.")
        return self


def preview_cancellation(
    snapshot: ReservationSnapshot, command: LotStartCancellationCommand
) -> dict:
    if snapshot.request_status not in {"RESERVED", "CANCELLED"}:
        raise PreviewError("Only a reserved request can be cancelled.")
    if not snapshot.reservations:
        raise PreviewError("The saved request has no reserved lot identities.")

    replay = snapshot.request_status == "CANCELLED"
    reservations = tuple(sorted(snapshot.reservations, key=lambda row: row.sequence_in_request))
    event = None
    updates = {"reservations": reservations}
    if not replay:
        updates = {
            "reservations": tuple(
                row.model_copy(update={"reservation_status": "CANCELLED"})
                for row in reservations
            ),
            "request_status": "CANCELLED",
            "cancellation_reason": command.reason,
        }
        event = {
            "request_id": str(snapshot.request_id),
            "event_type": "CANCELLED",
            "detail": {"reason": command.reason},
        }

    return {
        "status": "PASS",
        "preview_only": True,
        "prior_request_status": snapshot.request_status,
        "reservation": snapshot.model_copy(update=updates).model_dump(mode="json"),
        "non_reusable_lot_ids": [row.lot_id for row in reservations],
        "idempotent_replay": replay,
        "proposed_audit_event": event,
        "database_writes": False,
        "mes_writes": False,
    }


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def read_model(path, model, label):
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise PreviewError(f"Unable to read {label} JSON.") from None

    if len(payload) > MAX_INPUT_BYTES:
        raise PreviewError(f"The {label} JSON exceeds the 1 MiB limit.")

    try:
        data = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)
        return model.model_validate(data)
    except (ValueError, RecursionError):
        raise PreviewError(f"Invalid {label} JSON.") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reservation", type=Path, help="Saved reservation JSON")
    parser.add_argument("cancellation", type=Path, help="JSON object with a reason")
    args = parser.parse_args()
    try:
        snapshot = read_model(args.reservation, ReservationSnapshot, "reservation")
        command = read_model(args.cancellation, LotStartCancellationCommand, "cancellation")
        result = preview_cancellation(snapshot, command)
    except PreviewError as exc:
        parser.exit(2, f"{exc}\n")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
