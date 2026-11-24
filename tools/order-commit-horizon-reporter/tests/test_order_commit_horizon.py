from datetime import date
from pathlib import Path

from order_commit_horizon import read_snapshot, report_horizon


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "orders.json"


def test_operations_center_open_order_count() -> None:
    context = report_horizon(read_snapshot(EXAMPLE), date(2025, 1, 1))

    assert context["open_order_count"] >= 0
