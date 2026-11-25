"""Check the identity and lot allocations of a saved outbound event."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re


MAX_INPUT_BYTES = 1024 * 1024
ROW_ID_PATTERN = re.compile(r"^[0-9a-f]{24}$")
INPUT_FIELDS = {"revision_sha256", "row_id", "order_row_version", "lot_ids", "lot_quantities"}


class OutboundTransactionConflict(ValueError):
    """Raised when paired lot allocation fields contain invalid or ambiguous values."""


def outbound_event_identity(
    revision_sha256: str,
    row_id: str,
    order_row_version: int,
) -> str:
    """Return the deterministic identity for an outbound event."""

    if not re.fullmatch(r"[0-9a-f]{64}", revision_sha256):
        raise ValueError("The outbound source revision is invalid.")
    if not ROW_ID_PATTERN.fullmatch(row_id):
        raise ValueError("The outbound order identity is invalid.")
    if order_row_version <= 0:
        raise ValueError("The outbound order version is invalid.")
    payload = {
        "event_type": "FLEX_OUTBOUND_TRANSACTION",
        "order_row_version": order_row_version,
        "revision_sha256": revision_sha256,
        "row_id": row_id,
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def parse_lot_allocations(lot_ids: str, lot_quantities: str) -> tuple[tuple[str, int], ...]:
    """Parse paired lot columns and reject ambiguous allocation evidence."""

    identifiers = tuple(item for item in re.split(r"[\s,;]+", lot_ids.strip()) if item)
    raw_quantities = tuple(
        item for item in re.split(r"[\s,;]+", lot_quantities.strip()) if item
    )
    if not identifiers or len(identifiers) != len(raw_quantities):
        raise OutboundTransactionConflict(
            "Lot IDs and lot quantities must contain the same non-zero number of values."
        )
    if len({item.casefold() for item in identifiers}) != len(identifiers):
        raise OutboundTransactionConflict("Outbound lot IDs must be unique.")
    try:
        quantities = tuple(int(value) for value in raw_quantities)
    except ValueError as exc:
        raise OutboundTransactionConflict(
            "Every outbound lot quantity must be a whole number."
        ) from exc
    if any(value <= 0 for value in quantities):
        raise OutboundTransactionConflict(
            "Every outbound lot quantity must be greater than zero."
        )
    return tuple(zip(identifiers, quantities, strict=True))


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("Non-JSON constant")


def read_input(path):
    try:
        with path.open("rb") as stream:
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError("Unable to read the outbound event JSON.") from None

    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("The outbound event JSON exceeds the 1 MiB limit.")

    try:
        event = json.loads(payload.decode("utf-8-sig"), object_pairs_hook=unique_object,
                           parse_constant=reject_constant)
    except (ValueError, RecursionError):
        raise ValueError("Invalid outbound event JSON.") from None

    if (not isinstance(event, dict) or event.keys() != INPUT_FIELDS
            or type(event["order_row_version"]) is not int
            or any(not isinstance(event[field], str) for field in INPUT_FIELDS - {"order_row_version"})):
        raise ValueError("Invalid outbound event fields.")
    return event


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", type=Path, help="Saved outbound event fields in JSON")
    args = parser.parse_args()
    try:
        event = read_input(args.event)
        identity = outbound_event_identity(event["revision_sha256"], event["row_id"],
                                           event["order_row_version"])
        allocations = parse_lot_allocations(event["lot_ids"], event["lot_quantities"])
    except ValueError as exc:
        parser.exit(2, f"{exc}\n")

    result = {
        "status": "PASS",
        "event_identity": identity,
        "lot_count": len(allocations),
        "lot_allocations": [{"lot_id": lot_id, "quantity": quantity} for lot_id, quantity in allocations],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
