"""Create a new archive containing two fictional, minimal XLSX workbooks."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo


def workbook(label: str) -> bytes:
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
        "xl/worksheets/sheet1.xml": f"""<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{label}</t></is></c></row></sheetData></worksheet>""",
    }
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_STORED) as archive:
        for name, body in parts.items():
            member = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.create_system = 3
            archive.writestr(member, body.encode("utf-8"))
    return output.getvalue()


def make_demo_archive(root: Path) -> tuple[str, str]:
    root.mkdir()
    candidates = root / "candidates"
    candidates.mkdir()
    digests = []
    for index, status in ((1, "ACTIVE"), (2, "PENDING_REVIEW")):
        content = workbook(f"Fictional order {index}")
        digest = sha256(content).hexdigest()
        metadata = {
            "sha256": digest, "original_filename": f"fictional-orders-{index}.xlsx",
            "size_bytes": len(content), "uploaded_at": f"2030-09-0{index}T10:00:00Z", "status": status,
        }
        (candidates / f"{digest}.xlsx").write_bytes(content)
        (candidates / f"{digest}.json").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
        digests.append(digest)
    (root / "active.json").write_text(json.dumps({"sha256": digests[0]}) + "\n", encoding="utf-8")
    return digests[0], digests[1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="An archive directory that does not already exist")
    options = parser.parse_args()
    make_demo_archive(options.directory)
