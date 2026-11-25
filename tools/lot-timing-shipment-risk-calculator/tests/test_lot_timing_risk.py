from pathlib import Path

from lot_timing_risk import calculate_timing, read_request

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "timing-request.json"


def test_fixed_date_timing_and_priority_match_reviewed_legacy_rules():
    plan = calculate_timing(read_request(EXAMPLE))
    first, second = plan["orders"]

    assert first["priority_sort"] == 2
    assert first["priority_label"] == "Rank 1"
    assert first["risk_category"] == "Severe process risk"
    assert [
        (
            item["lot_id"],
            item["legacy_days_remaining"],
            item["days_until_due"],
            item["schedule_delta"],
            item["priority_sort"],
            item["risk_category"],
        )
        for item in first["allocations"]
    ] == [
        ("DEMO-K6-A", 2, 7, 5, 3, "Next shipment"),
        ("DEMO-K4-A", 30, 7, -23, 2, "Severe process risk"),
        ("DEMO-K2-A", 39, 7, -32, 2, "Severe process risk"),
    ]
    assert second["priority_sort"] == 2
    assert second["allocations"][0]["days_until_due"] == 21
    assert second["allocations"][0]["schedule_delta"] == -18


def test_priority_boundaries_are_deterministic():
    from datetime import date

    request = read_request(EXAMPLE)
    first, second = request.orders
    k6, k4, _ = first.allocations

    def calculate(*orders):
        return calculate_timing(request.model_copy(update={"orders": orders}))["orders"]

    past_due = calculate(first.model_copy(update={"due_date": date(2030, 1, 9), "allocations": (k6,)}))
    assert past_due[0]["allocations"][0]["priority_sort"] == 1
    assert past_due[0]["allocations"][0]["risk_category"] == "Past due"

    upcoming = first.model_copy(update={"allocations": (k6,)})
    next_shipment = calculate(upcoming)
    assert next_shipment[0]["allocations"][0]["priority_sort"] == 3
    assert next_shipment[0]["allocations"][0]["risk_category"] == "Next shipment"

    moderate = calculate(
        upcoming.model_copy(update={"due_date": date(2030, 1, 11)}),
        second.model_copy(update={"due_date": date(2030, 2, 6), "allocations": (k4,)}),
    )
    assert moderate[1]["allocations"][0]["schedule_delta"] == -3
    assert moderate[1]["allocations"][0]["priority_sort"] == 4
    assert moderate[1]["allocations"][0]["risk_category"] == "Moderate process risk"

    future = calculate(upcoming, second.model_copy(update={"allocations": (k6,)}))
    assert future[1]["allocations"][0]["priority_sort"] == 5
    assert future[1]["allocations"][0]["priority_label"] == "Rank 2"
