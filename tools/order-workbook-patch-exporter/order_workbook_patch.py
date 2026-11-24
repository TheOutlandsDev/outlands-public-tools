"""Patch the approved cells of a checksum-verified order workbook copy."""

import argparse
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from tempfile import TemporaryDirectory
from xml.dom import minidom
from xml.parsers import expat
from zipfile import BadZipFile, ZIP_DEFLATED, ZIP_STORED, ZipFile
from zlib import error as CompressionError


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_NS = "http://www.w3.org/XML/1998/namespace"

EDITABLE_COLUMNS = {
    "purchase_order": "D",
    "po_line": "E",
    "quantity": "F",
    "commit_date": "I",
    "ship_quantity": "J",
    "ship_date": "K",
    "dock_date": "N",
    "lot_ids": "O",
    "lot_quantities": "P",
    "work_request_flow": "Q",
    "customer_notes": "T",
    "planning_notes": "U",
}
MANUAL_COLUMNS = {
    **EDITABLE_COLUMNS,
    "order_date": "B",
    "part_number": "C",
    "requested_ship_date": "G",
    "organization": "H",
    "shipment_number": "L",
    "checked_by": "M",
    "carrier": "R",
    "tracking_number": "S",
}
DATE_FIELDS = {"order_date", "requested_ship_date", "commit_date", "ship_date", "dock_date"}
SHEETS = ("C", "P")
MIB = 1024 * 1024
INVALID_XML_CHAR = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")


class WorkbookPatchError(ValueError):
    """The inputs do not meet the workbook patch requirements."""


@dataclass
class OrderPatch:
    sheet: str
    row: int
    cells: dict[str, str | int | date | None]


def _read_bounded(path, limit):
    with path.open("rb") as stream:
        contents = stream.read(limit + 1)
    if len(contents) > limit:
        raise WorkbookPatchError("An input file exceeds the size limit.")
    return contents


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WorkbookPatchError("The snapshot contains a duplicate JSON field.")
        result[key] = value
    return result


def _cell_value(field, value):
    if value is None:
        return None
    if field in DATE_FIELDS:
        if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                pass
            else:
                if parsed >= date(1900, 3, 1):
                    return parsed
        raise WorkbookPatchError("An order date must be an ISO date on or after 1900-03-01.")
    if field in {"quantity", "ship_quantity"}:
        minimum = int(field == "quantity")
        if type(value) is not int or not minimum <= value <= 999_999_999_999_999:
            raise WorkbookPatchError("An order quantity is outside the supported integer range.")
        return value
    if not isinstance(value, str) or len(value) > 32767 or INVALID_XML_CHAR.search(value):
        raise WorkbookPatchError("An order field contains invalid cell text.")
    return value


def _snapshot(contents):
    try:
        payload = json.loads(contents, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError) as exc:
        if isinstance(exc, WorkbookPatchError):
            raise
        raise WorkbookPatchError("The snapshot is not valid JSON.") from exc
    if not isinstance(payload, dict) or payload.keys() != {"source_sha256", "source_row_count", "orders"}:
        raise WorkbookPatchError("The snapshot must declare a template hash, row count, and orders.")
    digest = payload["source_sha256"]
    count = payload["source_row_count"]
    records = payload["orders"]
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise WorkbookPatchError("The snapshot template SHA-256 is invalid.")
    if not isinstance(records, list) or type(count) is not int or not 0 <= count <= 1000 or len(records) != count:
        raise WorkbookPatchError("The snapshot row count does not match its orders or exceeds 1000.")

    seen = set()
    patches = []
    for record in records:
        required = {"source_sheet", "source_row", "fields"}
        if not isinstance(record, dict) or not required <= record.keys() <= required | {"record_origin"}:
            raise WorkbookPatchError("An order patch has missing or unknown fields.")
        sheet, row, fields = (record[name] for name in ("source_sheet", "source_row", "fields"))
        if sheet not in SHEETS or type(row) is not int or not 4 <= row <= 500:
            raise WorkbookPatchError("An order patch must address row 4 through 500 on sheet C or P.")
        identity = sheet, row
        if identity in seen:
            raise WorkbookPatchError("The snapshot contains a duplicate sheet and row.")
        seen.add(identity)
        origin = record.get("record_origin", "SOURCE_IMPORT")
        if origin not in ("SOURCE_IMPORT", "MANUAL"):
            raise WorkbookPatchError("An order patch has an invalid record origin.")
        columns = MANUAL_COLUMNS if origin == "MANUAL" else EDITABLE_COLUMNS
        if not isinstance(fields, dict) or not fields or not fields.keys() <= columns.keys():
            raise WorkbookPatchError("An order patch must name approved editable fields.")
        patches.append(OrderPatch(sheet, row, {columns[key]: _cell_value(key, value) for key, value in fields.items()}))
    return digest, patches


def _check_members(archive):
    members = archive.infolist()
    if len(members) > 512 or sum(member.file_size for member in members) > 64 * MIB:
        raise WorkbookPatchError("The workbook package exceeds its size or part count limit.")
    names = set()
    for member in members:
        name = member.orig_filename.removesuffix("/")
        if (not name or any(part in ("", ".", "..") for part in name.split("/"))
                or any(character in name for character in ("\\", ":", "\x00")) or name.casefold() in names):
            raise WorkbookPatchError("The workbook contains an unsafe or duplicate part name.")
        names.add(name.casefold())
        if (member.file_size > 16 * MIB or member.flag_bits & 1
                or member.compress_type not in (ZIP_DEFLATED, ZIP_STORED)):
            raise WorkbookPatchError("The workbook contains an unsupported or oversized part.")
        if PurePosixPath(name).name.casefold() == "vbaproject.bin":
            raise WorkbookPatchError("The workbook contains macros.")


def _no_doctype(*_args):
    raise WorkbookPatchError("Workbook XML must not declare a document type.")


def _read_xml(archive, name, namespace, root_tag):
    raw = archive.read(name)
    parser = expat.ParserCreate()
    parser.StartDoctypeDeclHandler = _no_doctype
    parser.Parse(raw, True)
    document = minidom.parseString(raw)
    root = document.documentElement
    if (root.namespaceURI, root.localName) != (namespace, root_tag):
        raise WorkbookPatchError("A workbook XML part has an unexpected root element.")
    return document


def _children(parent, namespace, name):
    return [child for child in parent.childNodes if child.nodeType == child.ELEMENT_NODE
            and (child.namespaceURI, child.localName) == (namespace, name)]


def _sheet_targets(archive):
    types = _read_xml(archive, "[Content_Types].xml", TYPES_NS, "Types")
    for node in types.documentElement.childNodes:
        if node.nodeType == node.ELEMENT_NODE:
            kind = node.getAttribute("ContentType").casefold()
            if "macroenabled" in kind or "vbaproject" in kind:
                raise WorkbookPatchError("The workbook contains macros.")

    workbook = _read_xml(archive, "xl/workbook.xml", MAIN_NS, "workbook").documentElement
    for settings in _children(workbook, MAIN_NS, "workbookPr"):
        if settings.getAttribute("date1904") in ("1", "true"):
            raise WorkbookPatchError("The workbook must use the 1900 date system.")
    relationships = _read_xml(
        archive, "xl/_rels/workbook.xml.rels", PACKAGE_REL_NS, "Relationships"
    ).documentElement
    by_id = {}
    for relationship in _children(relationships, PACKAGE_REL_NS, "Relationship"):
        identifier = relationship.getAttribute("Id")
        if not identifier or identifier in by_id:
            raise WorkbookPatchError("The workbook has an invalid or duplicate relationship ID.")
        by_id[identifier] = relationship

    targets = {}
    for sheet in workbook.getElementsByTagNameNS(MAIN_NS, "sheet"):
        name = sheet.getAttribute("name")
        if name not in SHEETS:
            continue
        relationship = by_id.get(sheet.getAttributeNS(OFFICE_REL_NS, "id"))
        if (relationship is None or name in targets
                or relationship.getAttribute("Type") != OFFICE_REL_NS + "/worksheet"
                or relationship.getAttribute("TargetMode") not in ("", "Internal")):
            raise WorkbookPatchError("The workbook has an invalid required worksheet relationship.")
        target = relationship.getAttribute("Target")
        part = target[1:] if target.startswith("/") else "xl/" + target
        if not re.fullmatch(r"xl/worksheets/[A-Za-z0-9_.-]+\.xml", part):
            raise WorkbookPatchError("The workbook has an unsupported worksheet part path.")
        targets[name] = part

    if targets.keys() != set(SHEETS) or len(set(targets.values())) != len(SHEETS):
        raise WorkbookPatchError("The workbook must contain separate C and P worksheets.")
    if any(part not in archive.namelist() for part in targets.values()):
        raise WorkbookPatchError("A required worksheet part is missing.")
    return targets


def _new(parent, tag):
    qualified = f"{parent.prefix}:{tag}" if parent.prefix else tag
    return parent.ownerDocument.createElementNS(MAIN_NS, qualified)


def _column_number(reference):
    letters = re.match(r"[A-Z]+", reference)
    if letters is None:
        raise WorkbookPatchError("The workbook has an invalid cell reference.")
    number = 0
    for character in letters.group(0):
        number = number * 26 + ord(character) - 64
    return number



def _grow_dimension(root, patch):
    dimensions = _children(root, MAIN_NS, "dimension")
    if not dimensions:
        return
    reference = dimensions[0].getAttribute("ref")
    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})(?::([A-Z]{1,3})([1-9][0-9]{0,6}))?", reference)
    if len(dimensions) != 1 or match is None:
        raise WorkbookPatchError("A target worksheet has an invalid used range.")

    left, top, right, bottom = match.groups()
    columns = [left, right or left, *patch.cells]
    first = f"{min(columns, key=_column_number)}{min(int(top), patch.row)}"
    last = f"{max(columns, key=_column_number)}{max(int(bottom or top), patch.row)}"
    dimensions[0].setAttribute("ref", first if first == last else f"{first}:{last}")


def _find_or_insert(parent, tag, reference, order):
    elements = _children(parent, MAIN_NS, tag)
    matches = [node for node in elements if node.getAttribute("r") == reference]
    if len(matches) > 1:
        raise WorkbookPatchError("The workbook contains a duplicate target row or cell.")
    if matches:
        return matches[0]

    result = _new(parent, tag)
    result.setAttribute("r", reference)
    rank = order(reference)
    before = next((node for node in elements if order(node.getAttribute("r")) > rank), None)
    parent.insertBefore(result, before)
    return result


def _set_cell(row, reference, value):
    cell = _find_or_insert(row, "c", reference, _column_number)
    if _children(cell, MAIN_NS, "f"):
        raise WorkbookPatchError("An approved target cell contains a formula.")
    for child in _children(cell, MAIN_NS, "v") + _children(cell, MAIN_NS, "is"):
        cell.removeChild(child)
        child.unlink()
    if cell.hasAttribute("t"):
        cell.removeAttribute("t")
    if value is None:
        return
    if isinstance(value, date):
        value = (value - date(1899, 12, 30)).days
    if isinstance(value, int):
        node = _new(cell, "v")
        cell.appendChild(node)
    else:
        cell.setAttribute("t", "inlineStr")
        inline = _new(cell, "is")
        cell.appendChild(inline)
        node = _new(inline, "t")
        inline.appendChild(node)
        if value != value.strip():
            node.setAttributeNS(XML_NS, "xml:space", "preserve")
    node.appendChild(node.ownerDocument.createTextNode(str(value)))


def patch_workbook(template, snapshot):
    """Return the completed workbook bytes and the number of patched rows."""
    expected, patches = _snapshot(snapshot)
    if sha256(template).hexdigest() != expected:
        raise WorkbookPatchError("The workbook checksum does not match the snapshot.")
    try:
        with ZipFile(BytesIO(template), "r") as archive:
            _check_members(archive)
            targets = _sheet_targets(archive)
            documents = {
                sheet: _read_xml(archive, targets[sheet], MAIN_NS, "worksheet")
                for sheet in {patch.sheet for patch in patches}
            }
            for patch in patches:
                root = documents[patch.sheet].documentElement
                grids = _children(root, MAIN_NS, "sheetData")
                if len(grids) != 1:
                    raise WorkbookPatchError("A target worksheet must contain one data grid.")
                row = _find_or_insert(grids[0], "row", str(patch.row), int)
                for column, value in sorted(patch.cells.items(), key=lambda pair: _column_number(pair[0])):
                    _set_cell(row, f"{column}{patch.row}", value)
                _grow_dimension(root, patch)
            changed = {targets[sheet]: document.toxml(encoding="utf-8") for sheet, document in documents.items()}
            output = BytesIO()
            with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=6) as target:
                target.comment = archive.comment
                for member in archive.infolist():
                    payload = archive.read(member)
                    target.writestr(member, changed.get(member.filename, payload))
    except WorkbookPatchError:
        raise
    except (BadZipFile, ValueError, LookupError, RuntimeError, EOFError, expat.ExpatError, CompressionError) as exc:
        raise WorkbookPatchError("The workbook is not a supported XLSX package.") from exc
    return output.getvalue(), len(patches)


def _publish(destination, contents):
    with TemporaryDirectory(dir=destination.parent, prefix=".order-patch-") as staging:
        packaged = Path(staging) / "workbook.xlsx"
        packaged.write_bytes(contents)
        if os.name == "nt":
            packaged.rename(destination)
        else:
            os.link(packaged, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.template.suffix.lower() != ".xlsx" or args.output.suffix.lower() != ".xlsx":
            raise WorkbookPatchError("The template and output must use the .xlsx extension.")
        snapshot = _read_bounded(args.snapshot, 2 * MIB)
        template = _read_bounded(args.template, 32 * MIB)
        result, row_count = patch_workbook(template, snapshot)
        _publish(args.output, result)
    except FileExistsError:
        print("The output workbook already exists.", file=sys.stderr)
        return 2
    except (WorkbookPatchError, OSError) as exc:
        print(str(exc) if isinstance(exc, WorkbookPatchError) else "Could not read or publish a workbook file.",
              file=sys.stderr)
        return 2
    print(json.dumps({"patched_rows": row_count, "sha256": sha256(result).hexdigest()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
