"""Exercise the installed material traceability packages on fictional records."""
from __future__ import annotations

import json
from importlib.resources import files

from outlands_bom_contract_checker.bom import check as bom_check
from outlands_lot_identity_checker.identities import check as identity_check
from outlands_material_allocation_checker.allocations import check as allocation_check
from outlands_handoff_lifecycle_checker.handoffs import check as handoff_check


PACKAGES = (
    "outlands_bom_contract_checker",
    "outlands_lot_identity_checker",
    "outlands_material_allocation_checker",
    "outlands_handoff_lifecycle_checker",
)
CHECKS = (bom_check, identity_check, allocation_check, handoff_check)


def sample(index: int, name: str = "input.json") -> bytes:
    return files(PACKAGES[index]).joinpath("examples", name).read_bytes()


def encode(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def main() -> None:
    bom = bom_check(sample(0))
    assert bom["status"] == "PASS"
    leaves = {row["component_id"]: row for row in bom["requirements"] if row["is_leaf"]}
    assert {key: row["quantity"] for key, row in leaves.items()} == {
        "blower-motor": 2, "panel-filter": 4}

    inventory = json.loads(sample(1))
    identity = identity_check(encode(inventory))
    assert identity["status"] == "PASS"
    resolved = {row["id"]: row["canonical_lot_id"] for row in identity["identities"]}
    assert resolved["service-motor-label"] == "motor-lot-a"

    selected = json.loads(sample(2))
    selected["lots"], selected["aliases"] = inventory["lots"], inventory["aliases"]
    selected["demands"] = [dict(id="demand-" + key, item_id=key,
                                unit=row["unit"], quantity=row["quantity"])
                           for key, row in sorted(leaves.items())]
    selected["allocations"] = [dict(id="reserve-" + key, demand_id="demand-" + key,
                                    lot_id="service-motor-label" if key == "blower-motor" else "filter-lot-a",
                                    quantity=row["quantity"])
                               for key, row in sorted(leaves.items())]
    allocation = allocation_check(encode(selected))
    assert allocation["status"] == "PASS"
    assert allocation["lot_contract_sha256"] == identity["lot_contract_sha256"]
    assert {row["id"]: row["unreserved"] for row in allocation["lots"]} == {
        "motor-lot-a": 2, "filter-lot-a": 4}

    reservation = next(row for row in selected["allocations"]
                       if row["id"] == "reserve-blower-motor")
    transfer = json.loads(sample(3))
    transfer["handoffs"][0].update(lot_id=resolved[reservation["lot_id"]],
                                    quantity=reservation["quantity"])
    transfer["receipts"][0]["quantity"] = reservation["quantity"]
    handoff = handoff_check(encode(transfer))
    assert handoff["status"] == "PASS" and handoff["accepted_quantity"] == 2
    assert handoff["handoffs"][0]["lot_id"] == "motor-lot-a"

    for report in (bom, identity, allocation, handoff):
        assert report["execution_authorized"] is False
        assert report["target_changes_performed"] is False
        assert report["content_privacy_verified"] is False
    reviews = [check(sample(index, "needs-review.json"))
               for index, check in enumerate(CHECKS)]
    assert all(report["status"] == "REVIEW_REQUIRED" for report in reviews)
    print(json.dumps({"status": "PASS", "positive_examples": 4,
                      "review_examples": 4, "leaf_quantities": {
                          key: row["quantity"] for key, row in leaves.items()},
                      "accepted_quantity": handoff["accepted_quantity"],
                      "operational_changes": False}, sort_keys=True))


if __name__ == "__main__":
    main()
