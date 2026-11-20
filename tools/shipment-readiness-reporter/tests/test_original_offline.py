"""Original direct projection tests with fictional identifiers and dates."""

from datetime import UTC, date, datetime
from pathlib import Path

from shipment_readiness import (
    FlexLogisticsHandoffLotState,
    OSGridOrder,
    SavedReadinessInput,
    build_shipment_readiness,
)


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "snapshot.json"


def order(**updates) -> OSGridOrder:
    source = SavedReadinessInput.model_validate_json(EXAMPLE.read_bytes())
    values = source.orders[0].model_dump()
    values.update(status="Open", dock_date=None, lot_ids=None, lot_quantities=None, row_version=None)
    values.update(updates)
    return OSGridOrder(**values)


def handoff_state(**updates) -> FlexLogisticsHandoffLotState:
    source = SavedReadinessInput.model_validate_json(EXAMPLE.read_bytes())
    values = source.handoff_states[0].model_dump()
    values.update(updates)
    return FlexLogisticsHandoffLotState(**values)


def result_for(
    *orders: OSGridOrder,
    handoff_states: tuple[FlexLogisticsHandoffLotState, ...] = (),
):
    return build_shipment_readiness(
        orders=orders,
        revision_sha256="b" * 64,
        revision_filename="fictional-orders.json",
        revision_status="ACTIVE",
        source_row_count=len(orders),
        handoff_states=handoff_states,
    )


def test_handoff_classifies_fpc_orders_without_claiming_mes_or_shipment() -> None:
    result = result_for(
        order(),
        order(
            row_id="c" * 24,
            source_row=5,
            dock_date=date(2030, 8, 18),
        ),
        order(
            row_id="d" * 24,
            source_row=6,
            dock_date=date(2030, 8, 18),
            lot_ids="DEMO-LOT-B",
            lot_quantities="300",
            row_version=3,
        ),
    )

    states = {row.row_id: row for row in result.rows}
    assert states["a" * 24].readiness_state == "AWAITING_DOCK"
    assert states["a" * 24].readiness_label == "In Flex production"
    assert states["c" * 24].readiness_state == "LOT_EVIDENCE_REQUIRED"
    assert states["d" * 24].readiness_state == "DOCKED_AWAITING_FLEX_CLEARANCE"
    assert states["d" * 24].can_mark_ready is True
    assert all(row.mes_transaction_recorded is False for row in result.rows)
    assert result.database_writes is False
    assert result.mes_transaction_recorded is False
    assert result.shipment_recorded is False


def test_handoff_keeps_panel_flex_out_of_operator_logistics_queue() -> None:
    result = result_for(
        order(
            row_id="e" * 24,
            source_sheet="P",
            modality="PANEL-DEMO",
            part_number="DEMO-PANEL",
            quantity=180,
        )
    )

    assert result.rows == ()
    assert result.filtered_row_count == 0


def test_handoff_excludes_unmapped_products_from_flex_operator_scope() -> None:
    result = result_for(order(modality="UNMAPPED", part_number="UNKNOWN"))

    assert result.rows == ()


def test_handoff_filters_deterministically() -> None:
    result = build_shipment_readiness(
        orders=(
            order(),
            order(
                row_id="f" * 24,
                modality="CON-DEMO",
                part_number="DEMO-02",
                quantity=560,
                dock_date=date(2030, 8, 18),
                lot_ids="DEMO-LOT-C",
                lot_quantities="560",
                row_version=2,
            ),
        ),
        revision_sha256="b" * 64,
        revision_filename="fictional-orders.json",
        revision_status="ACTIVE",
        source_row_count=2,
        search="DEMO-02",
        readiness="DOCKED_AWAITING_FLEX_CLEARANCE",
    )

    assert result.filtered_row_count == 1
    assert result.rows[0].part_number == "DEMO-02"


def test_docked_order_supports_partial_lot_clearance_and_ptl_return() -> None:
    docked = order(
        row_version=3,
        dock_date=date(2030, 8, 18),
        lot_ids="DEMO-LOT-A DEMO-LOT-B",
        lot_quantities="180 120",
        status="Docked",
    )

    ready = result_for(docked).rows[0]
    assert ready.readiness_state == "DOCKED_AWAITING_FLEX_CLEARANCE"
    assert ready.can_mark_ready is True
    assert ready.priority_eligible is True

    partial = result_for(docked, handoff_states=(handoff_state(),)).rows[0]
    assert partial.readiness_state == "PARTIALLY_READY_FOR_LOGISTICS"
    assert partial.ready_for_logistics_quantity == 180
    assert partial.production_remaining_quantity == 120
    assert partial.can_mark_ready is True
    assert partial.can_return_to_flex is True
    assert partial.logistics_mes_status == "AWAITING_AUTHORITATIVE_MES_EVIDENCE"

    returned = result_for(
        docked,
        handoff_states=(
            handoff_state(
                lifecycle_state="RETURNED_TO_FLEX",
                state_version=2,
                last_event_identity="d" * 64,
                returned_at=datetime(2030, 8, 18, 16, 0, tzinfo=UTC),
                returned_by="fictional-return-reviewer",
                return_reason="Lot requires production rework",
            ),
        ),
    ).rows[0]
    assert returned.readiness_state == "DOCKED_AWAITING_FLEX_CLEARANCE"
    assert returned.ready_for_logistics_quantity == 0
    assert returned.lots[0].return_reason == "Lot requires production rework"


def test_shipped_evidence_takes_precedence_over_historical_dock_date() -> None:
    shipped = order(
        row_version=4,
        dock_date=date(2030, 8, 18),
        lot_ids="DEMO-LOT-A",
        lot_quantities="300",
        ship_quantity=300,
        status="Shipped",
    )

    projected = result_for(shipped).rows[0]
    assert projected.readiness_state == "SHIPPING_EVIDENCE_RECORDED"
    assert projected.can_mark_ready is False
    assert projected.priority_eligible is False
