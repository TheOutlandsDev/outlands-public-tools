"""Compare a validated route CSV with occurrence keys and row hashes from a saved inventory."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

from route_reference import (
    RouteValidationError,
    ValidatedRouteDataset,
    route_occurrence_key,
    source_row_sha256,
    validate_route_dataset,
)


class RouteReconciliationError(ValueError):
    """The inventory cannot be reconciled with the source route records."""


def load_inventory(path: Path) -> tuple[str, dict[str, str]]:
    payload = json.loads(path.read_bytes())
    if not isinstance(payload, dict) or set(payload) != {"source_workbook_sha256", "occurrences"}:
        raise RouteReconciliationError("The inventory must declare a source hash and occurrences.")
    fingerprint = payload["source_workbook_sha256"]
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise RouteReconciliationError("The inventory source hash must be lowercase SHA-256.")
    if not isinstance(payload["occurrences"], list):
        raise RouteReconciliationError("The inventory occurrences must be an array.")

    existing: dict[str, str] = {}
    for item in payload["occurrences"]:
        if not isinstance(item, dict) or set(item) != {"route_occurrence_key", "source_row_sha256"}:
            raise RouteReconciliationError("Every inventory occurrence must declare a key and row hash.")
        key = item["route_occurrence_key"]
        row_hash = item["source_row_sha256"]
        if not isinstance(key, str) or not key or not isinstance(row_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", row_hash):
            raise RouteReconciliationError("The inventory contains an invalid occurrence key or row hash.")
        if key in existing:
            raise RouteReconciliationError("The inventory contains a duplicate route occurrence.")
        existing[key] = row_hash
    return fingerprint, existing


def reconcile_occurrences(
    dataset: ValidatedRouteDataset, source_hash: str, existing: dict[str, str],
) -> dict:
    if source_hash != dataset.metadata.source_workbook_sha256:
        raise RouteReconciliationError("The inventory belongs to a different source workbook.")

    expected = {
        route_occurrence_key(row): source_row_sha256(row)
        for row in dataset.rows
    }
    if set(existing) - set(expected):
        raise RouteReconciliationError("The inventory contains an unexpected route occurrence.")
    for key, stored_hash in existing.items():
        if expected[key] != stored_hash:
            raise RouteReconciliationError("A saved route occurrence does not match source.")

    expected_counts: Counter[tuple[str, str]] = Counter()
    matched_counts: Counter[tuple[str, str]] = Counter()
    missing = []
    for source_row_number, row in enumerate(dataset.rows, start=2):
        key = route_occurrence_key(row)
        route = (row["RequestedFlowName"], row["RequestedVersion"])
        expected_counts[route] += 1
        if key in existing:
            matched_counts[route] += 1
        else:
            missing.append({
                "route_occurrence_key": key,
                "source_row_sha256": expected[key],
                "source_row_number": source_row_number,
            })

    return {
        "source_workbook_sha256": source_hash,
        "expected_count": len(dataset.rows),
        "matched_count": len(existing),
        "missing_count": len(missing),
        "routes": [
            {
                "flow": flow,
                "version": version,
                "expected_count": count,
                "matched_count": matched_counts[(flow, version)],
                "missing_count": count - matched_counts[(flow, version)],
            }
            for (flow, version), count in expected_counts.items()
        ],
        "missing_occurrences": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route_csv", type=Path)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    try:
        dataset = validate_route_dataset(args.route_csv, args.metadata)
        source_hash, existing = load_inventory(args.inventory)
        report = reconcile_occurrences(dataset, source_hash, existing)
    except (RouteValidationError, RouteReconciliationError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("A route input is unreadable or invalid.", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return int(report["missing_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
