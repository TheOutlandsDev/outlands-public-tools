"""Select a route and report its ordered occurrences from a saved snapshot."""

import argparse
import json
from pathlib import Path
import sys

MAX_BYTES = 8 * 1024 * 1024


class RouteError(ValueError):
    """A selector or saved snapshot failed validation."""


def object_from_pairs(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise RouteError("JSON contains a duplicate field")
    return value


def read_json(path):
    if not path.is_file():
        raise RouteError("Each input must be a file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise RouteError("Input exceeds the 8 MiB limit")
    return json.loads(data.decode("utf-8"), object_pairs_hook=object_from_pairs)


def field(row, name, kind, minimum, maximum, prefix=""):
    value = row.get(name)
    if kind is str and isinstance(value, str):
        if minimum <= len(value) <= maximum and value.startswith(prefix):
            return value
    if kind is int and type(value) is int and minimum <= value <= maximum:
        return value
    raise RouteError(f"Invalid {name}")


def records(value, minimum, maximum, label):
    if (not isinstance(value, list) or not minimum <= len(value) <= maximum
            or any(not isinstance(row, dict) for row in value)):
        raise RouteError(f"Invalid {label}")
    return value


def route_identity(row):
    return (field(row, "requested_flow_name", str, 1, 256),
            field(row, "requested_version", str, 1, 50))


def summaries(rows):
    by_route = {}
    for row in records(rows, 1, 20, "route summaries"):
        key = route_identity(row)
        if key in by_route:
            raise RouteError("Duplicate flow and version in route summaries")
        by_route[key] = field(row, "occurrence_count", int, 1, 500)
    return by_route


def report_routes(contract, snapshot, flow=None, version=None):
    """Check saved summary counts and select one route using the original ordering."""
    if (flow is None) != (version is None):
        raise RouteError("Select a route using both its flow name and version")
    if flow is not None:
        route_identity({"requested_flow_name": flow, "requested_version": version})
    if not isinstance(contract, dict) or not isinstance(snapshot, dict):
        raise RouteError("Expected JSON objects for the contract and snapshot")

    expected = summaries(contract.get("routes"))
    actual = summaries(snapshot.get("summaries"))
    total = field(snapshot, "total_occurrences", int, 1, 1000)
    if total != sum(expected.values()) or actual != expected:
        raise RouteError("Route summaries did not pass the declared count contract")

    selected = min(actual) if flow is None else (flow, version)
    if selected not in actual:
        raise RouteError("The requested route was not found")

    details = []
    identities = set()
    for row in records(snapshot.get("occurrences"), 0, 1000, "route occurrences"):
        key = route_identity(row)
        if key not in actual:
            raise RouteError("An occurrence belongs to an unknown route")
        if key != selected:
            continue
        order_key = field(row, "route_order_key", str, 2, 4000, "R:")
        position = field(row, "step_position", int, 1, 1000)
        correlation = field(row, "step_correlation_id", str, 4, 64, "CID:")
        identity = (order_key, position, correlation)
        if identity in identities:
            raise RouteError("Duplicate selected route occurrence")
        identities.add(identity)
        details.append({
            "route_order_key": order_key,
            "step_position": position,
            "step_correlation_id": correlation,
            "step_id": field(row, "step_id", str, 3, 64, "ID:"),
            "step_name": field(row, "step_name", str, 1, 256),
        })
    if len(details) != actual[selected]:
        raise RouteError("Selected route did not pass the declared count contract")
    details.sort(key=lambda row: (
        row["route_order_key"], row["step_position"], row["step_correlation_id"]
    ))

    def summary(key):
        return dict(requested_flow_name=key[0], requested_version=key[1],
                    occurrence_count=actual[key])

    return dict(total_occurrences=total, routes=[summary(key) for key in sorted(actual)],
                selected_route=summary(selected), occurrences=details)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--flow")
    parser.add_argument("--version")
    args = parser.parse_args()
    try:
        result = report_routes(read_json(args.contract), read_json(args.snapshot),
                               args.flow, args.version)
    except RouteError as error:
        print(f"Route report: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("Route report: cannot read a bounded UTF-8 JSON input", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
