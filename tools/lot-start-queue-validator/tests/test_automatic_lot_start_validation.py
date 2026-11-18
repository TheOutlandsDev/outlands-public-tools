from dataclasses import dataclass, replace

import pytest

from production_planning.automatic_lot_start_validation import (
    AutomaticLotStartQueueValidationError,
    validate_and_summarize_automatic_queue,
)


@dataclass(frozen=True)
class QueueRow:
    modality: str = "DEMO-A"
    part_number: str = "PART-A"
    lot_prefix: str = "LOT-A"
    start_quantity: int = 200
    remaining_demand: int = 1460
    eligible_wip: int = 1925
    uncovered_demand: int = 0
    recommended_lot_count: int = 0
    queue_status: str = "CLEAR"
    wip_source_sha256: str | None = "a" * 64


def test_summary_explains_positive_open_demand_with_zero_uncovered() -> None:
    summary = validate_and_summarize_automatic_queue((QueueRow(),))

    assert summary.open_order_demand == 1460
    assert summary.eligible_wip == 1925
    assert summary.covered_by_wip == 1460
    assert summary.coverage_surplus == 465
    assert summary.uncovered_after_wip == 0
    assert summary.starts_required == 0


def test_wip_remainder_is_calculated_per_product_before_aggregation() -> None:
    summary = validate_and_summarize_automatic_queue(
        (
            QueueRow(),
            replace(
                QueueRow(),
                modality="DEMO-B",
                part_number="PART-B",
                lot_prefix="LOT-B",
                remaining_demand=260,
                eligible_wip=90,
                uncovered_demand=170,
                recommended_lot_count=1,
                queue_status="ACTIVE",
            ),
        )
    )

    assert summary.coverage_surplus == 465
    assert summary.uncovered_after_wip == 170


def test_uncovered_quantity_and_lots_are_recomputed_independently() -> None:
    summary = validate_and_summarize_automatic_queue(
        (
            replace(
                QueueRow(),
                eligible_wip=1175,
                uncovered_demand=285,
                recommended_lot_count=2,
                queue_status="ACTIVE",
            ),
        )
    )

    assert summary.uncovered_after_wip == 285
    assert summary.starts_required == 2


@pytest.mark.parametrize(
    "changes",
    (
        {"uncovered_demand": 1},
        {"recommended_lot_count": 1},
        {"queue_status": "ACTIVE"},
        {"wip_source_sha256": None},
    ),
)
def test_inconsistent_queue_values_fail_closed(changes) -> None:
    with pytest.raises(AutomaticLotStartQueueValidationError):
        validate_and_summarize_automatic_queue((replace(QueueRow(), **changes),))


def test_duplicate_modality_fails_closed() -> None:
    duplicate = replace(
        QueueRow(),
        part_number="PART-B",
        lot_prefix="LOT-B",
    )
    with pytest.raises(AutomaticLotStartQueueValidationError):
        validate_and_summarize_automatic_queue((QueueRow(), duplicate))
