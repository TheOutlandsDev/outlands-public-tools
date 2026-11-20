"""Write the fictional saved-plan fixture to a new JSON file."""

import argparse
import json
from pathlib import Path


def make_plan(path: Path) -> None:
    def allocation(lot, priority, days, kanban, risk, until_due=4):
        return dict(
            lot_id=lot, priority_label=f"Priority {priority}", priority_sort=priority,
            legacy_days_remaining=days, days_until_due=until_due, kanban=kanban,
            operation="Fictional inspection", quantity=12, risk_category=risk,
            risk_reason="Based on fictional saved allocation",
        )

    plan = dict(
        modality="DEMO-TYPE", planning_date="2030-06-01", orders=[
            dict(due_date="2030-06-05", allocations=[
                allocation("DEMO-K2-B", 3, 2, 2, "Standard"),
                allocation("DEMO-K2-A", 3, 2, 2, "Standard"),
                allocation("DEMO-K4-A", 2, 6, 4, "Severe process risk"),
            ]),
            dict(due_date="2030-06-06", allocations=[
                allocation("DEMO-K6-A", 4, 1, 6, "Next shipment", until_due=5),
            ]),
        ],
    )
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(dict(case_id="DEMO-CASE", source_status="fictional reviewed plan", plan=plan), stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_plan(parser.parse_args().output)
