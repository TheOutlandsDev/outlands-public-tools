"""Extract nonblank rows under a declared header from a saved XLSX worksheet."""

import argparse
from datetime import date, time, timedelta
import json
from pathlib import Path
import sys
from typing import Any
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from defusedxml.common import DefusedXmlException
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class WorksheetError(ValueError):
    """The worksheet does not match the requested header."""


def _text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = " ".join(str(value).replace("\n", " ").split()).strip()
    return normalized or None


def _sheet_rows(path: Path, source: dict[str, Any]) -> list[tuple[int, list[Any]]]:
    workbook = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        sheet = workbook[source["sheet_name"]]
        if sheet.max_row is None or sheet.max_column is None:
            sheet.calculate_dimension(force=True)
        if sheet.max_row is None:
            raise WorksheetError("A controlled snapshot has no readable rows.")
        headers = tuple(source["expected_headers"])
        start = int(source["header_start_column"])
        header_row = None
        for row_number in range(1, min(sheet.max_row, 20) + 1):
            actual = tuple(
                _text(sheet.cell(row=row_number, column=start + offset).value) or ""
                for offset in range(len(headers))
            )
            if actual == headers:
                header_row = row_number
                break
        if header_row is None:
            raise WorksheetError("A controlled snapshot header changed.")
        rows: list[tuple[int, list[Any]]] = []
        for row_number, cells in enumerate(
            sheet.iter_rows(
                min_row=header_row + 1,
                max_row=sheet.max_row,
                min_col=start,
                max_col=start + len(headers) - 1,
                values_only=True,
            ),
            start=header_row + 1,
        ):
            values = list(cells)
            if any(_text(value) for value in values):
                rows.append((row_number, values))
        return rows
    finally:
        workbook.close()


def encode_cell(value):
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    raise TypeError("Unsupported worksheet cell value")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", required=True)
    parser.add_argument("--header-start-column", type=int, default=1,
                        help="One-based index of the first declared header (default: 1)")
    parser.add_argument("--header", required=True, action="append",
                        help="Expected header text. Repeat in worksheet column order.")
    args = parser.parse_args()
    if (args.workbook.suffix.lower() != ".xlsx" or not args.sheet
            or args.header_start_column < 1
            or args.header_start_column + len(args.header) - 1 > 16384):
        parser.error("Expected an XLSX file, sheet name, and headers within columns 1-16384.")

    try:
        rows = _sheet_rows(args.workbook, {
            "sheet_name": args.sheet,
            "expected_headers": args.header,
            "header_start_column": args.header_start_column,
        })
        report = json.dumps({"rows": [
            {"source_row": number, "values": values} for number, values in rows
        ]}, default=encode_cell, allow_nan=False)
    except WorksheetError as error:
        print(str(error), file=sys.stderr)
        return 2
    except KeyError:
        print("The requested worksheet or required workbook part is missing.", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, BadZipFile, InvalidFileException, ParseError, DefusedXmlException):
        print("The input could not be read as an XLSX worksheet.", file=sys.stderr)
        return 2

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
