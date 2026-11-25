from datetime import date
from pathlib import Path

import pytest

from order_demand_replay import (
    AutomaticLotStartConflict,
    AutomaticLotStartError,
    AutomaticLotStartLedger,
    OrderState,
    load_automatic_lot_start_configuration,
)


CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples/rules.json"
SOURCE_REVISION = "a" * 64


def configuration():
    return load_automatic_lot_start_configuration(CONFIG_PATH)


def order(
    *,
    order_id: str = "DEMO-ORDER-0001",
    version: int = 1,
    part_number: str = "DEMO-PART-04",
    quantity: int = 48,
    shipped: int = 0,
    cancelled: bool = False,
) -> OrderState:
    return OrderState(
        order_id=order_id,
        row_version=version,
        source_revision_sha256=SOURCE_REVISION,
        part_number=part_number,
        ordered_quantity=quantity,
        accepted_ship_quantity=shipped,
        requested_ship_date=date(2030, 1, 20),
        cancelled=cancelled,
    )


def test_all_configured_products_use_their_declared_start_quantities() -> None:
    products = {item.modality: item for item in configuration().configured_products}
    expected_products = {
        "DEMO01", "DEMO04", "DEMO05", "DEMO06", "DEMO07", "DEMO08",
        "DEMO09", "DEMO10", "DEMO11", "DEMO12", "DEMO13",
    }
    actual_products = {
        item.modality
        for item in configuration().configured_products
        if item.lot_prefix.startswith("LOT")
    }
    assert actual_products == expected_products
    assert products["DEMO01"].start_quantity == 36
    assert products["DEMO11"].start_quantity == 36
    expected_48 = {
        "DEMO04", "DEMO05", "DEMO06", "DEMO07", "DEMO08",
        "DEMO09", "DEMO10", "DEMO12", "DEMO13",
    }
    assert expected_48 <= products.keys()
    assert all(products[modality].start_quantity == 48 for modality in expected_48)
    assert products["DEMO11"].status == "DEMO_REVIEWED_EXCEPTION"


def test_exception_product_full_size_order_recommends_one_lot() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    result = ledger.ingest(order(part_number="DEMO-PART-11", quantity=36))

    assert result.event is not None
    assert result.event.modality == "DEMO11"
    assert result.event.start_quantity == 36
    assert result.event.current_recommended_lots == 1
    assert result.event.recommendation_delta == 1


def test_new_order_creates_one_backfill_recommendation_exactly_once() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    first = ledger.ingest(order())
    replay = ledger.ingest(order())

    assert first.event is not None
    assert first.event.event_type == "CREATE"
    assert first.event.demand_delta == 48
    assert first.event.recommendation_delta == 1
    assert first.event.current_recommended_lots == 1
    assert first.event.database_writes is False
    assert first.event.mes_writes is False
    assert replay.applied is False
    assert replay.replay_ignored is True
    assert replay.event is None
    assert len(ledger.events) == 1


def test_order_increase_changes_only_incremental_modality_recommendation() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order(quantity=48))
    result = ledger.ingest(order(version=2, quantity=96))

    assert result.event is not None
    assert result.event.event_type == "INCREASE"
    assert result.event.demand_delta == 48
    assert result.event.previous_recommended_lots == 1
    assert result.event.current_recommended_lots == 2
    assert result.event.recommendation_delta == 1


def test_order_decrease_reduces_uncommitted_calculated_requirement() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order(quantity=96))
    result = ledger.ingest(order(version=2, quantity=48))

    assert result.event is not None
    assert result.event.event_type == "DECREASE"
    assert result.event.demand_delta == -48
    assert result.event.recommendation_delta == -1


def test_accepted_shipment_reduces_remaining_demand_without_duplicate_event() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order(quantity=96))
    shipped = order(version=2, quantity=96, shipped=48)
    first = ledger.ingest(shipped)
    replay = ledger.ingest(shipped)

    assert first.event is not None
    assert first.event.event_type == "SHIPMENT"
    assert first.event.current_remaining_quantity == 48
    assert first.event.recommendation_delta == -1
    assert replay.replay_ignored is True
    assert len(ledger.events) == 2


def test_fully_shipped_order_zeroes_remaining_demand_without_duplicate_event() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order(quantity=48))
    shipped = order(version=2, quantity=48, shipped=48)
    first = ledger.ingest(shipped)
    replay = ledger.ingest(shipped)

    assert first.event is not None
    assert first.event.event_type == "SHIPMENT"
    assert first.event.current_remaining_quantity == 0
    assert first.event.current_recommended_lots == 0
    assert first.event.recommendation_delta == -1
    assert replay.replay_ignored is True
    assert len(ledger.events) == 2


def test_cancellation_zeroes_remaining_demand_once() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order())
    cancelled = order(version=2, cancelled=True)
    result = ledger.ingest(cancelled)
    replay = ledger.ingest(cancelled)

    assert result.event is not None
    assert result.event.event_type == "CANCEL"
    assert result.event.current_remaining_quantity == 0
    assert result.event.recommendation_delta == -1
    assert replay.replay_ignored is True


def test_partial_orders_are_aggregated_before_whole_lot_rounding() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    first = ledger.ingest(order(order_id="DEMO-PARTIAL-0001", quantity=24))
    second = ledger.ingest(order(order_id="DEMO-PARTIAL-0002", quantity=24))

    assert first.event is not None and first.event.recommendation_delta == 1
    assert second.event is not None
    assert second.event.current_modality_demand == 48
    assert second.event.current_recommended_lots == 1
    assert second.event.recommendation_delta == 0


def test_non_demand_edit_updates_state_without_recommendation_event() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order())
    updated = order(version=2).model_copy(
        update={"source_revision_sha256": "b" * 64}
    )
    result = ledger.ingest(updated)

    assert result.applied is True
    assert result.state_changed_without_demand_change is True
    assert result.event is None
    assert len(ledger.events) == 1


def test_conflicting_same_version_and_older_version_fail_closed() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    ledger.ingest(order(quantity=48, version=2))
    with pytest.raises(AutomaticLotStartConflict, match="same order row version"):
        ledger.ingest(order(quantity=96, version=2))
    with pytest.raises(AutomaticLotStartConflict, match="older order row version"):
        ledger.ingest(order(quantity=48, version=1))


def test_exact_replay_of_an_older_applied_version_fails_closed() -> None:
    ledger = AutomaticLotStartLedger(configuration())
    original = order(quantity=48, version=1)
    ledger.ingest(original)
    ledger.ingest(order(quantity=96, version=2))

    with pytest.raises(AutomaticLotStartConflict, match="older order row version"):
        ledger.ingest(original)


@pytest.mark.parametrize("part_number", ["DEMO-BLOCKED-1", "DEMO-BLOCKED-2", "DEMO-BLOCKED-3", "DEMO-BLOCKED-4"])
def test_unapproved_start_quantities_fail_closed(part_number: str) -> None:
    ledger = AutomaticLotStartLedger(configuration())
    with pytest.raises(AutomaticLotStartError, match="fail closed"):
        ledger.ingest(order(part_number=part_number))


def test_accepted_ship_quantity_cannot_exceed_order_quantity() -> None:
    with pytest.raises(ValueError, match="Accepted ship quantity"):
        order(quantity=36, shipped=37)
