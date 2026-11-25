"""Adapt the original non-reuse and cancellation audit assertions to saved records."""

import json
from pathlib import Path

from lot_reservation_cancellation import (
    LotStartCancellationCommand,
    ReservationSnapshot,
    preview_cancellation,
)
from reference_lot_sequence import propose_standard_lot_ids

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/reservation.json"


def test_cancelled_or_pending_identifiers_remain_non_reusable():
    snapshot = ReservationSnapshot.model_validate_json(EXAMPLE.read_bytes())
    result = preview_cancellation(snapshot, LotStartCancellationCommand(reason="Fictional change"))
    assert propose_standard_lot_ids(
        lot_prefix="DEMO-01-",
        observed_lot_ids=["DEMO-01-AAAA", *result["non_reusable_lot_ids"]],
        count=1,
    ) == ("DEMO-01-AAAD",)


def test_reservation_preview_preserves_cancelled_identity_and_audit_history():
    original = json.loads(EXAMPLE.read_bytes())
    snapshot = ReservationSnapshot.model_validate(original)
    first = preview_cancellation(snapshot, LotStartCancellationCommand(reason="  Fictional change  "))
    assert snapshot.model_dump(mode="json") == original
    assert first["reservation"]["request_id"] == original["request_id"]
    assert first["reservation"]["source_request_key"] == original["source_request_key"]
    assert first["reservation"]["request_status"] == "CANCELLED"
    assert first["reservation"]["cancellation_reason"] == "Fictional change"
    assert first["reservation"]["reservations"] == [
        {**row, "reservation_status": "CANCELLED"}
        for row in reversed(original["reservations"])
    ]
    assert first["proposed_audit_event"] == {
        "request_id": original["request_id"],
        "event_type": "CANCELLED",
        "detail": {"reason": "Fictional change"},
    }
    assert first["idempotent_replay"] is False

    replay = preview_cancellation(
        ReservationSnapshot.model_validate(first["reservation"]),
        LotStartCancellationCommand(reason="Another fictional change"),
    )
    assert replay["reservation"] == first["reservation"]
    assert replay["non_reusable_lot_ids"] == first["non_reusable_lot_ids"]
    assert replay["idempotent_replay"] is True
    assert replay["proposed_audit_event"] is None
    assert first["database_writes"] is replay["database_writes"] is False
    assert first["mes_writes"] is replay["mes_writes"] is False
