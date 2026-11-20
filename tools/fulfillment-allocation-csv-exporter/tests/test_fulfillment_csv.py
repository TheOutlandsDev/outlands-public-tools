"""Both original CSV export tests using a fictional saved fulfillment result."""

import csv
from io import StringIO
from pathlib import Path
import sys

import pytest

from fulfillment_csv import ActiveFulfillmentResult, export_active_fulfillment_csv, load_saved_fulfillment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_fulfillment import make_fulfillment


@pytest.fixture
def result(tmp_path: Path) -> ActiveFulfillmentResult:
    source = tmp_path / "fictional.json"
    make_fulfillment(source)
    return load_saved_fulfillment(source)


def test_active_fulfillment_csv_is_flat_complete_and_provenance_bearing(result: ActiveFulfillmentResult) -> None:
    exported = export_active_fulfillment_csv(result, result.orders)
    rows = list(csv.DictReader(StringIO(exported.lstrip("\ufeff"))))

    assert len(rows) == sum(max(1, len(order.allocations)) for order in result.orders)
    assert len({row["source_revision_sha256"] for row in rows}) == 1
    assert len(rows[0]["source_revision_sha256"]) == 64
    assert "orders:fictional-orders.xlsx" in rows[0]["source_files"]
    assert {
        "demand_quantity",
        "covered_quantity",
        "uncovered_quantity",
        "recommended_start_quantity",
        "risk_reason",
        "lot_id",
        "allocated_quantity",
        "available_after",
    } <= set(rows[0])
    assert sum(int(row["allocated_quantity"] or 0) for row in rows) == (
        result.conservation.allocated_supply
    )


def test_active_fulfillment_csv_honors_a_prevalidated_filtered_order_set(result: ActiveFulfillmentResult) -> None:
    selected = tuple(
        order
        for order in result.orders
        if order.part_number == "DEMO-PART-A" and order.status_color == "Blue"
    )

    rows = list(
        csv.DictReader(
            StringIO(export_active_fulfillment_csv(result, selected).lstrip("\ufeff"))
        )
    )

    assert rows
    assert {row["part_number"] for row in rows} == {"DEMO-PART-A"}
    assert {row["status_color"] for row in rows} == {"Blue"}
