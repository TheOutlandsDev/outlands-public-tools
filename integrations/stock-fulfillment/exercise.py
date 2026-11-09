"""Exercise the installed stock packages with fictional declarations."""
from __future__ import annotations

import hashlib
import json
from importlib.resources import files

from outlands_stock_movement_ledger_checker.movements import check as ledger_check
from outlands_inventory_position_calculator.position import check as position_check
from outlands_replenishment_proposal_planner.replenish import check as proposal_check
from outlands_shipment_coverage_reconciler.shipments import check as shipment_check

PACKAGES = (
    "outlands_stock_movement_ledger_checker",
    "outlands_inventory_position_calculator",
    "outlands_replenishment_proposal_planner",
    "outlands_shipment_coverage_reconciler",
)
CHECKS = (ledger_check, position_check, proposal_check, shipment_check)


def sample(index: int, name: str = "input.json") -> bytes:
    return files(PACKAGES[index]).joinpath("examples", name).read_bytes()


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def pin(value: object) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def main() -> None:
    ledger = ledger_check(sample(0))
    assert ledger["status"] == "PASS"
    assert ledger["assessment"]["stocks"][0]["closing_quantity"] == 10

    position_input = json.loads(sample(1))
    stock = position_input["stocks"][0]
    stock.update(on_hand=ledger["assessment"]["stocks"][0]["closing_quantity"], at=ledger["as_of"])
    for side in ("inbound", "reservations"):
        for row in position_input[side]:
            row["stock_sha256"] = pin(stock)
    position = position_check(encode(position_input))
    assert position["status"] == "PASS"
    assert position["assessment"]["stocks"][0]["inventory_position"] == 8

    proposal_input = json.loads(sample(2))
    selected = proposal_input["positions"][0]
    selected.update(inventory_position=position["assessment"]["stocks"][0]["inventory_position"],
                    as_of=position["as_of"])
    proposal_input["policies"][0]["position_sha256"] = pin(selected)
    proposal = proposal_check(encode(proposal_input))
    assert proposal["status"] == "PASS"
    assert proposal["assessment"]["positions"][0]["proposed_quantity"] == 12

    shipment_input = json.loads(sample(3))
    assert shipment_input["orders"][0]["quantity"] == position_input["reservations"][0]["quantity"]
    shipment = shipment_check(encode(shipment_input))
    assert shipment["status"] == "PASS"
    assert shipment["assessment"]["orders"][0]["declared_received_quantity"] == 4

    for report in (ledger, position, proposal, shipment):
        for key in ("physical_stock_verified", "inbound_eligibility_verified",
                    "delivery_verified", "stock_updated", "purchase_order_created",
                    "reservations_changed", "shipment_executed",
                    "procurement_authorized", "target_changes_performed"):
            assert report[key] is False
    reviews = [check(sample(index, "needs-review.json"))
               for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "REVIEW_REQUIRED" for report in reviews)
    print(json.dumps({"status": "PASS", "positive_examples": 4,
                      "review_examples": 4, "closing_quantity": 10,
                      "inventory_position": 8, "proposed_quantity": 12,
                      "declared_received_quantity": 4,
                      "operational_changes": False}, sort_keys=True))


if __name__ == "__main__":
    main()
