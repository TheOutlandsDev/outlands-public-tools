"""Original deadline assertions adapted to the fictional allocation fixture."""

from datetime import date
from pathlib import Path

from demand_deadlines import build_ptl_production_exception_metrics
from order_needs import SavedSnapshot, build_order_needs


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "allocation-input.json"
OS_SHA = "b" * 64


def allocation():
    snapshot = SavedSnapshot.model_validate_json(EXAMPLE.read_bytes())
    return build_order_needs(
        snapshot, expected_configured_modalities=snapshot.expected_configured_modalities,
        generated_at=snapshot.generated_at,
    )


def test_ptl_exceptions_use_authoritative_remaining_production_demand() -> None:
    result = allocation()

    metrics = build_ptl_production_exception_metrics(
        result,
        generated_on=date(2030, 9, 5),
    )

    assert metrics.source_revision_sha256 == OS_SHA
    assert metrics.production_order_lines == 3
    assert metrics.production_quantity == 550
    assert metrics.late_order_lines == 1
    assert metrics.late_quantity == 300
    assert metrics.due_within_seven_days_order_lines == 1
    assert metrics.due_within_seven_days_quantity == 200


def test_window_includes_report_day_and_day_seven_but_not_day_eight():
    report = allocation()
    report_date = date(2030, 9, 4)
    # Retain quantities and move the last row to day eight.
    rows = (*report.rows[:2], report.rows[2].model_copy(update={"due_date": date(2030, 9, 12)}))
    report = report.model_copy(update={"rows": rows})
    metrics = build_ptl_production_exception_metrics(report, generated_on=report_date)
    assert metrics.production_order_lines == 3
    assert metrics.production_quantity == 550
    assert metrics.late_order_lines == metrics.late_quantity == 0
    assert metrics.due_within_seven_days_order_lines == 2
    assert metrics.due_within_seven_days_quantity == 500


def test_empty_demand_has_zero_counts_and_preserves_provenance():
    snapshot = SavedSnapshot.model_validate_json(EXAMPLE.read_bytes())
    orders = tuple(order.model_copy(update={"ship_quantity": order.quantity}) for order in snapshot.orders)
    queue = tuple(row.model_copy(update={"remaining_demand": 0}) for row in snapshot.queue)
    snapshot = snapshot.model_copy(update={"orders": orders, "queue": queue})
    report = build_order_needs(
        snapshot, expected_configured_modalities=snapshot.expected_configured_modalities,
        generated_at=snapshot.generated_at,
    )
    assert not report.rows
    metrics = build_ptl_production_exception_metrics(report)
    assert metrics.model_dump() == {
        "generated_on": snapshot.generated_at.date(),
        "source_revision_sha256": OS_SHA,
        "production_order_lines": 0,
        "production_quantity": 0,
        "late_order_lines": 0,
        "late_quantity": 0,
        "due_within_seven_days_order_lines": 0,
        "due_within_seven_days_quantity": 0,
    }
