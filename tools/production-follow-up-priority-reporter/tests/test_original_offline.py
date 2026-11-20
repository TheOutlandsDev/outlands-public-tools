"""Three original direct priority tests with fictional upstream fixtures."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from flex_priorities import InternalPanelFlexLotState, build_flex_priorities, build_ptl_priorities
from order_needs import SavedSnapshot, build_order_needs
from shipment_readiness import SavedReadinessInput, build_shipment_readiness


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
GENERATED = datetime(2030, 9, 1, 16, 30, tzinfo=UTC)
OS_SHA = "b" * 64


def allocation_result(*, fully_ready=False):
    saved = SavedSnapshot.model_validate_json((EXAMPLES / "allocation-input.json").read_bytes())
    if fully_ready:
        order = saved.orders[2].model_copy(update={"flex_ready_quantity": saved.orders[2].quantity})
        saved = saved.model_copy(update={"orders": (*saved.orders[:2], order, *saved.orders[3:])})
    return build_order_needs(
        saved, expected_configured_modalities=saved.expected_configured_modalities, generated_at=GENERATED,
    )


def readiness_result():
    saved = SavedReadinessInput.model_validate_json((EXAMPLES / "readiness-input.json").read_bytes())
    return build_shipment_readiness(
        orders=saved.orders,
        revision_sha256=saved.revision_sha256,
        revision_filename=saved.revision_filename,
        revision_status=saved.revision_status,
        source_row_count=saved.source_row_count,
    )


def test_flex_priorities_reduce_order_needs_to_owned_exceptions() -> None:
    order_needs = allocation_result()

    priorities = build_flex_priorities(order_needs)

    assert [item.rank for item in priorities.items] == [1, 2]
    assert [item.urgency for item in priorities.items] == [
        "PAST_DUE",
        "CONFIGURATION_REQUIRED",
    ]
    assert priorities.items[0].owner_workspace == "Lot Starts"
    assert priorities.items[0].href == "/labs/flex/lot-starts"
    assert priorities.items[1].owner_workspace == "Order Needs"
    assert "part_number=DEMO-UNCONFIGURED" in priorities.items[1].href
    assert priorities.queue_scope == "OPERATOR"
    assert priorities.database_writes is False


def test_flex_priorities_include_each_required_logistics_clearance() -> None:
    shipment_readiness = readiness_result()

    priorities = build_ptl_priorities(
        shipment_readiness,
        as_of=GENERATED.date(),
    )

    logistics = [
        item
        for item in priorities.items
        if item.owner_workspace == "Logistics Handoff"
    ]
    assert len(logistics) == 2
    assert {item.urgency for item in logistics} == {"PAST_DUE", "ACTION_REQUIRED"}
    assert {item.href for item in logistics} == {
        f"/labs/flex/ptl-suite#flex-handoff-{row:024x}" for row in (10, 11)
    }
    assert any(item.title == "Clear 2 COF-DEMO-A lots for Logistics" for item in logistics)
    assert all("remain assigned to Flex production" in item.reason for item in logistics)
    assert priorities.queue_scope == "PTL"
    assert priorities.source_revision_sha256 == OS_SHA
    assert priorities.source_revision_role == "living-os"
    assert priorities.source_ids == (
        "living-os",
        "logistics-handoff-workflow",
        "panel-flex-workflow",
    )
    assert priorities.total_action_count == 3
    os_evidence = [
        item for item in priorities.items if item.owner_workspace == "Living O&S"
    ]
    assert len(os_evidence) == 1
    assert os_evidence[0].href == "/labs/flex/ptl-suite#ptl-os"
    assert "lot evidence" in os_evidence[0].title
    assert all(
        item.owner_workspace not in {"Order Needs", "Lot Starts"}
        for item in priorities.items
    )

    limited = build_ptl_priorities(
        shipment_readiness,
        as_of=GENERATED.date(),
        limit=1,
    )
    assert len(limited.items) == 1
    assert limited.total_action_count == 3


def test_ptl_priorities_group_completed_panel_flex_lots_for_hla() -> None:
    shipment_readiness = build_shipment_readiness(
        orders=(),
        revision_sha256=OS_SHA,
        revision_filename="fictional-orders.json",
        revision_status="ACTIVE",
        source_row_count=0,
    )
    lots = TypeAdapter(tuple[InternalPanelFlexLotState, ...]).validate_json(
        (EXAMPLES / "panel-lots.json").read_bytes()
    )

    priorities = build_ptl_priorities(
        shipment_readiness,
        panel_flex_lots=lots,
        as_of=GENERATED.date(),
    )

    assert priorities.queue_scope == "PTL"
    assert len(priorities.items) == 1
    item = priorities.items[0]
    assert item.owner_workspace == "Panel Flex & HLA"
    assert item.title == "Transfer 2 completed Panel Flex lots to HLA"
    assert "300 circuits across DEMO-PANEL" in item.reason
    assert item.href == "/labs/flex/ptl-suite#ptl-panel-flex"

def test_fully_ready_product_without_due_date_produces_no_action():
    report = allocation_result(fully_ready=True)
    ready = next(product for product in report.products if product.part_number == "DEMO-UNCONFIGURED")
    assert ready.remaining_demand == 0
    assert not any(row.part_number == ready.part_number for row in report.rows)
    priorities = build_flex_priorities(report)
    assert priorities.total_action_count == 1
    assert priorities.items[0].owner_workspace == "Lot Starts"
