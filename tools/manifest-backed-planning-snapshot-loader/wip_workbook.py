"""Extract typed rows from a checksum-pinned repeated-block inventory workbook."""

from __future__ import annotations

import argparse
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import sys
from typing import Any

from openpyxl import load_workbook
from pydantic import ValidationError

from wip_supply import FPCWIPRecord
from workbook_preflight import WorkbookError, _load_workbook, inspect_workbook


INVENTORY_HEADERS = (
    "Material Name", "Priority", "Step Name", "Product Name", "Comment", "WIP",
    "@FPC Packaging", "QA/FAR", "Pack & Ship", "Kanban",
)


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


def _assert_headers(actual: tuple[Any, ...], expected: tuple[str, ...]) -> None:
    normalized = tuple((_text(value) or "").replace("WIP ", "WIP") for value in actual)
    if normalized != expected:
        raise PTLAInputContractError("A PTLA workbook header contract changed.")


def _load_wip(
    workbook: Any,
    *,
    expected_count: int | None,
) -> tuple[FPCWIPRecord, ...]:
    sheet_name = "FPC_Production_Inventory"
    if sheet_name not in workbook.sheetnames:
        raise PTLAInputContractError("The required FPC inventory sheet is missing.")
    sheet = workbook[sheet_name]
    if sheet.max_row is None or not 1 <= sheet.max_row <= 10_000:
        raise PTLAInputContractError("Inventory sheet dimensions exceed the supported row bounds.")
    records: list[FPCWIPRecord] = []
    header_blocks = 0
    for row_number, row in enumerate(
        sheet.iter_rows(min_row=1, max_row=sheet.max_row, min_col=1, max_col=11, values_only=True),
        start=1,
    ):
        material = _text(row[1])
        if material == "Material Name":
            _assert_headers(row[1:11], INVENTORY_HEADERS)
            header_blocks += 1
            continue
        if not material or material == "Total" or not _text(row[3]) or not _text(row[4]):
            continue
        try:
            records.append(FPCWIPRecord(
                source_row=row_number,
                material_name=material,
                priority=_integer(row[2]),
                step_name=_text(row[3]) or "",
                product_name=_text(row[4]) or "",
                comment=_text(row[5]),
                wip_quantity=_integer(row[6]),
                packaging_quantity=_integer(row[7]),
                qa_far_quantity=_integer(row[8]),
                pack_and_ship_quantity=_integer(row[9]),
                kanban_quantity=_integer(row[10]),
            ))
        except (ValidationError, PTLAInputContractError) as exc:
            raise PTLAInputContractError(
                f"The FPC inventory contract failed at source row {row_number}."
            ) from exc
    if header_blocks != 26:
        raise PTLAInputContractError("The frozen FPC inventory structure changed.")
    if expected_count is not None and len(records) != expected_count:
        raise PTLAInputContractError("The frozen FPC inventory count changed.")
    if len({record.material_name for record in records}) != len(records):
        raise PTLAInputContractError("The frozen FPC inventory contains duplicate material identifiers.")
    return tuple(records)


def extract(path: Path, expected_sha256: str, *, expected_count: int | None = None) -> tuple[FPCWIPRecord, ...]:
    if re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256) is None:
        raise PTLAInputContractError("Supply a 64-character SHA-256 digest.")
    if expected_count is not None and not 0 <= expected_count <= 10_000:
        raise PTLAInputContractError("Expected row count must be between 0 and 10000.")
    content = _load_workbook(path)
    if sha256(content).hexdigest() != expected_sha256.lower():
        raise PTLAInputHashMismatch("The inventory workbook failed its checksum gate.")
    return extract_verified_inventory(content, expected_count=expected_count)


def extract_verified_inventory(content: bytes, *, expected_count: int | None = None) -> tuple[FPCWIPRecord, ...]:
    inspect_workbook(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            return _load_wip(workbook, expected_count=expected_count)
        finally:
            workbook.close()
    except PTLAInputContractError:
        raise
    except Exception as exc:
        raise PTLAInputContractError("The inventory workbook could not be read safely.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sha256", required=True, help="Trusted expected workbook digest")
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    try:
        records = extract(args.workbook, args.sha256, expected_count=args.expected_count)
    except (PTLAInputContractError, WorkbookError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError:
        print("The inventory workbook is unavailable.", file=sys.stderr)
        return 2
    print(json.dumps({
        "source_sha256": args.sha256.lower(), "record_count": len(records),
        "records": [row.model_dump(mode="json") for row in records],
    }, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
