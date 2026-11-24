from datetime import date
from hashlib import sha256
from io import BytesIO
import json
from xml.dom import minidom
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from examples.make_demo_workbook import MAIN, REVISION_NS, make_snapshot, make_workbook
from order_workbook_patch import WorkbookPatchError, _publish, patch_workbook


C = "xl/worksheets/sheet1.xml"
P = "xl/worksheets/sheet2.xml"
NS = {"s": MAIN}


def patch(template, snapshot):
    return patch_workbook(template, json.dumps(snapshot).encode())


def repack(template, replacements, additions=()):
    content = BytesIO()
    with ZipFile(BytesIO(template)) as source, ZipFile(content, "w") as target:
        for name in source.namelist():
            target.writestr(name, replacements.get(name, source.read(name)))
        for name, data in additions:
            target.writestr(name, data)
    return content.getvalue()


def test_patches_typed_cells_and_preserves_other_package_parts():
    template = make_workbook()
    patched, rows = patch(template, make_snapshot(template))
    assert rows == 1
    with ZipFile(BytesIO(patched)) as result, ZipFile(BytesIO(template)) as original:
        assert result.namelist() == original.namelist()
        assert result.comment == original.comment
        assert {name for name in result.namelist() if result.read(name) != original.read(name)} == {C}
        worksheet = result.read(C)
    tree = ET.fromstring(worksheet)
    cells = {cell.attrib["r"]: cell for cell in tree.findall(".//s:c", NS)}
    assert cells["A4"].findtext("s:f", namespaces=NS) == "1+1"
    assert cells["F4"].findtext("s:v", namespaces=NS) == "120"
    assert cells["I4"].findtext("s:v", namespaces=NS) == str((date(2030, 9, 17) - date(1899, 12, 30)).days)
    assert cells["D4"].attrib["t"] == "inlineStr"
    assert cells["D4"].findtext("s:is/s:t", namespaces=NS) == " =DEMO "
    assert cells["D4"].find("s:is/s:t", NS).attrib["{http://www.w3.org/XML/1998/namespace}space"] == "preserve"
    assert list(cells["U4"]) == [] and "t" not in cells["U4"].attrib
    assert cells["C4"].findtext("s:is/s:t", namespaces=NS) == "DEMO-OLD"
    assert minidom.parseString(worksheet).documentElement.getAttribute("xmlns:xr2") == REVISION_NS


def test_manual_rows_can_set_extra_fields_and_preserve_numeric_row_order():
    template = make_workbook()
    snapshot = make_snapshot(template)
    order = snapshot["orders"][0]
    order.update(source_row=5, fields={"part_number": "DEMO-NEW", "quantity": 5})
    with pytest.raises(WorkbookPatchError, match="approved editable"):
        patch(template, snapshot)
    order["record_origin"] = "MANUAL"
    snapshot["orders"].append({"source_sheet": "P", "source_row": 4, "fields": {"quantity": 8}})
    snapshot["source_row_count"] = 2
    patched, count = patch(template, snapshot)
    assert count == 2
    with ZipFile(BytesIO(patched)) as result:
        tree = ET.fromstring(result.read(C))
        assert [row.get("r") for row in tree.findall(".//s:row", NS)] == ["4", "5", "6"]
        assert tree.findtext(".//s:c[@r='C5']/s:is/s:t", namespaces=NS) == "DEMO-NEW"
        panel = ET.fromstring(result.read(P))
        assert panel.findtext(".//s:c[@r='F4']/s:v", namespaces=NS) == "8"
        assert panel.find("s:dimension", NS).get("ref") == "A1:F4"


def test_checksum_is_checked_before_opening_zip():
    template = make_workbook()
    with pytest.raises(WorkbookPatchError, match="checksum does not match"):
        patch(b"not a zip", make_snapshot(template))


def test_duplicate_row_and_bad_count_are_rejected():
    template = make_workbook()
    snapshot = make_snapshot(template)
    snapshot["orders"].append(snapshot["orders"][0])
    with pytest.raises(WorkbookPatchError, match="row count"):
        patch(template, snapshot)
    snapshot["source_row_count"] = 2
    with pytest.raises(WorkbookPatchError, match="duplicate sheet and row"):
        patch(template, snapshot)


def test_formula_in_target_cell_refuses_even_a_clear():
    original = make_workbook()
    with ZipFile(BytesIO(original)) as archive:
        sheet = archive.read(C).replace(b'<c r="F4"><v>3</v></c>', b'<c r="F4"><f>1+2</f><v>3</v></c>')
    workbook = repack(original, {C: sheet})
    snapshot = make_snapshot(workbook)
    snapshot["orders"][0]["fields"]["quantity"] = None
    with pytest.raises(WorkbookPatchError, match="contains a formula"):
        patch(workbook, snapshot)


def test_workbook_rejects_unsafe_parts_doctype_and_macro_project():
    template = make_workbook()
    with ZipFile(BytesIO(template)) as archive:
        sheet = archive.read(C)
    for replacements, additions, error in (
        ({}, (("../outside.xml", b"<x/>"),), "unsafe or duplicate part"),
        ({}, (("XL/Worksheets/Sheet1.xml", b"<x/>"),), "unsafe or duplicate part"),
        ({C: b"<!DOCTYPE worksheet>" + sheet}, (), "document type"),
        ({}, (("xl/vbaProject.bin", b"dummy"),), "contains macros"),
    ):
        workbook = repack(template, replacements, additions)
        with pytest.raises(WorkbookPatchError, match=error):
            patch(workbook, make_snapshot(workbook))


def test_publishing_cannot_overwrite_existing_output(tmp_path):
    destination = tmp_path / "copy.xlsx"
    template = make_workbook()
    receipt = sha256(template).hexdigest()
    _publish(destination, template)
    try:
        with pytest.raises(FileExistsError):
            _publish(destination, b"other content")
    finally:
        assert sha256(destination.read_bytes()).hexdigest() == receipt
        assert set(tmp_path.iterdir()) == {destination}
