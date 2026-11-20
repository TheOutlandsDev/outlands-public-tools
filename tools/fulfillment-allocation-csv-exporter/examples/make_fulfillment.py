"""Write a fictional saved fulfillment result to a new JSON file."""

import argparse
import json
from pathlib import Path


def make_fulfillment(path: Path) -> None:
    first = dict(
        week=22, index=1, part_number="DEMO-PART-A", due_date="2030-06-04",
        demand_quantity=30, covered_quantity=20, uncovered_quantity=10,
        recommended_start_quantity=10, recommended_lot_count=1,
        next_lot_to_start="DEMO-LOT-03", priority_sort=3, priority_label="Priority 3",
        status_color="Blue", risk_category="Review", risk_reason="Fictional review",
        allocations=[],
    )
    for number, quantity, before, after in ((1, 12, 15, 3), (2, 8, 8, 0)):
        first["allocations"].append(dict(
            lot_id=f"DEMO-LOT-{number:02}", part_number=first["part_number"], due_date=first["due_date"],
            kanban=2, operation="Fictional inspection", allocated_quantity=quantity,
            available_before=before, available_after=after,
            priority_sort=3, priority_label="Priority 3", status_color="Blue",
            risk_category="Review", risk_reason="Fictional review", days_until_due=3, days_remaining=2,
        ))
    second = dict(first, index=2, part_number="DEMO-PART-B", demand_quantity=15,
                  covered_quantity=0, uncovered_quantity=15, priority_sort=4,
                  priority_label="Priority 4", status_color="Orange", allocations=[])
    payload = dict(
        planning_timestamp="2030-06-01T12:00:00+00:00",
        sources={"orders": dict(filename="fictional-orders.xlsx", sha256="a" * 64),
                 "inventory": dict(filename="fictional-inventory.xlsx", sha256="b" * 64)},
        orders=[first, second],
        conservation=dict(demand=45, covered=20, uncovered=25, eligible_supply=23,
                          allocated_supply=20, remaining_supply=3),
    )
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_fulfillment(parser.parse_args().output)
