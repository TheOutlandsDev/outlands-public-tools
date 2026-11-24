"""Report saved open orders by commit date and summarize demand by product."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import sys
from typing import Annotated

from pydantic import BaseModel, Field, StrictInt


MAX_INPUT_BYTES = 16 * 1024 * 1024
Part = Annotated[str, Field(min_length=1, max_length=80)]


class HorizonInputError(ValueError):
    """A saved order snapshot cannot be read safely."""


class OpenOrder(BaseModel):
    source_row: StrictInt = Field(gt=0)
    part_number: Part
    quantity: StrictInt
    flex_ptl_commit_date: date
    ship_quantity: StrictInt | None = Field(default=None, ge=0)
    dock_date: date | None = None


class SavedOrders(BaseModel):
    customer_orders: tuple[OpenOrder, ...]
    panel_orders: tuple[OpenOrder, ...]
    part_to_modality: dict[Part, Part] = Field(default_factory=dict)


def _open(order: OpenOrder) -> bool:
    return order.quantity > 0 and order.ship_quantity is None and order.dock_date is None


def _risk(order: OpenOrder, today: date) -> tuple[str, str]:
    days = (order.flex_ptl_commit_date - today).days
    if days < 0:
        return "Late", f"{abs(days)} day(s) past Flex commit"
    if days <= 7:
        return "High", f"Due in {days} day(s)"
    if days <= 30:
        return "Watch", f"Due in {days} day(s)"
    return "On track", f"Due in {days} day(s)"


def report_horizon(
    snapshot: SavedOrders,
    today: date,
    *,
    product: str | None = None,
    risk: str | None = None,
    horizon_days: int = 90,
) -> dict:
    if horizon_days < 0:
        raise HorizonInputError("The horizon must be zero or more days.")
    customer = snapshot.customer_orders
    panel = snapshot.panel_orders
    all_open = [row for row in (*customer, *panel) if _open(row)]
    visible = []
    for row in all_open:
        row_risk, reason = _risk(row, today)
        if product and row.part_number != product:
            continue
        if risk and row_risk.lower() != risk.lower():
            continue
        if (row.flex_ptl_commit_date - today).days > horizon_days:
            continue
        visible.append({"order": row, "risk": row_risk, "risk_reason": reason})
    visible.sort(key=lambda item: (item["order"].flex_ptl_commit_date, item["order"].part_number, item["order"].source_row))

    demand: dict[str, dict[str, int]] = defaultdict(lambda: {"orders": 0, "quantity": 0, "late": 0, "high": 0})
    for row in all_open:
        row_risk, _ = _risk(row, today)
        item = demand[row.part_number]
        item["orders"] += 1
        item["quantity"] += row.quantity
        if row_risk == "Late": item["late"] += 1
        if row_risk == "High": item["high"] += 1
    demand_rows = [
        {"part_number": part, "modality": snapshot.part_to_modality.get(part, "Unmapped"), **values}
        for part, values in sorted(demand.items())
    ]
    return {
        "today": today.isoformat(),
        "open_order_count": len(all_open),
        "open_order_quantity": sum(row.quantity for row in all_open),
        "late_count": sum(1 for row in all_open if _risk(row, today)[0] == "Late"),
        "high_risk_count": sum(1 for row in all_open if _risk(row, today)[0] == "High"),
        "demand_rows": demand_rows,
        "orders": [
            {**item, "order": item["order"].model_dump(mode="json")}
            for item in visible[:250]
        ],
        "order_results_truncated": len(visible) > 250,
        "horizon_days": horizon_days,
    }


def _unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise HorizonInputError("The snapshot contains duplicate JSON fields.")
        fields[key] = value
    return fields


def read_snapshot(path: Path) -> SavedOrders:
    if not path.is_file():
        raise HorizonInputError("The snapshot must be a regular file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise HorizonInputError("The snapshot is empty or exceeds its size limit.")
    payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
    return SavedOrders.model_validate(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat, help="Report date as YYYY-MM-DD")
    parser.add_argument("--horizon-days", type=int, default=90)
    parser.add_argument("--product", help="Exact part number")
    parser.add_argument("--risk", help="Risk name, compared case-insensitively")
    args = parser.parse_args(argv)
    try:
        result = report_horizon(read_snapshot(args.snapshot), args.as_of, product=args.product,
                                risk=args.risk, horizon_days=args.horizon_days)
    except HorizonInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, RecursionError):
        print("ERROR: The saved snapshot is unreadable or invalid.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
