import pytest

from bulk_logistics_handoff import BulkReadyCommand, BulkReturnCommand


def test_bulk_commands_are_bounded_and_reject_duplicate_orders() -> None:
    ready_order = {
        "row_id": "b" * 24,
        "source_revision_sha256": "a" * 64,
        "expected_order_version": 3,
        "lots": ({"lot_id": "DEMO-LOT-01", "quantity": 180},),
    }
    ready = BulkReadyCommand(
        orders=(
            ready_order,
            {
                **ready_order,
                "row_id": "c" * 24,
                "lots": ({"lot_id": "DEMO-LOT-02", "quantity": 120},),
            },
        ),
        comment="Demo reviewer checked this batch.",
    )
    assert len(ready.orders) == 2
    assert sum(len(order.lots) for order in ready.orders) == 2

    with pytest.raises(ValueError, match="Each selected order"):
        BulkReadyCommand(orders=(ready_order, ready_order))

    returned = BulkReturnCommand(
        orders=(
            {
                "row_id": "b" * 24,
                "source_revision_sha256": "a" * 64,
                "expected_order_version": 4,
                "lots": (
                    {"lot_id": "DEMO-LOT-01", "expected_state_version": 1},
                ),
            },
        ),
        reason="Demo reviewer requested rework.",
    )
    assert returned.reason == "Demo reviewer requested rework."
