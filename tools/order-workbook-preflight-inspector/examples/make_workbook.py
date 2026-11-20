"""Create a small fictional XLSX exclusively for the preflight example."""

import argparse
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


def fictional_workbook(extra: dict[str, str] | None = None) -> bytes:
    parts = {
        "[Content_Types].xml": """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>""",
        "_rels/.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        "xl/workbook.xml": """<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Fictional Orders" sheetId="1" r:id="rId1"/></sheets></workbook>""",
        "xl/_rels/workbook.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>""",
        "xl/worksheets/sheet1.xml": """<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row r="1">
<c r="A1" t="e"><f>'[fictional-forecast.xlsx]Planning'!A1</f><v>#REF!</v></c>
<c r="B1" t="e"><f>1/0</f><v>#DIV/0!</v></c>
</row></sheetData></worksheet>""",
    }
    parts.update({
        "xl/externalLinks/externalLink1.xml": '<externalLink xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>',
        "xl/externalLinks/_rels/externalLink1.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" TargetMode="External" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/externalLinkPath"
Target="https://example.invalid/fictional-catalog.xlsx"/>
</Relationships>""",
    })
    if extra:
        parts.update(extra)
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for name, body in parts.items():
            member = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.create_system = 3
            archive.writestr(member, body.encode("utf-8"))
    return output.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    options = parser.parse_args()
    with options.workbook.open("xb") as destination:
        destination.write(fictional_workbook())
