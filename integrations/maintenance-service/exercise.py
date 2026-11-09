"""Exercise installed maintenance packages using fictional declarations."""
from __future__ import annotations

import json
from importlib.resources import files

from outlands_meter_history_checker.meters import check as meter_check
from outlands_maintenance_due_planner.due import check as due_check
from outlands_work_order_lifecycle_checker.orders import check as order_check
from outlands_service_completion_checker.completion import check as completion_check

PACKAGES = (
    "outlands_meter_history_checker",
    "outlands_maintenance_due_planner",
    "outlands_work_order_lifecycle_checker",
    "outlands_service_completion_checker",
)
CHECKS = (meter_check, due_check, order_check, completion_check)


def sample(index: int, name: str = "input.json") -> bytes:
    return files(PACKAGES[index]).joinpath("examples", name).read_bytes()


def main() -> None:
    values = [json.loads(sample(index)) for index in range(4)]
    reports = [check(sample(index)) for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "PASS" for report in reports)
    meter, due, order, completion = reports

    # The due example repeats the meter total as a supplied declaration.
    assert values[0]["meters"][0]["id"] == values[1]["meters"][0]["id"]
    assert meter["snapshots"][0]["total_usage"] == values[1]["meters"][0]["total_usage"] == 12
    assert due["assessments"][0]["due_state"] == "not_due"
    assert due["meter_sources_verified"] is False

    # The service example pins the exact fictional order checked separately.
    assert values[2]["orders"] == values[3]["orders"]
    assert order["orders"][0]["order_sha256"] == values[3]["contracts"][0]["order_sha256"]
    assert completion["assessments"][0]["order_sha256"] == order["orders"][0]["order_sha256"]
    assert completion["assessments"][0]["completed_under_contract"] is True

    assert meter["live_reading_collected"] is False
    assert due["schedule_created"] is False and due["service_performed"] is False
    assert order["orders_changed"] is False
    assert completion["physical_service_verified"] is False
    assert completion["stock_or_orders_changed"] is False
    reviews = [check(sample(index, "needs-review.json"))
               for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "REVIEW_REQUIRED" for report in reviews)
    print(json.dumps({"status": "PASS", "positive_examples": 4,
                      "review_examples": 4, "declared_meter_total": "MATCH",
                      "order_pin": "MATCH", "operational_changes": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()
