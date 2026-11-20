"""Verify saved XLSX snapshots against a local checksum and worksheet manifest."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath
import stat
from zipfile import ZipFile

from openpyxl import load_workbook

from workbook_preflight import _members


MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ROWS = 20_000
MAX_COLUMNS = 128


class SnapshotError(ValueError):
    """The snapshot failed its manifest contract."""


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise SnapshotError("Manifest JSON contains duplicate fields")
    return fields


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
        formula_count = 0
        for row in row_stream:
            formula_count += sum(cell.data_type == "f" for cell in row)
        return dict(header_row=header_row, header_column=start, worksheet_rows=rows, worksheet_columns=columns,
                    formula_count=formula_count)
    finally:
        workbook.close()


def inspect_inventory_shape(content: bytes, source: dict, headers: tuple[str, ...], start: int) -> dict:
    counts = _worksheet_counts(content, source, headers, start)
    with ZipFile(BytesIO(content)) as archive:
        counts["external_link_count"] = sum(
            name.startswith("xl/externalLinks/externalLink") and name.endswith(".xml")
            for name in _members(archive)
        )
    return counts
