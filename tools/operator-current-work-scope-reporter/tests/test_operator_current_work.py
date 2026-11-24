import json
from pathlib import Path

from operator_current_work import read_snapshot, report_scope


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "work-center.json"


def test_operator_work_center_current_and_full_scope_counts() -> None:
    payload = json.loads(EXAMPLE.read_bytes())
    snapshot = read_snapshot(EXAMPLE)
    current = report_scope(snapshot)
    full = report_scope(snapshot, scope="full")

    current_rows = [
        row
        for row in payload["queue_rows"]
        if row["risk_category"] in {"Past due", "Next shipment"}
        or row["uncovered"] > 0
        or row["recommended_lots"] > 0
    ]
    current_lot_ids = {
        allocation["lot_id"]
        for row in current_rows
        for allocation in row["allocations"]
    }
    assert current.allocation_count == sum(
        len(row["allocations"]) for row in current_rows
    )
    assert current.order_count == len(current_rows)
    assert current.wip_count == sum(
        row["lot_id"] in current_lot_ids for row in payload["wip_rows"]
    )
    assert full.allocation_count == len(payload["actions"])
    assert full.order_count == len(payload["orders"])
    assert full.wip_count == len(payload["wip_rows"])
