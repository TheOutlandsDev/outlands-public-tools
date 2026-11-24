"""Extract last-lot mappings from a saved XLSX workbook."""

import argparse
from contextlib import closing
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict

from workbook_preflight import WorkbookError, _load_workbook, inspect_workbook


DEFAULT_SHEET = "LastLotStarted"


class LastLotWorkbookError(ValueError):
    """The workbook could not supply a valid set of last-lot mappings."""


class LastLotMapping(BaseModel):
    product: str | None
    material_template: str | None
    prefix: str
    last_lot_started: str
    next_lot_to_start: str

    model_config = ConfigDict(frozen=True)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    result = " ".join(str(value).split()).strip()
    return result or None


def load_last_lot_contract(
    path: Path, *, sheet_name: str = DEFAULT_SHEET,
) -> tuple[LastLotMapping, ...]:
    """Read the fixed last-lot table and preserve the workbook's order."""
    if path.suffix.lower() != ".xlsx":
        raise LastLotWorkbookError("An .xlsx workbook is required.")
    try:
        content = _load_workbook(path)
        inspect_workbook(content)
    except WorkbookError as exc:
        raise LastLotWorkbookError(str(exc)) from exc
    except OSError as exc:
        raise LastLotWorkbookError("The last-lot workbook could not be read.") from exc

    try:
        with closing(load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)) as workbook:
            if workbook.sheetnames != [sheet_name]:
                raise LastLotWorkbookError("The workbook must contain only the selected last-lot worksheet.")
            rows = list(workbook[sheet_name].iter_rows(
                min_row=2, max_row=23, min_col=1, max_col=6, values_only=True,
            ))
    except LastLotWorkbookError:
        raise
    except Exception as exc:
        raise LastLotWorkbookError("The last-lot workbook is invalid.") from exc

    if not rows or tuple(_text(value) for value in rows[0]) != (
        "Product Group", "Material Template", "Prefix", "Last Lot Started", None,
        "Next Lot To Start",
    ):
        raise LastLotWorkbookError("last-lot headers changed")
    records = tuple(
        LastLotMapping(
            product=_text(row[0]),
            material_template=_text(row[1]),
            prefix=_text(row[2]) or "",
            last_lot_started=_text(row[3]) or "",
            next_lot_to_start=_text(row[5]) or "",
        )
        for row in rows[1:]
        if _text(row[2])
    )
    if len(records) != 21:
        raise LastLotWorkbookError("last-lot record count changed")
    for attribute in ("prefix", "last_lot_started", "next_lot_to_start"):
        values = [getattr(item, attribute) for item in records]
        if len(values) != len(set(values)):
            raise LastLotWorkbookError(f"last-lot {attribute} is not unique")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="Name of the sole worksheet")
    args = parser.parse_args()
    try:
        rows = load_last_lot_contract(args.workbook, sheet_name=args.sheet)
    except LastLotWorkbookError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"last_lots": [row.model_dump() for row in rows]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
