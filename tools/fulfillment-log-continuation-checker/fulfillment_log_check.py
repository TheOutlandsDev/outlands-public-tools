"""Check saved fulfillment log continuations against ordered allocations."""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

MAX_INPUT_BYTES = 4 * 1024 * 1024
OrderKey = tuple[int, int, str]
LotSequence = list[tuple[str, int]]


class ContinuationError(ValueError):
    """The log or saved allocation report cannot be compared."""


def read_text(path: Path) -> str:
    if not path.is_file():
        raise ContinuationError("Expected a saved input file")
    with path.open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise ContinuationError("Input exceeds the 4 MiB limit")
    return content.decode("utf-8-sig")


LOG_PATTERN = re.compile(
    r"^For Week #(\d+) Index #(\d+)-([^ ]+) we need -->(\d+).*"
)
LOT_PATTERN = re.compile(r"-->([A-Z0-9-]+) @ Kanban #(\d+)")


def parse_log(path: Path) -> list[dict[str, Any]]:
    lines = read_text(path).splitlines()
    groups: list[dict[str, Any]] = []
    for line in lines:
        match = LOG_PATTERN.match(line)
        if match is None:
            continue
        key = (int(match[1]), int(match[2]), match[3])
        lots = [(lot, int(kanban)) for lot, kanban in LOT_PATTERN.findall(line)]
        if groups and groups[-1]["key"] == key:
            groups[-1]["allocation_lines"] += 1
            groups[-1]["lots"].extend(lots)
        else:
            groups.append({
                "key": key,
                "demand": int(match[4]),
                "lots": lots,
                "allocation_lines": 1,
            })
    return groups


def unique_fields(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ContinuationError("Allocation report contains a duplicate JSON field")
    return result


def is_natural(value: object) -> bool:
    return type(value) is int and value >= 0


def read_report(path: Path) -> dict[OrderKey, LotSequence]:
    document = json.loads(read_text(path), object_pairs_hook=unique_fields)
    if not isinstance(document, dict) or not isinstance(document.get("orders"), list):
        raise ContinuationError("Allocation report requires an orders array")

    by_order = {}
    for number, order in enumerate(document["orders"], start=1):
        if not isinstance(order, dict):
            raise ContinuationError(f"Report order {number} must be an object")
        week, index, part = (order.get(name) for name in ("week", "index", "part_number"))
        if not is_natural(week) or not is_natural(index) or not isinstance(part, str) or not part:
            raise ContinuationError(f"Report order {number} has an invalid order key")
        key = (week, index, part)
        if key in by_order:
            raise ContinuationError(f"Report order {number} repeats an order key")
        allocations = order.get("allocations")
        if not isinstance(allocations, list):
            raise ContinuationError(f"Report order {number} requires an allocations array")
        lots = []
        for allocation in allocations:
            if not isinstance(allocation, dict):
                raise ContinuationError(f"Report order {number} has an invalid allocation")
            lot_id, kanban = allocation.get("lot_id"), allocation.get("kanban")
            if not isinstance(lot_id, str) or not lot_id or not is_natural(kanban):
                raise ContinuationError(f"Report order {number} has an invalid lot ID or Kanban")
            lots.append((lot_id, kanban))
        by_order[key] = lots
    return by_order


def order_fields(key: OrderKey) -> dict:
    week, index, part = key
    return {"week": week, "index": index, "part_number": part}


def lot_fields(lots: LotSequence) -> list[dict]:
    return [{"lot_id": lot, "kanban": kanban} for lot, kanban in lots]


def compare_allocations(groups: list[dict[str, Any]], saved: dict[OrderKey, LotSequence]) -> dict:
    keys = {group["key"] for group in groups}
    if not groups:
        raise ContinuationError("Log contains no recognizable allocation lines")
    if len(keys) != len(groups):
        raise ContinuationError("Log repeats an order key in nonconsecutive groups")

    orders = []
    issues = []
    for group in groups:
        key = group["key"]
        expected = group["lots"]
        actual = saved.get(key)
        identity = order_fields(key)
        orders.append({
            **identity,
            "demand_quantity": group["demand"],
            "allocation_lines": group["allocation_lines"],
            "lots": lot_fields(expected),
        })
        if actual is None:
            issues.append({**identity, "kind": "ORDER_MISSING_FROM_REPORT"})
        elif actual != expected:
            issues.append({
                **identity,
                "kind": "ORDERED_LOTS_DIFFER",
                "log_lots": lot_fields(expected),
                "report_lots": lot_fields(actual),
            })
    issues.extend({**order_fields(key), "kind": "ORDER_MISSING_FROM_LOG"}
                  for key in sorted(saved.keys() - keys))
    return {
        "status": "FAIL" if issues else "PASS",
        "order_group_count": len(groups),
        "allocation_line_count": sum(group["allocation_lines"] for group in groups),
        "demand_quantity": sum(group["demand"] for group in groups),
        "orders": orders,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("allocation_report", type=Path)
    args = parser.parse_args()
    try:
        report = compare_allocations(parse_log(args.log), read_report(args.allocation_report))
    except ContinuationError as exc:
        print(f"Fulfillment check: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("Fulfillment check: cannot read a valid UTF-8 log or allocation report", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
