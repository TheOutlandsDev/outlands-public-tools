"""Export saved fulfillment allocations to CSV with their source provenance."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import csv
from datetime import date, datetime
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import stat
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MAX_INPUT_BYTES = 4 * 1024 * 1024
SourceKey = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")]


class ActiveFulfillmentError(ValueError):
    """A saved fulfillment export could not be verified."""


FULFILLMENT_EXPORT_COLUMNS = (
    "planning_timestamp",
    "source_revision_sha256",
    "source_files",
    "week",
    "order_index",
    "part_number",
    "due_date",
    "demand_quantity",
    "covered_quantity",
    "uncovered_quantity",
    "recommended_start_quantity",
    "recommended_lot_count",
    "next_lot_to_start",
    "priority_sort",
    "priority_label",
    "status_color",
    "risk_category",
    "risk_reason",
    "allocation_sequence",
    "lot_id",
    "kanban",
    "operation",
    "allocated_quantity",
    "available_before",
    "available_after",
    "days_until_due",
    "days_remaining",
)


class SourceEvidence(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["PASS"] = "PASS"

    @field_validator("filename")
    @classmethod
    def require_source_basename(cls, value: str) -> str:
        if (value != value.strip() or value in {".", ".."}
                or any(ch in value for ch in "/\\:|") or any(ord(ch) < 32 for ch in value)):
            raise ValueError("Source filenames must be bare names.")
        return value

    model_config = ConfigDict(frozen=True)


class FulfillmentAllocation(BaseModel):
    lot_id: str
    part_number: str
    due_date: date
    kanban: int = Field(ge=1, le=6)
    operation: str
    allocated_quantity: int = Field(gt=0)
    available_before: int = Field(gt=0)
    available_after: int = Field(ge=0)
    is_verification: Literal[False] = False
    priority_sort: int = Field(ge=1, le=9)
    priority_label: str
    status_color: Literal["Red", "Orange", "Yellow", "Blue"]
    risk_category: str
    risk_reason: str
    days_until_due: int
    days_remaining: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class FulfillmentOrder(BaseModel):
    week: int = Field(gt=0)
    index: int = Field(gt=0)
    part_number: str
    due_date: date
    demand_quantity: int = Field(gt=0)
    covered_quantity: int = Field(ge=0)
    uncovered_quantity: int = Field(ge=0)
    recommended_start_quantity: int = Field(ge=0)
    recommended_lot_count: int = Field(ge=0)
    next_lot_to_start: str | None
    priority_sort: int = Field(ge=1, le=9)
    priority_label: str
    status_color: Literal["Red", "Orange", "Yellow", "Blue"]
    risk_category: str
    risk_reason: str
    allocations: tuple[FulfillmentAllocation, ...]

    model_config = ConfigDict(frozen=True)


class FulfillmentConservation(BaseModel):
    demand: int = Field(ge=0)
    covered: int = Field(ge=0)
    uncovered: int = Field(ge=0)
    eligible_supply: int = Field(ge=0)
    allocated_supply: int = Field(ge=0)
    remaining_supply: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_conservation(self) -> "FulfillmentConservation":
        if self.demand != self.covered + self.uncovered:
            raise ValueError("demand conservation failed")
        if self.eligible_supply != self.allocated_supply + self.remaining_supply:
            raise ValueError("supply conservation failed")
        return self


class ActiveFulfillmentResult(BaseModel):
    """The saved fulfillment result fields consumed by the original exporter."""

    status: Literal["PASS"] = "PASS"
    planning_timestamp: datetime
    sources: dict[SourceKey, SourceEvidence] = Field(min_length=1, max_length=32)
    orders: tuple[FulfillmentOrder, ...] = Field(max_length=10_000)
    conservation: FulfillmentConservation

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def reconcile_saved_totals(self) -> "ActiveFulfillmentResult":
        for order in self.orders:
            if (order.demand_quantity != order.covered_quantity + order.uncovered_quantity
                    or sum(line.allocated_quantity for line in order.allocations) != order.covered_quantity):
                raise ValueError("A saved order does not reconcile with its allocations.")
        if (
            sum(row.demand_quantity for row in self.orders) != self.conservation.demand
            or sum(row.covered_quantity for row in self.orders) != self.conservation.covered
            or sum(row.uncovered_quantity for row in self.orders) != self.conservation.uncovered
            or sum(row.covered_quantity for row in self.orders) != self.conservation.allocated_supply
        ):
            raise ValueError("The saved order totals do not reconcile with the summary.")
        return self


def _csv_safe(value: Any) -> Any:
    """Prevent exported text from being interpreted as a spreadsheet formula."""

    if isinstance(value, str) and (
        value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n"))
    ):
        return f"'{value}"
    return value


def export_active_fulfillment_csv(
    result: ActiveFulfillmentResult,
    orders: Sequence[FulfillmentOrder],
) -> str:
    """Return a flat, provenance-bearing fulfillment trace for review/export."""

    source_manifest = "|".join(
        f"{key}:{source.sha256}"
        for key, source in sorted(result.sources.items())
    )
    source_revision = sha256(source_manifest.encode("utf-8")).hexdigest()
    source_files = "|".join(
        f"{key}:{source.filename}"
        for key, source in sorted(result.sources.items())
    )
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FULFILLMENT_EXPORT_COLUMNS)
    writer.writeheader()
    for order in orders:
        allocations: Sequence[FulfillmentAllocation | None] = (
            order.allocations if order.allocations else (None,)
        )
        for allocation_sequence, allocation in enumerate(allocations, start=1):
            row = {
                "planning_timestamp": result.planning_timestamp.isoformat(),
                "source_revision_sha256": source_revision,
                "source_files": source_files,
                "week": order.week,
                "order_index": order.index,
                "part_number": order.part_number,
                "due_date": order.due_date.isoformat(),
                "demand_quantity": order.demand_quantity,
                "covered_quantity": order.covered_quantity,
                "uncovered_quantity": order.uncovered_quantity,
                "recommended_start_quantity": order.recommended_start_quantity,
                "recommended_lot_count": order.recommended_lot_count,
                "next_lot_to_start": order.next_lot_to_start or "",
                "priority_sort": order.priority_sort,
                "priority_label": order.priority_label,
                "status_color": order.status_color,
                "risk_category": order.risk_category,
                "risk_reason": order.risk_reason,
                "allocation_sequence": allocation_sequence if allocation else "",
                "lot_id": allocation.lot_id if allocation else "",
                "kanban": allocation.kanban if allocation else "",
                "operation": allocation.operation if allocation else "",
                "allocated_quantity": (
                    allocation.allocated_quantity if allocation else ""
                ),
                "available_before": allocation.available_before if allocation else "",
                "available_after": allocation.available_after if allocation else "",
                "days_until_due": allocation.days_until_due if allocation else "",
                "days_remaining": allocation.days_remaining if allocation else "",
            }
            writer.writerow({key: _csv_safe(value) for key, value in row.items()})
    return "\ufeff" + output.getvalue()


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ActiveFulfillmentError("The JSON has duplicate fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise ActiveFulfillmentError("The JSON has a non-finite number.")


def load_saved_fulfillment(path: Path) -> ActiveFulfillmentResult:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ActiveFulfillmentError("The saved fulfillment result must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise ActiveFulfillmentError("The saved fulfillment result is unavailable.") from exc
    if not 0 < len(content) <= MAX_INPUT_BYTES:
        raise ActiveFulfillmentError("The saved result is empty or exceeds the size limit.")
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        return ActiveFulfillmentResult.model_validate(payload)
    except ActiveFulfillmentError:
        raise
    except (ValueError, RecursionError) as exc:
        raise ActiveFulfillmentError("The saved fulfillment result or its totals are invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved fulfillment result JSON")
    parser.add_argument("--part-number", help="Select an exact part number")
    parser.add_argument("--status-color", choices=("Red", "Orange", "Yellow", "Blue"))
    args = parser.parse_args()
    try:
        result = load_saved_fulfillment(args.input)
    except ActiveFulfillmentError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    orders = tuple(
        order for order in result.orders
        if (args.part_number is None or order.part_number == args.part_number)
        and (args.status_color is None or order.status_color == args.status_color)
    )
    sys.stdout.buffer.write(export_active_fulfillment_csv(result, orders).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
