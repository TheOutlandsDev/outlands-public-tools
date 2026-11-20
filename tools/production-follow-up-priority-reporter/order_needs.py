"""Allocate eligible WIP to saved orders and export preallocated report rows."""

from __future__ import annotations

import argparse
from collections import defaultdict
from collections.abc import Sequence
import csv
import json
import os
import stat
import sys
from datetime import UTC, date, datetime
from io import StringIO
from math import ceil
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from automatic_lot_start_validation import validate_and_summarize_automatic_queue


class OrderNeedsError(ValueError):
    """Raised when Order Needs cannot prove one authoritative result."""


class OSGridOrder(BaseModel):
    """The saved order fields consumed by the allocation engine."""

    part_number: str = Field(min_length=1, max_length=40)
    modality: str = Field(min_length=1, max_length=40)
    quantity: int = Field(gt=0)
    flex_ptl_commit_date: date
    ship_quantity: int | None = Field(default=None, ge=0)
    flex_ready_quantity: int = Field(default=0, ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")


class AutomaticLotStartQueueState(BaseModel):
    modality: str
    part_number: str
    lot_prefix: str
    start_quantity: int = Field(gt=0)
    remaining_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    uncovered_demand: int = Field(ge=0)
    recommended_lot_count: int = Field(ge=0)
    recommended_start_by: date | None
    queue_status: Literal["ACTIVE", "CLEAR"]
    queue_version: int = Field(gt=0)
    source_event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    wip_source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    updated_at: datetime
    updated_by: str

    model_config = ConfigDict(frozen=True, extra="forbid")

    @computed_field
    @property
    def wip_remaining_after_demand(self) -> int:
        """Eligible WIP that remains after this product's open demand is covered."""

        return max(0, self.eligible_wip - self.remaining_demand)


class OrderNeedsRepository(Protocol):
    def active_revision(self) -> dict[str, object]: ...

    def list_active_orders(self, *, limit: int = 1000) -> tuple[OSGridOrder, ...]: ...

    def list_automatic_lot_start_queue(
        self, *, limit: int = 20
    ) -> tuple[AutomaticLotStartQueueState, ...]: ...


class OrderNeedsSource(BaseModel):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    filename: str = Field(min_length=1, max_length=240)
    revision_status: Literal["ACTIVE"]
    source_row_count: int = Field(ge=0, le=1000)
    wip_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrderNeedsRow(BaseModel):
    due_date: date
    iso_year: int = Field(ge=2020, le=2100)
    iso_week: int = Field(ge=1, le=53)
    part_number: str
    modality: str
    order_line_count: int = Field(gt=0)
    ordered_quantity: int = Field(gt=0)
    accepted_ship_quantity: int = Field(ge=0)
    ready_for_logistics_quantity: int = Field(default=0, ge=0)
    remaining_demand: int = Field(gt=0)
    configured: bool
    planning_status: Literal[
        "COVERED", "PARTIALLY_COVERED", "UNCOVERED", "FAIL_CLOSED"
    ]
    eligible_wip_before: int | None = Field(default=None, ge=0)
    covered_by_wip: int | None = Field(default=None, ge=0)
    uncovered_after_wip: int | None = Field(default=None, ge=0)
    eligible_wip_after: int | None = Field(default=None, ge=0)
    lot_size: int | None = Field(default=None, gt=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_conservation(self) -> "OrderNeedsRow":
        if self.ordered_quantity != (
            self.accepted_ship_quantity
            + self.ready_for_logistics_quantity
            + self.remaining_demand
        ):
            raise ValueError("order-row demand conservation failed")
        planning_values = (
            self.eligible_wip_before,
            self.covered_by_wip,
            self.uncovered_after_wip,
            self.eligible_wip_after,
            self.lot_size,
        )
        if not self.configured:
            if self.planning_status != "FAIL_CLOSED" or any(
                value is not None for value in planning_values
            ):
                raise ValueError("unconfigured demand must fail closed")
            return self
        if any(value is None for value in planning_values):
            raise ValueError("configured demand is missing planning values")
        if self.remaining_demand != self.covered_by_wip + self.uncovered_after_wip:
            raise ValueError("coverage conservation failed")
        if self.eligible_wip_before != self.covered_by_wip + self.eligible_wip_after:
            raise ValueError("WIP conservation failed")
        return self


class OrderNeedsProductSummary(BaseModel):
    part_number: str
    modality: str
    configured: bool
    planning_status: Literal["CLEAR", "STARTS_REQUIRED", "FAIL_CLOSED"]
    order_line_count: int = Field(ge=0)
    ordered_quantity: int = Field(ge=0)
    accepted_ship_quantity: int = Field(ge=0)
    ready_for_logistics_quantity: int = Field(default=0, ge=0)
    remaining_demand: int = Field(ge=0)
    eligible_wip: int | None = Field(default=None, ge=0)
    covered_by_wip: int | None = Field(default=None, ge=0)
    uncovered_after_wip: int | None = Field(default=None, ge=0)
    wip_remaining_after_demand: int | None = Field(default=None, ge=0)
    lot_size: int | None = Field(default=None, gt=0)
    recommended_lot_count: int | None = Field(default=None, ge=0)
    recommended_start_by: date | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrderNeedsTotals(BaseModel):
    open_order_lines: int = Field(ge=0)
    ordered_quantity: int = Field(ge=0)
    accepted_ship_quantity: int = Field(ge=0)
    ready_for_logistics_quantity: int = Field(default=0, ge=0)
    remaining_demand: int = Field(ge=0)
    configured_demand: int = Field(ge=0)
    fail_closed_demand: int = Field(ge=0)
    eligible_wip: int = Field(ge=0)
    covered_by_wip: int = Field(ge=0)
    uncovered_after_wip: int = Field(ge=0)
    wip_remaining_after_demand: int = Field(ge=0)
    recommended_lot_count: int = Field(ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_conservation(self) -> "OrderNeedsTotals":
        if self.ordered_quantity != (
            self.accepted_ship_quantity
            + self.ready_for_logistics_quantity
            + self.remaining_demand
        ):
            raise ValueError("total demand conservation failed")
        if self.remaining_demand != self.configured_demand + self.fail_closed_demand:
            raise ValueError("configured-scope conservation failed")
        if self.configured_demand != self.covered_by_wip + self.uncovered_after_wip:
            raise ValueError("configured coverage conservation failed")
        if self.eligible_wip != self.covered_by_wip + self.wip_remaining_after_demand:
            raise ValueError("total WIP conservation failed")
        return self


class OrderNeedsResult(BaseModel):
    status: Literal["PASS"] = "PASS"
    authority: Literal["SUPPLIED_ORDER_AND_WIP_SNAPSHOTS"] = (
        "SUPPLIED_ORDER_AND_WIP_SNAPSHOTS"
    )
    generated_at: datetime
    source: OrderNeedsSource
    totals: OrderNeedsTotals
    products: tuple[OrderNeedsProductSummary, ...]
    rows: tuple[OrderNeedsRow, ...]
    database_writes: Literal[False] = False

    model_config = ConfigDict(frozen=True, extra="forbid")


def _remaining(order: OSGridOrder) -> tuple[int, int, int]:
    accepted = min(order.quantity, order.ship_quantity or 0)
    ready = min(max(0, order.quantity - accepted), order.flex_ready_quantity)
    return accepted, ready, max(0, order.quantity - accepted - ready)


def build_order_needs(
    repository: OrderNeedsRepository,
    *,
    expected_configured_modalities: int,
    generated_at: datetime | None = None,
) -> OrderNeedsResult:
    """Allocate accepted WIP to active O&S demand in deterministic due-date order."""

    active = repository.active_revision()
    if active.get("revision_status") != "ACTIVE":
        raise OrderNeedsError("The O&S revision is not active.")
    revision_sha256 = str(active.get("revision_sha256", ""))
    if len(revision_sha256) != 64:
        raise OrderNeedsError("The O&S revision hash is invalid.")

    orders = repository.list_active_orders(limit=1000)
    persisted_queue = repository.list_automatic_lot_start_queue(limit=20)
    persisted_queue_by_part = {item.part_number: item for item in persisted_queue}
    if len(persisted_queue_by_part) != len(persisted_queue):
        raise OrderNeedsError("The authoritative queue contains duplicate products.")

    grouped: dict[tuple[date, str, str], dict[str, int]] = defaultdict(
        lambda: {
            "lines": 0,
            "ordered": 0,
            "shipped": 0,
            "ready": 0,
            "remaining": 0,
        }
    )
    product_totals: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {
            "lines": 0,
            "ordered": 0,
            "shipped": 0,
            "ready": 0,
            "remaining": 0,
        }
    )
    persisted_demand_by_part: dict[str, int] = defaultdict(int)
    for order in orders:
        accepted, ready, remaining = _remaining(order)
        persisted_demand_by_part[order.part_number] += max(
            0, order.quantity - accepted
        )
        if order.quantity - accepted == 0:
            continue
        product_key = (order.part_number, order.modality)
        product_target = product_totals[product_key]
        for target in (product_target,):
            target["lines"] += 1
            target["ordered"] += order.quantity
            target["shipped"] += accepted
            target["ready"] += ready
            target["remaining"] += remaining
        if remaining == 0:
            continue
        key = (order.flex_ptl_commit_date, order.part_number, order.modality)
        grouped_target = grouped[key]
        grouped_target["lines"] += 1
        grouped_target["ordered"] += order.quantity
        grouped_target["shipped"] += accepted
        grouped_target["ready"] += ready
        grouped_target["remaining"] += remaining

    adjusted_queue: list[AutomaticLotStartQueueState] = []
    for queue_row in persisted_queue:
        if persisted_demand_by_part.get(queue_row.part_number, 0) != queue_row.remaining_demand:
            raise OrderNeedsError(
                f"O&S and queue demand disagree for {queue_row.part_number}."
            )
        production_demand = sum(
            values["remaining"]
            for (part, _modality), values in product_totals.items()
            if part == queue_row.part_number
        )
        uncovered = max(0, production_demand - queue_row.eligible_wip)
        recommended_lots = (
            ceil(uncovered / queue_row.start_quantity) if uncovered else 0
        )
        adjusted_queue.append(
            queue_row.model_copy(
                update={
                    "remaining_demand": production_demand,
                    "uncovered_demand": uncovered,
                    "recommended_lot_count": recommended_lots,
                    "recommended_start_by": (
                        queue_row.recommended_start_by if recommended_lots else None
                    ),
                    "queue_status": "ACTIVE" if recommended_lots else "CLEAR",
                }
            )
        )
    queue = tuple(adjusted_queue)
    queue_summary = validate_and_summarize_automatic_queue(queue)
    if queue_summary.configured_modalities != expected_configured_modalities:
        raise OrderNeedsError("The authoritative queue configuration is incomplete.")
    if queue_summary.wip_source_sha256 is None:
        raise OrderNeedsError("The accepted WIP source hash is unavailable.")
    queue_by_part = {item.part_number: item for item in queue}

    remaining_wip = {part: row.eligible_wip for part, row in queue_by_part.items()}
    result_rows: list[OrderNeedsRow] = []
    for (due_date, part_number, modality), values in sorted(
        grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2])
    ):
        queue_row = queue_by_part.get(part_number)
        iso_year, iso_week, _ = due_date.isocalendar()
        if queue_row is None:
            result_rows.append(
                OrderNeedsRow(
                    due_date=due_date,
                    iso_year=iso_year,
                    iso_week=iso_week,
                    part_number=part_number,
                    modality=modality,
                    order_line_count=values["lines"],
                    ordered_quantity=values["ordered"],
                    accepted_ship_quantity=values["shipped"],
                    ready_for_logistics_quantity=values["ready"],
                    remaining_demand=values["remaining"],
                    configured=False,
                    planning_status="FAIL_CLOSED",
                )
            )
            continue
        before = remaining_wip[part_number]
        covered = min(before, values["remaining"])
        uncovered = values["remaining"] - covered
        after = before - covered
        remaining_wip[part_number] = after
        planning_status = (
            "COVERED" if uncovered == 0 else "UNCOVERED" if covered == 0 else "PARTIALLY_COVERED"
        )
        result_rows.append(
            OrderNeedsRow(
                due_date=due_date,
                iso_year=iso_year,
                iso_week=iso_week,
                part_number=part_number,
                modality=modality,
                order_line_count=values["lines"],
                ordered_quantity=values["ordered"],
                accepted_ship_quantity=values["shipped"],
                ready_for_logistics_quantity=values["ready"],
                remaining_demand=values["remaining"],
                configured=True,
                planning_status=planning_status,
                eligible_wip_before=before,
                covered_by_wip=covered,
                uncovered_after_wip=uncovered,
                eligible_wip_after=after,
                lot_size=queue_row.start_quantity,
            )
        )

    product_rows: list[OrderNeedsProductSummary] = []
    for (part_number, modality), values in sorted(product_totals.items()):
        queue_row = queue_by_part.get(part_number)
        if queue_row is None:
            product_rows.append(
                OrderNeedsProductSummary(
                    part_number=part_number,
                    modality=modality,
                    configured=False,
                    planning_status="FAIL_CLOSED",
                    order_line_count=values["lines"],
                    ordered_quantity=values["ordered"],
                    accepted_ship_quantity=values["shipped"],
                    ready_for_logistics_quantity=values["ready"],
                    remaining_demand=values["remaining"],
                )
            )
            continue
        covered = min(queue_row.remaining_demand, queue_row.eligible_wip)
        product_rows.append(
            OrderNeedsProductSummary(
                part_number=part_number,
                modality=modality,
                configured=True,
                planning_status=(
                    "STARTS_REQUIRED" if queue_row.recommended_lot_count else "CLEAR"
                ),
                order_line_count=values["lines"],
                ordered_quantity=values["ordered"],
                accepted_ship_quantity=values["shipped"],
                ready_for_logistics_quantity=values["ready"],
                remaining_demand=values["remaining"],
                eligible_wip=queue_row.eligible_wip,
                covered_by_wip=covered,
                uncovered_after_wip=queue_row.uncovered_demand,
                wip_remaining_after_demand=queue_row.wip_remaining_after_demand,
                lot_size=queue_row.start_quantity,
                recommended_lot_count=queue_row.recommended_lot_count,
                recommended_start_by=queue_row.recommended_start_by,
            )
        )

    ordered_total = sum(row.ordered_quantity for row in product_rows)
    shipped_total = sum(row.accepted_ship_quantity for row in product_rows)
    ready_total = sum(row.ready_for_logistics_quantity for row in product_rows)
    remaining_total = sum(row.remaining_demand for row in product_rows)
    configured_demand = sum(
        row.remaining_demand for row in product_rows if row.configured
    )
    totals = OrderNeedsTotals(
        open_order_lines=sum(row.order_line_count for row in product_rows),
        ordered_quantity=ordered_total,
        accepted_ship_quantity=shipped_total,
        ready_for_logistics_quantity=ready_total,
        remaining_demand=remaining_total,
        configured_demand=configured_demand,
        fail_closed_demand=remaining_total - configured_demand,
        eligible_wip=queue_summary.eligible_wip,
        covered_by_wip=queue_summary.covered_by_wip,
        uncovered_after_wip=queue_summary.uncovered_after_wip,
        wip_remaining_after_demand=queue_summary.coverage_surplus,
        recommended_lot_count=queue_summary.starts_required,
    )
    return OrderNeedsResult(
        generated_at=generated_at or datetime.now(UTC),
        source=OrderNeedsSource(
            revision_sha256=revision_sha256,
            filename=str(active.get("original_filename", "")),
            revision_status="ACTIVE",
            source_row_count=int(active.get("source_row_count", 0)),
            wip_source_sha256=queue_summary.wip_source_sha256,
        ),
        totals=totals,
        products=tuple(product_rows),
        rows=tuple(result_rows),
    )


def filter_order_needs(
    rows: Sequence[OrderNeedsRow],
    *,
    part_number: str | None = None,
    modality: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[OrderNeedsRow, ...]:
    """Filter preallocated rows without recalculating or reallocating WIP."""

    if date_from and date_to and date_from > date_to:
        raise OrderNeedsError("date_from must not be later than date_to")
    return tuple(
        row
        for row in rows
        if (not part_number or row.part_number == part_number)
        and (not modality or row.modality == modality)
        and (not date_from or row.due_date >= date_from)
        and (not date_to or row.due_date <= date_to)
    )


ORDER_NEEDS_EXPORT_COLUMNS = (
    "generated_at", "os_revision_sha256", "wip_source_sha256", "due_date",
    "iso_year", "iso_week", "part_number", "modality", "order_line_count",
    "ordered_quantity", "accepted_ship_quantity", "ready_for_logistics_quantity",
    "remaining_demand",
    "configured", "planning_status", "eligible_wip_before", "covered_by_wip",
    "uncovered_after_wip", "eligible_wip_after", "lot_size",
)


def _csv_safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def export_order_needs_csv(
    result: OrderNeedsResult, rows: Sequence[OrderNeedsRow]
) -> str:
    """Export the governed, preallocated Order Needs result with provenance."""

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=ORDER_NEEDS_EXPORT_COLUMNS)
    writer.writeheader()
    for row in rows:
        record = row.model_dump(mode="json")
        record.update(
            generated_at=result.generated_at.isoformat(),
            os_revision_sha256=result.source.revision_sha256,
            wip_source_sha256=result.source.wip_source_sha256,
        )
        writer.writerow(
            {key: _csv_safe(record.get(key, "")) for key in ORDER_NEEDS_EXPORT_COLUMNS}
        )
    return "\ufeff" + output.getvalue()


class SavedRevision(BaseModel):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_filename: str = Field(min_length=1, max_length=240)
    revision_status: Literal["ACTIVE"]
    source_row_count: int = Field(ge=0, le=1000)

    model_config = ConfigDict(frozen=True, extra="forbid")


class SavedSnapshot(BaseModel):
    revision: SavedRevision
    orders: tuple[OSGridOrder, ...] = Field(max_length=1000)
    queue: tuple[AutomaticLotStartQueueState, ...] = Field(max_length=20)
    expected_configured_modalities: int = Field(ge=1, le=20)
    generated_at: datetime

    model_config = ConfigDict(frozen=True, extra="forbid")

    def active_revision(self) -> dict[str, object]:
        return self.revision.model_dump()

    def list_active_orders(self, *, limit: int = 1000) -> tuple[OSGridOrder, ...]:
        return self.orders[:limit]

    def list_automatic_lot_start_queue(
        self, *, limit: int = 20
    ) -> tuple[AutomaticLotStartQueueState, ...]:
        return self.queue[:limit]


_MAX_FILE_BYTES = 1024 * 1024


def _ordinary_file(info: os.stat_result) -> bool:
    attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT


def _unique_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise OrderNeedsError("Saved input contains duplicate JSON fields.")
    return result


def _reject_constant(_value: str) -> object:
    raise OrderNeedsError("Saved input contains an invalid JSON number.")


def _read_json(path: Path) -> object:
    try:
        selected = path.lstat()
        if not _ordinary_file(selected):
            raise OrderNeedsError("Saved input must be an ordinary file.")
        if selected.st_size > _MAX_FILE_BYTES:
            raise OrderNeedsError("Saved input exceeds the 1 MiB limit.")
        flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if not _ordinary_file(opened) or not os.path.samestat(selected, opened):
                raise OrderNeedsError("Saved input changed while opening.")
            content = stream.read(_MAX_FILE_BYTES + 1)
    except OrderNeedsError:
        raise
    except (OSError, ValueError):
        raise OrderNeedsError("Unable to read the saved input.") from None
    if len(content) > _MAX_FILE_BYTES:
        raise OrderNeedsError("Saved input exceeds the 1 MiB limit.")

    try:
        return json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_constant,
        )
    except OrderNeedsError:
        raise
    except (ArithmeticError, ValueError, RecursionError):
        raise OrderNeedsError("Saved input must contain valid UTF-8 JSON.") from None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON containing saved order and queue rows")
    parser.add_argument("--format", choices=("json", "csv"), default="json")
    parser.add_argument("--part-number")
    parser.add_argument("--modality")
    parser.add_argument("--date-from", type=date.fromisoformat)
    parser.add_argument("--date-to", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        snapshot = SavedSnapshot.model_validate(_read_json(args.input))
        result = build_order_needs(
            snapshot,
            expected_configured_modalities=snapshot.expected_configured_modalities,
            generated_at=snapshot.generated_at,
        )
        rows = filter_order_needs(
            result.rows, part_number=args.part_number, modality=args.modality,
            date_from=args.date_from, date_to=args.date_to,
        )
    except (ValueError, OverflowError):
        print("Order allocation refused. Check the snapshot and filter values.", file=sys.stderr)
        return 2
    if args.format == "csv":
        # Write UTF-8 BOM and exact CSV line endings on Windows and Linux.
        sys.stdout.buffer.write(export_order_needs_csv(result, rows).encode("utf-8"))
    else:
        report = result.model_copy(update={"rows": rows})
        sys.stdout.buffer.write((report.model_dump_json() + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
