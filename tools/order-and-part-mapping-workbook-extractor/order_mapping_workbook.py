"""Extract typed order and part-mapping rows from a checksum-pinned workbook."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from typing import Any, Literal

from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from workbook_preflight import WorkbookError, _load_workbook, inspect_workbook


ORDER_HEADERS = (
    "Order Date", "Part Number", "Customer PO", "PO Line", "Qty",
    "Requested Date", "Org", "Commit Date", "Ship Qty",
    "Ship Date", "Shipment Number", "Checked By", "Dock Date", "Lot ID(s)",
    "Lot Qty(s)", "Work Request Flow", "Carrier", "Tracking #",
    "Customer Notes", "Planning Notes", "Lead Time Calculation",
    "Admin #1 Open", "Admin #2 Used", "Admin #3 Used",
)
MAPPING_HEADERS = (
    "Mapping Code", "Customer Part", "Supplier Part", "Rev", "Unit Value", "Harmonized Code",
)


class PTLAOrderRecord(BaseModel):
    """One saved customer or panel order."""

    source_sheet: Literal["C", "P"]
    source_row: int = Field(ge=4, le=500)
    order_date: date | None = None
    part_number: str = Field(min_length=1, max_length=40)
    customer_or_oracle_po: str | None = Field(default=None, max_length=80)
    po_line: str | None = Field(default=None, max_length=30)
    quantity: int = Field(gt=0)
    ngb_etd_or_oracle_rsd: date | None = None
    organization: str | None = Field(default=None, max_length=20)
    flex_ptl_commit_date: date
    ship_quantity: int | None = Field(default=None, ge=0)
    ship_date: date | None = None
    shipment_number: str | None = Field(default=None, max_length=80)
    checked_by: str | None = Field(default=None, max_length=40)
    dock_date: date | None = None
    lot_ids: str | None = Field(default=None, max_length=2000)
    lot_quantities: str | None = Field(default=None, max_length=2000)
    work_request_flow: str | None = Field(default=None, max_length=256)
    carrier: str | None = Field(default=None, max_length=80)
    tracking_number: str | None = Field(default=None, max_length=120)
    customer_notes: str | None = Field(default=None, max_length=4000)
    ptl_notes: str | None = Field(default=None, max_length=4000)
    lead_time_calculation: date | str | None = None
    admin_1_open: str | None = Field(default=None, max_length=40)
    admin_2_used: str | None = Field(default=None, max_length=40)
    admin_3_used: str | None = Field(default=None, max_length=40)

    model_config = ConfigDict(frozen=True)


class PTLAMappingRecord(BaseModel):
    """One part mapping from the workbook Mapping sheet."""

    source_row: int = Field(ge=4, le=500)
    source_sheet: Literal["Mapping"] = "Mapping"
    mapping_code: str = Field(min_length=1, max_length=40)
    customer_part_number: str = Field(min_length=1, max_length=40)
    supplier_part_number: str = Field(min_length=1, max_length=120)
    revision: str = Field(min_length=1, max_length=20)
    unit_value: Decimal = Field(ge=0)
    harmonized_code: str = Field(min_length=1, max_length=40)
    production_revision: int | None = Field(default=None, ge=0)
    validation_revision: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(frozen=True)


class PTLAInputContractError(ValueError):
    """The workbook failed its extraction contract."""


class PTLAInputHashMismatch(PTLAInputContractError):
    """The workbook did not match the supplied SHA-256."""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).split()).strip()
    return normalized or None


def _integer(value: Any, *, allow_none: bool = True) -> int | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise PTLAInputContractError("A required numeric workbook value is blank.")
    if isinstance(value, bool):
        raise PTLAInputContractError("A Boolean workbook value cannot be a quantity.")
    try:
        number = Decimal(str(value))
    except Exception as exc:
        raise PTLAInputContractError("A workbook quantity is not numeric.") from exc
    if not number.is_finite() or abs(number) > 2**53 - 1:
        raise PTLAInputContractError("A numeric value exceeds the supported integer range.")
    if number != number.to_integral_value():
        raise PTLAInputContractError("A workbook quantity is not a whole number.")
    return int(number)


def _date(value: Any, *, allow_none: bool = True) -> date | None:
    if value is None or value == "":
        if allow_none:
            return None
        raise PTLAInputContractError("A required workbook date is blank.")
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        converted = from_excel(value)
        if isinstance(converted, datetime):
            return converted.date()
    raise PTLAInputContractError("A workbook date is not a supported Excel date.")


def _date_or_text(value: Any) -> date | str | None:
    """Preserve cached formula errors while typing valid Excel dates."""

    if value is None or value == "":
        return None
    if isinstance(value, (date, datetime, int, float)) and not isinstance(value, bool):
        return _date(value)
    return _text(value)


def _assert_headers(actual: tuple[Any, ...], expected: tuple[str, ...]) -> None:
    normalized = tuple((_text(value) or "").replace("WIP ", "WIP") for value in actual)
    if normalized != expected:
        raise PTLAInputContractError("A PTLA workbook header contract changed.")


def _load_orders(
    workbook: Any,
    sheet_name: str,
    *,
    expected_count: int | None,
) -> tuple[PTLAOrderRecord, ...]:
    if sheet_name not in workbook.sheetnames:
        raise PTLAInputContractError("A required PTLA order sheet is missing.")
    sheet = workbook[sheet_name]
    if sheet.max_row is None or not 3 <= sheet.max_row <= 500:
        raise PTLAInputContractError("Order sheet dimensions exceed the supported row bounds.")
    _assert_headers(tuple(sheet.iter_rows(min_row=3, max_row=3, min_col=2, max_col=25, values_only=True))[0], ORDER_HEADERS)
    records: list[PTLAOrderRecord] = []
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=25, values_only=True),
        start=4,
    ):
        part_number, quantity, commit_date = row[2], row[5], row[8]
        if part_number in (None, "") or quantity in (None, "") or commit_date in (None, ""):
            continue
        try:
            records.append(PTLAOrderRecord(
                source_sheet=sheet_name,
                source_row=row_number,
                order_date=_date(row[1]),
                part_number=_text(part_number) or "",
                customer_or_oracle_po=_text(row[3]),
                po_line=_text(row[4]),
                quantity=_integer(quantity, allow_none=False),
                ngb_etd_or_oracle_rsd=_date(row[6]),
                organization=_text(row[7]),
                flex_ptl_commit_date=_date(commit_date, allow_none=False),
                ship_quantity=_integer(row[9]),
                ship_date=_date(row[10]),
                shipment_number=_text(row[11]),
                checked_by=_text(row[12]),
                dock_date=_date(row[13]),
                lot_ids=_text(row[14]),
                lot_quantities=_text(row[15]),
                work_request_flow=_text(row[16]),
                carrier=_text(row[17]),
                tracking_number=_text(row[18]),
                customer_notes=_text(row[19]),
                ptl_notes=_text(row[20]),
                lead_time_calculation=_date_or_text(row[21]),
                admin_1_open=_text(row[22]),
                admin_2_used=_text(row[23]),
                admin_3_used=_text(row[24]),
            ))
        except (ValidationError, PTLAInputContractError) as exc:
            raise PTLAInputContractError(
                f"The {sheet_name} order contract failed at source row {row_number}."
            ) from exc
    if expected_count is not None and len(records) != expected_count:
        raise PTLAInputContractError("A frozen PTLA order count changed.")
    if len(records) > 497:
        raise PTLAInputContractError("A PTLA order sheet exceeds the bounded row limit.")
    business_keys = {
        (
            record.part_number,
            record.customer_or_oracle_po,
            record.po_line,
            record.quantity,
            record.flex_ptl_commit_date,
        )
        for record in records
    }
    if len(business_keys) != len(records):
        raise PTLAInputContractError("The frozen PTLA orders contain duplicate keys.")
    return tuple(records)


def _load_mappings(
    workbook: Any,
    *,
    expected_count: int | None,
) -> tuple[PTLAMappingRecord, ...]:
    if "Mapping" not in workbook.sheetnames:
        raise PTLAInputContractError("The required PTLA mapping sheet is missing.")
    sheet = workbook["Mapping"]
    if sheet.max_row is None or not 3 <= sheet.max_row <= 100:
        raise PTLAInputContractError("Mapping sheet dimensions exceed the supported row bounds.")
    _assert_headers(tuple(sheet.iter_rows(min_row=3, max_row=3, min_col=2, max_col=7, values_only=True))[0], MAPPING_HEADERS)
    records: list[PTLAMappingRecord] = []
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=4, max_row=sheet.max_row, min_col=1, max_col=11, values_only=True),
        start=4,
    ):
        if row[1] in (None, "") or row[2] in (None, ""):
            continue
        try:
            records.append(PTLAMappingRecord(
                source_row=row_number,
                mapping_code=_text(row[1]) or "",
                customer_part_number=_text(row[2]) or "",
                supplier_part_number=_text(row[3]) or "",
                revision=_text(row[4]) or "",
                unit_value=Decimal(str(row[5])),
                harmonized_code=_text(row[6]) or "",
                production_revision=_integer(row[9]),
                validation_revision=_integer(row[10]),
            ))
        except (ValidationError, ValueError, ArithmeticError) as exc:
            raise PTLAInputContractError(
                f"The PTLA mapping contract failed at source row {row_number}."
            ) from exc
    if expected_count is not None and len(records) != expected_count:
        raise PTLAInputContractError("The frozen PTLA mapping count changed.")
    if len({record.mapping_code for record in records}) != len(records):
        raise PTLAInputContractError("The frozen PTLA mapping contains duplicate mapping codes.")
    return tuple(records)


def extract(path: Path, expected_sha256: str) -> tuple[
    tuple[PTLAOrderRecord, ...], tuple[PTLAOrderRecord, ...], tuple[PTLAMappingRecord, ...],
]:
    if re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256) is None:
        raise PTLAInputContractError("Supply a 64-character SHA-256 digest.")
    content = _load_workbook(path)
    if sha256(content).hexdigest() != expected_sha256.lower():
        raise PTLAInputHashMismatch("The order workbook failed its checksum gate.")
    inspect_workbook(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            return (_load_orders(workbook, "C", expected_count=None),
                    _load_orders(workbook, "P", expected_count=None),
                    _load_mappings(workbook, expected_count=None))
        finally:
            workbook.close()
    except PTLAInputContractError:
        raise
    except Exception as exc:
        raise PTLAInputContractError("The order workbook could not be read safely.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sha256", required=True, help="Trusted expected workbook digest")
    args = parser.parse_args()
    try:
        customer, panel, mappings = extract(args.workbook, args.sha256)
    except (PTLAInputContractError, WorkbookError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("The order workbook is unavailable.", file=sys.stderr)
        return 2
    print(json.dumps({
        "source_sha256": args.sha256.lower(),
        "customer_orders": [row.model_dump(mode="json") for row in customer],
        "panel_orders": [row.model_dump(mode="json") for row in panel],
        "mappings": [row.model_dump(mode="json") for row in mappings],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
