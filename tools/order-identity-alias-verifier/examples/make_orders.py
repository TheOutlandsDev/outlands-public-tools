"""Write fictional saved order states and their legacy identities to a new file."""

import argparse
from datetime import date
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from order_alias import IdentityNamespaces, LegacyOrderIdentityRecord, OSOrderState, SavedIdentityBatch


NAMESPACES = IdentityNamespaces(legacy_contract_version="demo-legacy-1",
                               candidate_policy_revision="demo-candidate-1")


def order(*, order_id: str = "DEMO-ORDER-0001", version: int = 1, shipped: int = 0) -> OSOrderState:
    return OSOrderState(
        order_id=order_id, row_version=version, source_revision_sha256="a" * 64,
        part_number="DEMO-PART-A", ordered_quantity=36, accepted_ship_quantity=shipped,
        requested_ship_date=date(2031, 4, 15), cancelled=False,
    )


def record(value: OSOrderState | None = None) -> LegacyOrderIdentityRecord:
    current = value or order()
    return LegacyOrderIdentityRecord(
        legacy_event_fingerprint=current.fingerprint(NAMESPACES.legacy_contract_version), order=current,
    )


def make_orders(path: Path) -> None:
    batch = SavedIdentityBatch(
        namespaces=NAMESPACES,
        records=(record(), record(order(version=2, shipped=12)), record(order(order_id="DEMO-ORDER-0002"))),
    )
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(batch.model_dump(mode="json"), indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    make_orders(parser.parse_args().output)
