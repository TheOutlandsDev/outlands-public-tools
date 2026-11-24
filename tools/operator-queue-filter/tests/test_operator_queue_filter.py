from pathlib import Path

from operator_queue_filter import filter_work_center, read_snapshot


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "work-center.json"


def test_operator_work_center_filters_product_kanban_and_risk() -> None:
    snapshot = read_snapshot(EXAMPLE)
    product = filter_work_center(snapshot, product="DEMO-A").model_dump(mode="json")
    kanban = filter_work_center(snapshot, kanban=5).model_dump(mode="json")
    risk = filter_work_center(snapshot, risk="Next shipment").model_dump(mode="json")

    assert {row["part_number"] for row in product["orders"]} == {"DEMO-A"}
    assert {row["part_number"] for row in product["actions"]} == {"DEMO-A"}
    assert {row["part_number"] for row in product["queue_rows"]} == {"DEMO-A"}
    assert {row["kanban"] for row in kanban["actions"]} == {5}
    assert {row["kanban"] for row in kanban["wip_rows"]} == {5}
    assert kanban["queue_rows"]
    assert all(
        {allocation["kanban"] for allocation in row["allocations"]} == {5}
        for row in kanban["queue_rows"]
    )
    assert {
        row["risk_category"] for row in risk["actions"]
    } == {"Next shipment"}
