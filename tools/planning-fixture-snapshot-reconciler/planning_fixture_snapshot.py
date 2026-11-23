"""Compare saved planning rows against an approved planning fixture snapshot."""

import argparse
from datetime import date, datetime
import json
from math import isfinite
from pathlib import Path
import sys


ROW_KEY_FIELDS = {
    "flex_planning_cases": ("case_id",),
    "flex_planning_orders": ("case_id", "order_id"),
    "flex_planning_wip": ("case_id", "lot_id"),
}


class FlexFixtureLoadError(ValueError):
    """A snapshot structure or its values do not match the fixture contract."""


def _canonical_rows(table: str, rows: list[dict]) -> list[dict]:
    """Normalize ClickHouse scalar representations and ignore row-return order."""

    normalized = [
        {
            key: value.decode("utf-8") if isinstance(value, bytes) else value
            for key, value in row.items()
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda row: tuple(row[field] for field in ROW_KEY_FIELDS[table]),
    )


def _canonical_snapshot(snapshot: dict) -> dict:
    if not isinstance(snapshot, dict) or snapshot.keys() != ROW_KEY_FIELDS.keys():
        raise FlexFixtureLoadError("Expected the case, order, and WIP tables.")
    normalized = {}
    for table, keys in ROW_KEY_FIELDS.items():
        rows = snapshot[table]
        if not isinstance(rows, list):
            raise FlexFixtureLoadError("Every table must contain a list of rows.")
        for row in rows:
            if not isinstance(row, dict) or any(not isinstance(k, str) for k in row):
                raise FlexFixtureLoadError("Every row must be an object with text field names.")
            if any(not isinstance(row.get(key), (str, bytes)) or not row[key] for key in keys):
                raise FlexFixtureLoadError("Every row must have nonempty text identity fields.")
            for value in row.values():
                if value is not None and (
                    type(value) not in (str, bytes, bool, int, float, date, datetime)
                    or (type(value) is float and not isfinite(value))
                ):
                    raise FlexFixtureLoadError("Every row field must contain a finite scalar.")
        canonical = _canonical_rows(table, rows)
        identities = {tuple(row[key] for key in keys) for row in canonical}
        if len(identities) != len(canonical):
            raise FlexFixtureLoadError("A table contains duplicate row identities.")
        normalized[table] = canonical
    return normalized


def _typed_values(snapshot: dict) -> dict:
    return {
        table: [{key: (type(value), value) for key, value in row.items()} for row in rows]
        for table, rows in snapshot.items()
    }


def reconcile_fixture_snapshot(expected: dict, stored: dict) -> dict:
    """Classify an empty snapshot or compare populated tables by exact values."""
    expected_by_table = _canonical_snapshot(expected)
    stored_by_table = _canonical_snapshot(stored)
    populated = any(stored_by_table.values())
    if populated and _typed_values(stored_by_table) != _typed_values(expected_by_table):
        raise FlexFixtureLoadError("The stored fixture is incomplete or differs from source.")

    counts = {
        table: {"expected": len(expected_by_table[table]), "stored": len(stored_by_table[table])}
        for table in ROW_KEY_FIELDS
    }
    return {
        "status": "match" if populated else "empty",
        "expected_row_count": sum(count["expected"] for count in counts.values()),
        "stored_row_count": sum(count["stored"] for count in counts.values()),
        "tables": counts,
    }


def _unique_object(items):
    result = dict(items)
    if len(result) != len(items):
        raise FlexFixtureLoadError("A JSON object contains duplicate field names.")
    return result


def _load_snapshot(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except FlexFixtureLoadError:
        raise
    except (OSError, ValueError, RecursionError) as exc:
        raise FlexFixtureLoadError("A snapshot is unreadable or invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("approved", type=Path, help="Expected rows from the approved fixture")
    parser.add_argument("stored", type=Path, help="Saved rows to reconcile")
    args = parser.parse_args()
    try:
        report = reconcile_fixture_snapshot(_load_snapshot(args.approved), _load_snapshot(args.stored))
    except FlexFixtureLoadError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
