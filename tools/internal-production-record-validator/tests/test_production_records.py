"""Five original direct production record tests using fictional product mappings."""

from datetime import date
from pathlib import Path
import sys
from uuid import UUID

import pytest

from production_records import (
    ApprovedProducts, CompletionRecord, InternalDemandCreateCommand, InternalDemandRevisionCommand,
    InternalLotBulkTransferCommand, InternalLotCompletionCommand, InternalLotTransferCommand,
    InternalLotTransferSelection, InternalPanelFlexLotEvidence, operational_event_identity,
    resolve_internal_product,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_records import DEMAND_ID, EVIDENCE, PRODUCTS


@pytest.fixture
def approved():
    return ApprovedProducts.model_validate(PRODUCTS)


def test_internal_operational_identity_is_deterministic_and_revision_specific():
    first = operational_event_identity("MANUAL_INTERNAL_DEMAND", DEMAND_ID, 1)
    replay = operational_event_identity("MANUAL_INTERNAL_DEMAND", DEMAND_ID, 1)
    revised = operational_event_identity("MANUAL_INTERNAL_DEMAND", DEMAND_ID, 2)
    assert first == replay
    assert first != revised
    assert len(first) == 64


def test_internal_product_resolution_covers_exactly_five_modalities(approved):
    assert resolve_internal_product("DEM01", approved).display_modality == "XDEM01"
    assert resolve_internal_product("XDEM02", approved).canonical_modality == "DEM02"
    assert resolve_internal_product("XDEM03", approved).assembly == "9910003"
    assert resolve_internal_product("XDEM04", approved).assembly == "9910004"
    assert resolve_internal_product("DEM05", approved).display_modality == "XDEM05"
    with pytest.raises(ValueError, match="not configured"):
        resolve_internal_product("OUTSIDE", approved)


def test_internal_demand_commands_are_bounded_and_fail_closed(approved):
    fields = dict(demand_id=UUID(DEMAND_ID), modality="XDEM02", requested_quantity=36,
                  needed_by=date(2031, 3, 2), demand_status="DRAFT", revision_comment="Fictional demand")
    command = InternalDemandCreateCommand.model_validate(fields, context=approved)
    assert command.requested_quantity == 36
    with pytest.raises(ValueError):
        InternalDemandCreateCommand.model_validate({**fields, "modality": "OUTSIDE"}, context=approved)
    with pytest.raises(ValueError):
        InternalDemandRevisionCommand(
            expected_revision=1, requested_quantity=0, needed_by=date(2031, 3, 2),
            demand_status="ACTIVE", revision_comment="Invalid quantity",
        )


def test_completion_evidence_requires_matching_product_and_snapshot(approved):
    evidence = InternalPanelFlexLotEvidence.model_validate(EVIDENCE, context=approved)
    command = InternalLotCompletionCommand(
        completion_revision=1, source_sha256="a" * 64, completion_comment="Fictional completion test",
    )
    assert evidence.quantity == 18
    assert command.completion_revision == 1
    with pytest.raises(ValueError, match="product contract"):
        InternalPanelFlexLotEvidence.model_validate(
            {**evidence.model_dump(mode="python"), "assembly": "9910002"}, context=approved,
        )
    with pytest.raises(ValueError, match="source snapshot"):
        CompletionRecord.model_validate(
            dict(kind="completion", evidence=EVIDENCE,
                 command={**command.model_dump(mode="python"), "source_sha256": "b" * 64}),
            context=approved,
        )


def test_transfer_command_is_bounded_and_consumption_is_not_an_action(approved):
    command = InternalLotTransferCommand(expected_row_version=2, transfer_comment="Fictional transfer")
    assert command.expected_row_version == 2
    with pytest.raises(ValueError):
        InternalLotTransferCommand(expected_row_version=0, transfer_comment="Invalid row version")
    with pytest.raises(ValueError):
        InternalLotTransferCommand.model_validate(
            dict(expected_row_version=2, transfer_comment="Transfer", consumed_by_hla=True),
        )

    a = InternalLotTransferSelection(lot_id="XDEM01_ALPHA", expected_row_version=2)
    b = InternalLotTransferSelection(lot_id="XDEM02_BETA", expected_row_version=4)
    batch = InternalLotBulkTransferCommand.model_validate(
        dict(lots=(a, b), transfer_comment="Fictional reviewed lots"), context=approved,
    )
    assert [lot.lot_id for lot in batch.lots] == ["XDEM01_ALPHA", "XDEM02_BETA"]
    with pytest.raises(ValueError, match="only once"):
        InternalLotBulkTransferCommand.model_validate(
            dict(lots=(a, a), transfer_comment="Duplicate lots"), context=approved,
        )
    with pytest.raises(ValueError):
        InternalLotBulkTransferCommand.model_validate(
            {**batch.model_dump(mode="python"), "consumed_by_hla": True}, context=approved,
        )
