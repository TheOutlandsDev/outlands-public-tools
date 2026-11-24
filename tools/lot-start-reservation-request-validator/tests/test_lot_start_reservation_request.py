import pytest
from pydantic import ValidationError

from lot_start_reservation_request import (
    LotIdentityEvidence,
    LotStartCandidateRequest,
    LotStartReservationCommand,
    identity_source_sha256,
)


def test_reservation_command_and_evidence_hash_are_bounded_and_deterministic() -> None:
    evidence = LotIdentityEvidence(
        current_wip=[" demo-aaa1 "],
        historical_inventory=["DEMO-AAAZ"],
        last_lot_registry=[],
        pending_reservations=[],
        cancelled_reservations=[],
        mes_identity_lookup=[],
        mes_lookup_status="NOT_AVAILABLE",
    )
    assert evidence.current_wip == ["DEMO-AAA1"]
    assert identity_source_sha256(evidence) == identity_source_sha256(
        LotIdentityEvidence.model_validate(evidence.model_dump())
    )
    command = LotStartReservationCommand(
        source_request_key="test-lot-start-001",
        candidate=LotStartCandidateRequest(
            modality="DEMO01",
            uncovered_demand=100,
            identity_evidence=evidence,
        ),
    )
    assert command.candidate.uncovered_demand == 100

    with pytest.raises(ValidationError):
        LotStartReservationCommand(
            source_request_key="test-lot-start-002",
            candidate=LotStartCandidateRequest(
                modality="DEMO01",
                uncovered_demand=0,
                identity_evidence=evidence,
            ),
        )
