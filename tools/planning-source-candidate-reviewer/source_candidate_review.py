"""Review a saved orders, WIP, and lot-start candidate bundle without writes."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import sys
from typing import Annotated, Any, Iterable, Literal
from zipfile import BadZipFile

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from order_mapping_workbook import PTLAInputContractError, PTLAOrderRecord, extract_verified_workbook
from workbook_preflight import MAX_WORKBOOK_BYTES, WorkbookError, inspect_workbook


EXPECTED_FILES = ("orders.xlsx", "wip.csv", "lot-log.xlsx", "last-lot.xlsx")
WIP_HEADERS = (
    "Material Id", "Material Name", "Circuits", "PriCircuits", "Step",
    "Date Entered Step", "Product", "Resource", "Priority", "Hold Reason",
    "Hold Reason Comment", "Date Started",
)
LOT_ID_PATTERN = re.compile(r"[A-Z0-9]{10}")
MAX_JSON_BYTES = 2 * 1024 * 1024


class SourceCandidateError(ValueError):
    """The saved candidate bundle could not be verified."""


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Source(ContractModel):
    filename: str
    bytes: Annotated[int, Field(gt=0, le=MAX_WORKBOOK_BYTES)]
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ExpectedPanelRow(ContractModel):
    source_row: Annotated[int, Field(ge=4, le=500)]
    quantity: int
    row_id: Annotated[str, Field(pattern=r"^[a-f0-9]{24}$")]


class CandidateManifest(ContractModel):
    status: Literal["PRESERVED_PENDING_SOURCE_REVIEW"]
    production_included: bool
    sources: Annotated[list[Source], Field(min_length=4, max_length=4)]
    order_counts: tuple[int, int, int]
    panel_identities: dict[str, ExpectedPanelRow]
    panel_products: list[str]
    wip_count: Annotated[int, Field(ge=1, le=5000)]
    log_count: Annotated[int, Field(ge=1, le=5000)]
    registry_count: Annotated[int, Field(ge=1, le=500)]
    overlap_year: Annotated[int, Field(ge=1900, le=9999)]
    overlap_after_month: Annotated[int, Field(ge=1, le=12)]

    @field_validator("production_included")
    @classmethod
    def reference_only(cls, value: bool) -> bool:
        if value:
            raise ValueError("A candidate manifest must be reference-only.")
        return value


class SavedBaseline(ContractModel):
    orders: Annotated[list[PTLAOrderRecord], Field(max_length=1000)]


def _read(path: Path, limit: int) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise SourceCandidateError("A required input is unavailable.")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise SourceCandidateError("An input exceeds its size limit.")
    return content


def _verified_sources(directory: Path) -> tuple[CandidateManifest, dict[str, bytes]]:
    try:
        manifest = CandidateManifest.model_validate_json(_read(directory / "manifest.json", MAX_JSON_BYTES))
        if tuple(item.filename for item in manifest.sources) != EXPECTED_FILES:
            raise SourceCandidateError("The candidate manifest has changed.")
        content = {}
        for item in manifest.sources:
            try:
                data = _read(directory / item.filename, item.bytes)
            except SourceCandidateError as exc:
                raise SourceCandidateError("A preserved candidate file is unavailable.") from exc
            if len(data) != item.bytes:
                raise SourceCandidateError("A preserved candidate file is unavailable.")
            if sha256(data).hexdigest() != item.sha256:
                raise SourceCandidateError("A preserved candidate checksum changed.")
            content[item.filename] = data
    except (OSError, ValidationError) as exc:
        raise SourceCandidateError("The candidate manifest or one of its files is unavailable.") from exc
    return manifest, content


def _row_id(order: PTLAOrderRecord) -> str:
    key = "|".join((order.source_sheet, str(order.source_row), order.part_number,
                    order.customer_or_oracle_po or "", order.po_line or ""))
    return sha256(key.encode("utf-8")).hexdigest()[:24]


def _registry(content: bytes, expected_count: int) -> tuple[tuple[str, str], ...]:
    inspect_workbook(content)
    book = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
    try:
        if book.sheetnames != ["LastLotStarted"] or book.active.max_row is None or book.active.max_row > 502:
            raise SourceCandidateError("The last-lot workbook sheet or row bounds changed.")
        rows = book.active.iter_rows(min_row=2, max_col=6, values_only=True)
        headers = ("Product Group", "Material Template", "Prefix", "Last Lot Started", None, "Next Lot To Start")
        if next(rows, None) != headers:
            raise SourceCandidateError("The last-lot headers changed.")
        records = [(str(row[2]).strip(), str(row[3] or "").strip(), str(row[5] or "").strip())
                   for row in rows if row[2] and str(row[2]).strip()]
    finally:
        book.close()
    if len(records) != expected_count or any(not row[1] or not row[2] for row in records):
        raise SourceCandidateError("The last-lot records changed.")
    if any(len(set(column)) != expected_count for column in zip(*records)):
        raise SourceCandidateError("The last-lot identifiers are not unique.")
    return tuple((prefix, following) for prefix, _, following in records)


def _whole_number(value: str, *, line: int, field: str) -> int:
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise SourceCandidateError(f"WIP line {line} has an invalid {field}.") from exc
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise SourceCandidateError(f"WIP line {line} has an invalid {field}.")
    if number > 10**12:
        raise SourceCandidateError(f"WIP line {line} has an out-of-range {field}.")
    return int(number)


def _business_key(order: Any) -> tuple[Any, ...]:
    commit_date = order.flex_ptl_commit_date
    return (
        order.part_number,
        order.customer_or_oracle_po,
        order.po_line,
        order.quantity,
        commit_date.isoformat() if hasattr(commit_date, "isoformat") else commit_date,
    )


def inspect_source_candidates(
    data_root: Path,
    *,
    active_orders: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Verify original bytes, parse bounded evidence, and compare without writes."""

    manifest, content = _verified_sources(data_root)
    customer, panel, mappings = extract_verified_workbook(content["orders.xlsx"])
    if (len(customer), len(panel), len(mappings)) != manifest.order_counts:
        raise SourceCandidateError("The candidate order row counts changed.")
    panel_ids = {
        order.part_number: ExpectedPanelRow(
            source_row=order.source_row, quantity=order.quantity, row_id=_row_id(order)
        )
        for order in panel
    }
    if len(panel_ids) != len(panel) or panel_ids != manifest.panel_identities:
        raise SourceCandidateError("The exact panel row identities changed.")

    order_comparison = None
    if active_orders is not None:
        customer_baseline = tuple(order for order in active_orders if order.source_sheet == "C")
        active = {_business_key(order): order for order in customer_baseline}
        if len(active) != len(customer_baseline):
            raise SourceCandidateError("The baseline contains duplicate customer order keys.")
        candidate = {_business_key(order): order for order in customer}
        matching = candidate.keys() & active.keys()
        order_comparison = {
            "active_rows": len(active),
            "candidate_rows": len(candidate),
            "added": len(candidate.keys() - active.keys()),
            "removed": len(active.keys() - candidate.keys()),
            "moved_source_rows": sum(
                candidate[key].source_row != active[key].source_row for key in matching
            ),
            "shipping_updates": sum(
                candidate[key].ship_quantity != active[key].ship_quantity
                or candidate[key].ship_date != active[key].ship_date
                for key in matching
            ),
            "dock_updates": sum(
                candidate[key].dock_date != active[key].dock_date
                for key in matching
            ),
            "added_orders": tuple(
                {
                    "source_row": candidate[key].source_row,
                    "part_number": candidate[key].part_number,
                    "quantity": candidate[key].quantity,
                    "commit_date": candidate[key].flex_ptl_commit_date.isoformat(),
                }
                for key in sorted(candidate.keys() - active.keys(), key=str)
            ),
        }

    wip_rows: list[dict[str, Any]] = []
    with StringIO(content["wip.csv"].decode("utf-8-sig"), newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != WIP_HEADERS:
            raise SourceCandidateError("The WIP CSV header contract changed.")
        for line, row in enumerate(reader, start=2):
            if not row["Material Id"] or not row["Material Name"] or not row["Product"]:
                raise SourceCandidateError(f"WIP line {line} has a missing identity.")
            if row.get(None):
                raise SourceCandidateError(f"WIP line {line} has extra columns.")
            try:
                started = datetime.strptime(row["Date Started"], "%m/%d/%Y %I:%M %p")
            except (ValueError, TypeError) as exc:
                raise SourceCandidateError(f"WIP line {line} has an invalid start date.") from exc
            if len(wip_rows) >= manifest.wip_count or any(value is None for value in row.values()):
                raise SourceCandidateError("The WIP CSV row shape or count changed.")
            wip_rows.append({
                "material_id": row["Material Id"],
                "lot_id": row["Material Name"],
                "product": row["Product"],
                "step": row["Step"],
                "circuits": _whole_number(row["Circuits"], line=line, field="Circuits"),
                "primary_circuits": _whole_number(
                    row["PriCircuits"], line=line, field="PriCircuits"
                ),
                "hold_reason": row["Hold Reason"],
                "started": started,
            })
    if len(wip_rows) != manifest.wip_count or len({row["material_id"] for row in wip_rows}) != manifest.wip_count:
        raise SourceCandidateError("The WIP CSV material identity contract changed.")
    if len({row["lot_id"] for row in wip_rows}) != manifest.wip_count:
        raise SourceCandidateError("The WIP CSV lot identities are not unique.")

    inspect_workbook(content["lot-log.xlsx"])
    workbook = load_workbook(BytesIO(content["lot-log.xlsx"]), read_only=True, data_only=True, keep_links=False)
    try:
        if workbook.sheetnames != ["LotStartLog"]:
            raise SourceCandidateError("The lot-start log sheet changed.")
        sheet = workbook.active
        if sheet.max_row is None or not 5 <= sheet.max_row <= 5004 or sheet.max_column is None or sheet.max_column > 50:
            raise SourceCandidateError("The lot-start log sheet dimensions changed.")
        months = tuple(
            value for value in next(sheet.iter_rows(min_row=3, max_row=3, values_only=True))
            if isinstance(value, int)
        )
        log_lots = {
            row[3]
            for row in sheet.iter_rows(min_row=5, values_only=True)
            if len(row) > 3 and isinstance(row[3], str)
            and LOT_ID_PATTERN.fullmatch(row[3])
        }
    finally:
        workbook.close()
    if len(log_lots) != manifest.log_count:
        raise SourceCandidateError("The lot-start log material count changed.")
    observed_lots = log_lots | {
        row["lot_id"] for row in wip_rows if LOT_ID_PATTERN.fullmatch(row["lot_id"])
    }
    last_lots = _registry(content["last-lot.xlsx"], manifest.registry_count)
    collisions = tuple(sorted({prefix for prefix, following in last_lots if following in observed_lots}))
    later_overlaps = sum(
        row["lot_id"] in log_lots and row["started"].year == manifest.overlap_year
        and row["started"].month > manifest.overlap_after_month
        for row in wip_rows
    )

    held = [row for row in wip_rows if row["hold_reason"]]
    internal = [row for row in wip_rows if row["product"] in manifest.panel_products]
    return {
        "manifest": manifest.model_dump(mode="json"),
        "orders": {
            "customer_count": len(customer),
            "panel_count": len(panel),
            "mapping_count": len(mappings),
            "exact_panel_identities_present": True,
            "comparison": order_comparison,
        },
        "wip": {
            "row_count": len(wip_rows),
            "raw_circuits": sum(row["circuits"] for row in wip_rows),
            "primary_circuits": sum(row["primary_circuits"] for row in wip_rows),
            "held_rows": len(held),
            "held_circuits": sum(row["circuits"] for row in held),
            "panel_rows": len(internal),
            "panel_circuits": sum(row["circuits"] for row in internal),
            "held_lots": tuple({
                "lot_id": row["lot_id"],
                "circuits": row["circuits"],
                "primary_circuits": row["primary_circuits"],
                "reason": row["hold_reason"],
            } for row in held),
        },
        "lot_log": {
            "material_count": len(log_lots),
            "visible_months": months,
            "wip_lots_started_after_cutoff": later_overlaps,
            "registry_next_id_collisions": collisions,
        },
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory with manifest.json and the four inputs")
    parser.add_argument("--baseline", type=Path, help="Optional saved JSON file containing an orders array")
    args = parser.parse_args()
    try:
        baseline = (SavedBaseline.model_validate_json(_read(args.baseline, MAX_JSON_BYTES)).orders
                    if args.baseline is not None else None)
        result = inspect_source_candidates(args.directory, active_orders=baseline)
    except (SourceCandidateError, PTLAInputContractError, WorkbookError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, BadZipFile, csv.Error):
        print("A candidate or baseline file could not be read.", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
