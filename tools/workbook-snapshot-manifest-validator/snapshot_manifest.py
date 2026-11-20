"""Verify saved XLSX snapshots against a local checksum and worksheet manifest."""

from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from defusedxml.common import DefusedXmlException

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from workbook_preflight import (
    WorkbookError, _load_workbook, _members, inspect_workbook,
)


MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 128
COUNT_FIELDS = ("worksheet_rows", "worksheet_columns", "data_rows", "formula_count", "external_link_count")


class SnapshotError(ValueError):
    """The snapshot failed its manifest contract."""


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise SnapshotError("Manifest JSON contains duplicate fields")
    return fields


def _load_manifest(path: Path) -> list[dict]:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise SnapshotError("The manifest must be an ordinary file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise SnapshotError("The manifest exceeds the size limit")
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields)
    if (not isinstance(value, dict) or set(value) != {"schema", "sources"} or type(value["schema"]) is not int
            or value["schema"] != 1 or not isinstance(value["sources"], list) or not 1 <= len(value["sources"]) <= 16):
        raise SnapshotError("Invalid snapshot manifest structure")
    return value["sources"]


def _workbook_path(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or path.as_posix() != name or any(c in name for c in "\\:") or ".." in path.parts:
        raise SnapshotError("Workbook paths must be relative to the manifest")
    if path.suffix.lower() != ".xlsx":
        raise SnapshotError("A snapshot must be an XLSX workbook")
    current = root
    for part in path.parts[:-1]:
        current /= part
        info = current.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise SnapshotError("Workbook paths must use ordinary directories")
    return current / path.name


def _manifest_fields(source: object) -> tuple[tuple[str, ...], int]:
    required = {"kind", "path", "sha256", "sheet_name", "expected_headers", "header_start_column", *COUNT_FIELDS}
    if not isinstance(source, dict) or set(source) != required:
        raise SnapshotError("Invalid snapshot source fields")
    for key in ("kind", "path", "sha256", "sheet_name"):
        if not isinstance(source[key], str) or not 1 <= len(source[key]) <= 240:
            raise SnapshotError("Invalid snapshot source text")
    if re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None:
        raise SnapshotError("Invalid snapshot SHA-256")
    headers = source["expected_headers"]
    if (not isinstance(headers, list) or not 1 <= len(headers) <= MAX_COLUMNS
            or not all(isinstance(header, str) and 1 <= len(header) <= 240 for header in headers)):
        raise SnapshotError("Invalid snapshot header fields")
    column = source["header_start_column"]
    if type(column) is not int or not 1 <= column <= MAX_COLUMNS or column + len(headers) - 1 > MAX_COLUMNS:
        raise SnapshotError("Invalid snapshot header column")
    for field in COUNT_FIELDS:
        if type(source[field]) is not int or source[field] < 0:
            raise SnapshotError("Invalid snapshot count")
    return tuple(headers), column


def _normalized_header(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split()).strip()


def _worksheet_counts(content: bytes, source: dict, headers: tuple[str, ...], start: int) -> dict:
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=False, keep_links=False)
    try:
        if source["sheet_name"] not in workbook.sheetnames:
            raise SnapshotError("The declared snapshot sheet is missing")
        sheet = workbook[source["sheet_name"]]
        rows, columns = sheet.max_row, sheet.max_column
        if rows is None or columns is None or not 1 <= rows <= MAX_ROWS or not 1 <= columns <= MAX_COLUMNS:
            raise SnapshotError("The worksheet dimensions are missing or exceed the supported limits")
        if start + len(headers) - 1 > columns:
            raise SnapshotError("The snapshot header contract changed")
        if rows != source["worksheet_rows"] or columns != source["worksheet_columns"]:
            raise SnapshotError("The snapshot failed its worksheet dimensions gate")

        row_stream = sheet.iter_rows(min_row=1, max_row=rows, min_col=start, max_col=start + len(headers) - 1)
        header_row = None
        for number, row in enumerate(row_stream, start=1):
            if number > 20:
                break
            if tuple(_normalized_header(cell.value) for cell in row) == headers:
                header_row = number
                break
        if header_row is None:
            raise SnapshotError("The snapshot header contract changed")
        formula_count = data_rows = 0
        for row in row_stream:
            formula_count += sum(cell.data_type == "f" for cell in row)
            if any(_normalized_header(cell.value) for cell in row):
                data_rows += 1
        return dict(header_row=header_row, header_column=start, worksheet_rows=rows, worksheet_columns=columns,
                    data_rows=data_rows, formula_count=formula_count)
    finally:
        workbook.close()


def inspect_snapshot_source(source: dict, root: Path) -> dict:
    headers, start = _manifest_fields(source)
    path = _workbook_path(root, source["path"])
    content = _load_workbook(path)
    actual = sha256(content).hexdigest()
    if actual != source["sha256"]:
        raise SnapshotError("The workbook failed its checksum gate")
    inspect_workbook(content)
    with ZipFile(BytesIO(content)) as archive:
        external_link_count = sum(
            name.startswith("xl/externalLinks/externalLink") and name.endswith(".xml")
            for name in _members(archive)
        )
    counts = _worksheet_counts(content, source, headers, start)
    counts["external_link_count"] = external_link_count
    for field in COUNT_FIELDS:
        if counts[field] != source[field]:
            raise SnapshotError(f"The snapshot failed its {field} gate")
    return dict(kind=source["kind"], sha256=actual, sheet_name=source["sheet_name"], **counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        sources = _load_manifest(args.manifest)
        reports = [inspect_snapshot_source(source, args.manifest.parent) for source in sources]
    except (SnapshotError, WorkbookError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError,
            BadZipFile, ParseError, DefusedXmlException, InvalidFileException):
        print("Invalid or unreadable snapshot input", file=sys.stderr)
        return 2
    print(json.dumps({"sources": reports}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
