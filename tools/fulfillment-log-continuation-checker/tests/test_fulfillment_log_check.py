from pathlib import Path

from fulfillment_log_check import compare_allocations, parse_log, read_report

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_fictional_log_matches_order_group_and_allocation_line_counts():
    groups = parse_log(EXAMPLES / "fulfillment.txt")
    result = compare_allocations(groups, read_report(EXAMPLES / "allocations.json"))

    assert result["status"] == "PASS"
    assert result["order_group_count"] == 32
    assert result["allocation_line_count"] == 33
    assert result["demand_quantity"] == 920


def test_fictional_log_preserves_k6_to_k5_continuation():
    groups = parse_log(EXAMPLES / "fulfillment.txt")
    order = next(row for row in groups if row["key"] == (17, 1, "DEMO-PART-A"))

    assert order["demand"] == 300
    assert order["allocation_lines"] == 2
    assert order["lots"] == [("DEMO-LOT-01-A", 6), ("DEMO-LOT-01-B", 5)]
