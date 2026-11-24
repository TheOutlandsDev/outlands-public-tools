"""Create a fictional workbook and matching saved order request in a new folder."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
COMPAT = "http://schemas.openxmlformats.org/markup-compatibility/2006"
REVISION_NS = "http://schemas.microsoft.com/office/spreadsheetml/2015/revision2"


def make_workbook():
    workbook = f"""<workbook xmlns="{MAIN}" xmlns:r="{OFFICE_REL}">
      <sheets><sheet name="C" sheetId="1" r:id="rId1"/><sheet name="P" sheetId="2" r:id="rId2"/>
      <sheet name="Notes" sheetId="3" r:id="rId3"/></sheets></workbook>"""
    relationships = f'<Relationships xmlns="{PACKAGE_REL}">' + "".join(
        f'<Relationship Id="rId{index}" Type="{OFFICE_REL}/worksheet" Target="{prefix}sheet{index}.xml"/>'
        for index, prefix in ((1, "worksheets/"), (2, "/xl/worksheets/"), (3, "worksheets/"))
    ) + "</Relationships>"
    root_relationships = (
        f'<Relationships xmlns="{PACKAGE_REL}">'
        f'<Relationship Id="rId1" Type="{OFFICE_REL}/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    content_types = f"""<Types xmlns="{TYPES}">
      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
      <Default Extension="xml" ContentType="application/xml"/>
      <Override PartName="/xl/workbook.xml"
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
      </Types>"""
    content_types = content_types.replace("</Types>", "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, 4)
    ) + "</Types>")
    orders = f"""<worksheet xmlns="{MAIN}" xmlns:mc="{COMPAT}" xmlns:xr2="{REVISION_NS}" mc:Ignorable="xr2">
      <sheetData><row r="4"><c r="A4"><f>1+1</f><v>2</v></c>
      <c r="C4" t="inlineStr"><is><t>DEMO-OLD</t></is></c>
      <c r="F4"><v>3</v></c><c r="U4" t="inlineStr"><is><t>Old note</t></is></c></row>
      <row r="6"><c r="A6"><v>6</v></c></row></sheetData></worksheet>"""
    empty = f'<worksheet xmlns="{MAIN}"><dimension ref="A1"/><sheetData/></worksheet>'
    notes = f'<worksheet xmlns="{MAIN}"><sheetData><row r="1"><c r="A1"><v>42</v></c></row></sheetData></worksheet>'
    file = BytesIO()
    with ZipFile(file, "w", compression=ZIP_DEFLATED) as archive:
        archive.comment = b"Fictional order workbook example."
        for name, contents in {
            "[Content_Types].xml": content_types,
            "_rels/.rels": root_relationships,
            "xl/workbook.xml": workbook,
            "xl/_rels/workbook.xml.rels": relationships,
            "xl/worksheets/sheet1.xml": orders,
            "xl/worksheets/sheet2.xml": empty,
            "xl/worksheets/sheet3.xml": notes,
        }.items():
            archive.writestr(name, contents)
    return file.getvalue()


def make_snapshot(workbook):
    return {
        "source_sha256": sha256(workbook).hexdigest(),
        "source_row_count": 1,
        "orders": [{
            "source_sheet": "C",
            "source_row": 4,
            "fields": {
                "quantity": 120,
                "purchase_order": " =DEMO ",
                "commit_date": "2030-09-17",
                "planning_notes": None,
            },
        }],
    }


def make_demo(directory):
    directory.mkdir()
    workbook = make_workbook()
    with (directory / "template.xlsx").open("xb") as stream:
        stream.write(workbook)
    with (directory / "orders.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(make_snapshot(workbook), stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    make_demo(Path(sys.argv[1]))
