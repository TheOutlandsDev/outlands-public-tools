"""Original event identity and allocation assertions with fictional lot IDs."""

import pytest

from outbound_event_identity_checker import (
    OutboundTransactionConflict,
    outbound_event_identity,
    parse_lot_allocations,
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


def test_outbound_lot_allocations_are_bounded_and_unambiguous() -> None:
    assert parse_lot_allocations("DEMO-LOT-A DEMO-LOT-B", "180 120") == (
        ("DEMO-LOT-A", 180),
        ("DEMO-LOT-B", 120),
    )
    with pytest.raises(OutboundTransactionConflict, match="same non-zero"):
        parse_lot_allocations("DEMO-LOT-A DEMO-LOT-B", "300")
    with pytest.raises(OutboundTransactionConflict, match="unique"):
        parse_lot_allocations("DEMO-LOT-A DEMO-LOT-A", "180 120")
    with pytest.raises(OutboundTransactionConflict, match="whole number"):
        parse_lot_allocations("DEMO-LOT-A", "300.5")
