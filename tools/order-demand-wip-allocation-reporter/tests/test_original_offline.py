"""Six original direct tests using a fictional saved snapshot."""

import csv
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path

import pytest

from order_needs import (
    OrderNeedsError,
    SavedSnapshot,
    build_order_needs,
    export_order_needs_csv,
    filter_order_needs,
)


WIP_SHA = "a" * 64
OS_SHA = "b" * 64
GENERATED = datetime(2030, 9, 1, 16, 30, tzinfo=UTC)
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "snapshot.json"


class OrderNeedsRepository:
    def __init__(self, *, mismatch: bool = False) -> None:
        self.snapshot = SavedSnapshot.model_validate_json(EXAMPLE.read_bytes())
        self.orders = self.snapshot.orders
        self.queue = self.snapshot.queue
        if mismatch:
            first = self.queue[0].model_copy(update={"remaining_demand": 501, "uncovered_demand": 141})
            self.queue = (first, *self.queue[1:])
        self.configured_part = self.queue[0].part_number

    def active_revision(self):
        return self.snapshot.active_revision()

    def list_active_orders(self, *, limit: int = 1000):
        assert limit == 1000
        return self.orders

    def list_automatic_lot_start_queue(self, *, limit: int = 20):
        assert limit == 20
        return self.queue


def test_order_needs_allocates_wip_by_due_date_and_conserves_quantities() -> None:
    repository = OrderNeedsRepository()
    result = build_order_needs(
        repository, expected_configured_modalities=12, generated_at=GENERATED
    )

    assert result.status == "PASS"
    assert result.database_writes is False
    assert result.source.revision_sha256 == OS_SHA
    assert result.source.wip_source_sha256 == WIP_SHA
    assert result.totals.open_order_lines == 3
    assert result.totals.ordered_quantity == 600
    assert result.totals.accepted_ship_quantity == 50
    assert result.totals.ready_for_logistics_quantity == 0
    assert result.totals.remaining_demand == 550
    assert result.totals.configured_demand == 500
    assert result.totals.fail_closed_demand == 50
    assert result.totals.eligible_wip == 360
    assert result.totals.covered_by_wip == 360
    assert result.totals.uncovered_after_wip == 140
    assert result.totals.recommended_lot_count == 1

    configured_rows = [row for row in result.rows if row.configured]
    assert [row.due_date for row in configured_rows] == [
        date(2030, 9, 4), date(2030, 9, 11)
    ]
    assert [row.covered_by_wip for row in configured_rows] == [300, 60]
    assert [row.uncovered_after_wip for row in configured_rows] == [0, 140]
    assert [row.eligible_wip_after for row in configured_rows] == [60, 0]
    assert [row.planning_status for row in configured_rows] == [
        "COVERED", "PARTIALLY_COVERED"
    ]
    fail_closed = next(row for row in result.rows if not row.configured)
    assert fail_closed.planning_status == "FAIL_CLOSED"
    assert fail_closed.covered_by_wip is None


def test_ready_for_logistics_quantity_stops_production_demand_without_shipping() -> None:
    repository = OrderNeedsRepository()
    repository.orders = (
        repository.orders[0].model_copy(update={"flex_ready_quantity": 200}),
        *repository.orders[1:],
    )

    result = build_order_needs(
        repository, expected_configured_modalities=12, generated_at=GENERATED
    )

    assert result.totals.ordered_quantity == 600
    assert result.totals.accepted_ship_quantity == 50
    assert result.totals.ready_for_logistics_quantity == 200
    assert result.totals.remaining_demand == 350
    assert result.totals.configured_demand == 300
    assert result.totals.uncovered_after_wip == 0
    assert result.totals.recommended_lot_count == 0
    first = next(row for row in result.rows if row.due_date == date(2030, 9, 4))
    assert first.ready_for_logistics_quantity == 200
    assert first.remaining_demand == 100


def test_fully_ready_order_remains_visible_without_creating_production_demand() -> None:
    repository = OrderNeedsRepository()
    repository.orders = (
        repository.orders[0].model_copy(update={"flex_ready_quantity": 300}),
        *repository.orders[1:],
    )

    result = build_order_needs(
        repository, expected_configured_modalities=12, generated_at=GENERATED
    )

    product = next(
        row for row in result.products if row.part_number == repository.configured_part
    )
    assert result.totals.open_order_lines == 3
    assert result.totals.ordered_quantity == 600
    assert result.totals.ready_for_logistics_quantity == 300
    assert result.totals.remaining_demand == 250
    assert product.order_line_count == 2
    assert product.ready_for_logistics_quantity == 300
    assert product.remaining_demand == 200
    assert all(row.due_date != date(2030, 9, 4) for row in result.rows)


def test_order_needs_fails_closed_when_os_and_queue_demand_disagree() -> None:
    with pytest.raises(OrderNeedsError, match="disagree"):
        build_order_needs(
            OrderNeedsRepository(mismatch=True),
            expected_configured_modalities=12,
            generated_at=GENERATED,
        )


def test_order_needs_filters_preallocated_rows_without_reallocating_wip() -> None:
    repository = OrderNeedsRepository()
    result = build_order_needs(
        repository, expected_configured_modalities=12, generated_at=GENERATED
    )
    filtered = filter_order_needs(result.rows, date_from=date(2030, 9, 11))

    assert len(filtered) == 2
    configured = next(row for row in filtered if row.configured)
    assert configured.eligible_wip_before == 60
    assert configured.covered_by_wip == 60
    assert configured.uncovered_after_wip == 140
    with pytest.raises(OrderNeedsError, match="date_from"):
        filter_order_needs(
            result.rows,
            date_from=date(2030, 9, 12),
            date_to=date(2030, 9, 11),
        )


def test_order_needs_csv_retains_provenance_and_filtered_values() -> None:
    repository = OrderNeedsRepository()
    result = build_order_needs(
        repository, expected_configured_modalities=12, generated_at=GENERATED
    )
    selected = filter_order_needs(
        result.rows, part_number=repository.configured_part
    )
    rows = list(
        csv.DictReader(
            StringIO(export_order_needs_csv(result, selected).lstrip("\ufeff"))
        )
    )

    assert len(rows) == 2
    assert {row["part_number"] for row in rows} == {repository.configured_part}
    assert {row["os_revision_sha256"] for row in rows} == {OS_SHA}
    assert {row["wip_source_sha256"] for row in rows} == {WIP_SHA}
    assert [row["covered_by_wip"] for row in rows] == ["300", "60"]
