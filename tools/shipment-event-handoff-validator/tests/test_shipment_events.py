"""The three original event and handoff cases using fictional records."""

from shipment_events import (
    FlexReadyForLogisticsCommand,
    FlexReturnToFlexCommand,
    flex_handoff_event_identity,
    outbound_event_identity,
)


def test_outbound_identity_is_deterministic_and_row_version_specific() -> None:
    revision = "a" * 64
    row_id = "b" * 24
    first = outbound_event_identity(revision, row_id, 3)
    replay = outbound_event_identity(revision, row_id, 3)
    revised = outbound_event_identity(revision, row_id, 4)

    assert first == replay
    assert first != revised
    assert len(first) == 64


def test_logistics_handoff_identity_is_lot_action_and_version_specific() -> None:
    values = {
        "revision_sha256": "a" * 64,
        "row_id": "b" * 24,
        "lot_id": "DEMO-LOT-01",
        "quantity": 12,
        "action": "READY_FOR_LOGISTICS",
        "state_version": 1,
    }
    first = flex_handoff_event_identity(**values)
    assert first == flex_handoff_event_identity(**values)
    assert first != flex_handoff_event_identity(
        **{**values, "action": "RETURN_TO_FLEX", "state_version": 2}
    )


def test_logistics_handoff_commands_require_explicit_lots_and_return_reason() -> None:
    ready = FlexReadyForLogisticsCommand(
        source_revision_sha256="a" * 64,
        expected_order_version=3,
        lots=(
            {"lot_id": "DEMO-LOT-01", "quantity": 12},
            {"lot_id": "DEMO-LOT-02", "quantity": 8},
        ),
    )
    assert sum(lot.quantity for lot in ready.lots) == 20

    returned = FlexReturnToFlexCommand(
        source_revision_sha256="a" * 64,
        expected_order_version=4,
        lots=({"lot_id": "DEMO-LOT-01", "expected_state_version": 1},),
        reason="Fictional lot requires review",
    )
    assert returned.reason == "Fictional lot requires review"
