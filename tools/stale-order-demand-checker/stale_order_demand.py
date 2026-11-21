"""Find obsolete order states that still carry positive demand."""

import argparse
import json
from pathlib import Path
import sys


def stale_open_order_ids(
    state_by_id: dict[str, object], expected_order_ids: set[str]
) -> list[str]:
    """Return only obsolete states that can still contribute live demand."""

    return sorted(
        row_id
        for row_id, row in state_by_id.items()
        if row_id not in expected_order_ids
        and not row["cancelled"]
        and int(row["remaining_quantity"]) > 0
    )


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("Duplicate keys are ambiguous.")
    return result


def valid_order_id(value):
    return isinstance(value, str) and bool(value.strip())


def load_snapshot(path: Path):
    payload = json.loads(path.read_bytes(), object_pairs_hook=unique_object)
    if not isinstance(payload, dict) or set(payload) != {"active_order_ids", "states"}:
        raise ValueError("Expected active_order_ids and states.")
    active = payload["active_order_ids"]
    if not isinstance(active, list) or any(not valid_order_id(order_id) for order_id in active):
        raise ValueError("Expected a list of non-blank active order IDs.")

    states = payload["states"]
    if not isinstance(states, dict):
        raise ValueError("Expected states keyed by order ID.")
    for order_id, row in states.items():
        if (
            not valid_order_id(order_id)
            or not isinstance(row, dict)
            or type(row.get("cancelled")) is not bool
            or type(row.get("remaining_quantity")) is not int
        ):
            raise ValueError("Expected an order ID, a boolean cancelled flag and an integer remaining quantity.")
    return states, set(active)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved active IDs and order states in JSON")
    args = parser.parse_args()
    try:
        states, active = load_snapshot(args.snapshot)
    except (OSError, ValueError):
        print("Invalid order state snapshot. See SETUP.md for the JSON format.", file=sys.stderr)
        return 2

    stale = stale_open_order_ids(states, active)
    print(json.dumps({"stale_order_ids": stale}))
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
