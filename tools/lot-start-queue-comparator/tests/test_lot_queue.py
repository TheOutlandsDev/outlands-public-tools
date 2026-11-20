"""Three original direct cases and the result-count check using fictional queues."""

from pathlib import Path
import sys

import pytest

from lot_queue import QueueComparisonResult, QueueComparisonRow, QueueTotals, _differences, _totals

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_queues import demo_row


def queue_row(lots=1):
    return QueueComparisonRow(**demo_row(lots=lots))


def test_equal_queues_have_no_recommendation_or_timing_differences():
    current = (queue_row(),)
    recommendation, timing = _differences(current, current)
    assert recommendation == ()
    assert timing == ()


def test_recommendation_difference_is_exact_and_bounded():
    recommendation, timing = _differences((queue_row(lots=1),), (queue_row(lots=2),))
    assert timing == ()
    assert recommendation == ({
        "modality": "DEMO-A",
        "before_lots": 1,
        "after_lots": 2,
        "before_start_quantity": 24,
        "after_start_quantity": 48,
    },)


def test_queue_totals_conserve_demand_wip_and_starts():
    totals = _totals((queue_row(),))
    assert totals == QueueTotals(
        queue_rows=1, open_order_demand=30, eligible_wip=12, covered_by_wip=12,
        wip_surplus_after_demand=0, uncovered_after_wip=18,
        recommended_lots=1, recommended_start_quantity=24,
    )


def test_result_rejects_inconsistent_difference_count():
    base = {
        "before_totals": _totals(()), "after_totals": _totals(()),
        "changed_recommendations": ({"modality": "DEMO-A"},), "changed_recommendation_count": 0,
        "timing_or_start_date_changes": (), "timing_or_start_date_change_count": 0,
    }
    with pytest.raises(ValueError, match="recommendation difference count"):
        QueueComparisonResult.model_validate(base)
    base["changed_recommendation_count"] = 1
    base["timing_or_start_date_changes"] = ({"modality": "DEMO-B"},)
    with pytest.raises(ValueError, match="timing difference count"):
        QueueComparisonResult.model_validate(base)
