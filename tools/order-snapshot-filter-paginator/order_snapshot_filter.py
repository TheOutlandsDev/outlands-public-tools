"""Filter and paginate an already projected saved order snapshot."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


OrderStatus = Literal["Open", "Shipped", "Docked"]
DateField = Literal["order_date", "requested_ship_date", "commit_date", "ship_date"]
Sheet = Literal["C", "P"]


class SavedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class OrderRow(SavedRecord):
    row_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    source_sheet: Sheet
    source_row: int = Field(ge=4, le=500)
    part_number: str = Field(min_length=1)
    modality: str = Field(default="UNMAPPED", min_length=1, max_length=40)
    status: OrderStatus
    quantity: int = Field(gt=0)
    order_date: date | None = None
    requested_ship_date: date | None = None
    commit_date: date
    ship_date: date | None = None
    purchase_order: str | None = None
    po_line: str | None = None
    lot_ids: str | None = None
    lot_quantities: str | None = None
    work_request_flow: str | None = None
    shipment_number: str | None = None
    carrier: str | None = None
    tracking_number: str | None = None
    customer_notes: str | None = None
    planning_notes: str | None = None
    flex_handoff_state: str = "IN_PRODUCTION"
    flex_ready_lot_ids: str | None = None
    flex_ready_by: str | None = None
    logistics_mes_status: str = "NOT_READY_FOR_LOGISTICS"
    row_version: int | None = Field(default=None, gt=0)


class SavedSnapshot(SavedRecord):
    revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    revision_filename: str = Field(min_length=1, max_length=240)
    revision_status: str = Field(min_length=1, max_length=80)
    available_modalities: tuple[str, ...] = Field(default=(), max_length=40)
    rows: tuple[OrderRow, ...] = Field(max_length=1000)


class OrderPage(BaseModel):
    model_config = ConfigDict(frozen=True)

    revision_sha256: str
    revision_filename: str
    revision_status: str
    available_modalities: tuple[str, ...] = Field(max_length=40)
    selected_modalities: tuple[str, ...] = Field(max_length=40)
    total_rows: int = Field(ge=0, le=1000)
    filtered_rows: int = Field(ge=0, le=1000)
    page: int = Field(ge=1)
    page_size: int = Field(ge=10, le=200)
    page_count: int = Field(ge=0)
    rows: tuple[OrderRow, ...] = Field(max_length=200)


def _newest_order_first(row: OrderRow) -> tuple[bool, int, str, str, int]:
    """Place newest order dates first and undated rows last deterministically."""

    return (
        row.order_date is None,
        -(row.order_date.toordinal()) if row.order_date is not None else 0,
        row.part_number,
        row.source_sheet,
        row.source_row,
    )


def filter_order_snapshot(
    snapshot: SavedSnapshot,
    *,
    search: str | None = None,
    sheet: Sheet | None = None,
    modalities: tuple[str, ...] = (),
    status: OrderStatus | None = None,
    page: int = 1,
    page_size: int = 200,
    date_field: DateField = "order_date",
    date_from: date | None = None,
    date_to: date | None = None,
) -> OrderPage:
    """Filter and paginate saved rows with their supplied revision provenance."""
    if page < 1 or not 10 <= page_size <= 200:
        raise ValueError("Page must be positive and page size must be between 10 and 200.")

    rows = list(snapshot.rows)
    total_rows = len(rows)
    available = tuple(sorted(set(snapshot.available_modalities) | {row.modality for row in rows}))
    if set(modalities) - set(available):
        raise ValueError("An unknown modality was requested.")
    normalized_search = " ".join((search or "").split()).casefold()

    if date_from and date_to and date_from > date_to:
        raise ValueError("The beginning of the date range must not follow its end.")

    if sheet:
        rows = [row for row in rows if row.source_sheet == sheet]
    if modalities:
        rows = [row for row in rows if row.modality in modalities]
    if status:
        rows = [row for row in rows if row.status == status]
    if date_from:
        rows = [
            row for row in rows
            if (value := getattr(row, date_field)) is not None and value >= date_from
        ]
    if date_to:
        rows = [
            row for row in rows
            if (value := getattr(row, date_field)) is not None and value <= date_to
        ]
    if normalized_search:
        rows = [
            row
            for row in rows
            if normalized_search
            in " ".join(
                value
                for value in (
                    row.part_number,
                    row.modality,
                    str(row.order_date or ""),
                    row.purchase_order or "",
                    row.po_line or "",
                    row.lot_ids or "",
                    row.lot_quantities or "",
                    row.work_request_flow or "",
                    row.shipment_number or "",
                    row.carrier or "",
                    row.tracking_number or "",
                    row.customer_notes or "",
                    row.planning_notes or "",
                    row.flex_handoff_state,
                    row.flex_ready_lot_ids or "",
                    row.flex_ready_by or "",
                    row.logistics_mes_status,
                )
                if value
            ).casefold()
        ]
    rows.sort(key=_newest_order_first)
    filtered_rows = len(rows)
    page_count = (filtered_rows + page_size - 1) // page_size if filtered_rows else 0
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size] if page <= page_count else []
    return OrderPage(
        revision_sha256=snapshot.revision_sha256,
        revision_filename=snapshot.revision_filename,
        revision_status=snapshot.revision_status,
        available_modalities=available,
        selected_modalities=modalities,
        total_rows=total_rows,
        filtered_rows=filtered_rows,
        page=page,
        page_size=page_size,
        page_count=page_count,
        rows=tuple(page_rows),
    )


def iso_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected a date in YYYY-MM-DD format")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Saved order snapshot in JSON")
    parser.add_argument("--search")
    parser.add_argument("--sheet", choices=("C", "P"))
    parser.add_argument("--modality", action="append", default=[], help="Repeat to select multiple modalities.")
    parser.add_argument("--status", choices=("Open", "Shipped", "Docked"))
    parser.add_argument("--date-field", choices=("order_date", "requested_ship_date", "commit_date", "ship_date"),
                        default="order_date")
    parser.add_argument("--date-from", type=iso_date)
    parser.add_argument("--date-to", type=iso_date)
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--page-size", type=int, default=200)
    args = parser.parse_args()

    try:
        snapshot = SavedSnapshot.model_validate_json(args.snapshot.read_bytes())
        result = filter_order_snapshot(
            snapshot, search=args.search, sheet=args.sheet, modalities=tuple(args.modality),
            status=args.status, page=args.page, page_size=args.page_size,
            date_field=args.date_field, date_from=args.date_from, date_to=args.date_to,
        )
    except (OSError, ValidationError):
        print("The saved order snapshot or result limits are invalid.", file=sys.stderr)
        return 2
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
