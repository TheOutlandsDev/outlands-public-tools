"""Create a fictional worksheet with a header near the search boundary."""

import argparse
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import Workbook


def make_sample(path, *, header_row, omit_dimensions):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Inventory"
    sheet.cell(1, 1, "Fictional Warehouse")
    for column, value in enumerate(("Item", "Count", "Received"), start=2):
        sheet.cell(header_row, column, value)
    for offset, values in ((1, ("A-01", 0, datetime(2026, 1, 2))),
                           (2, ("   ", None, None)),
                           (3, ("B-02", 4, None)),
                           (4, ("C-03", "=2+2", None))):
        for column, value in enumerate(values, start=2):
            sheet.cell(header_row + offset, column, value)

    with TemporaryDirectory() as staging, path.open("xb") as output:
        original = Path(staging) / "fixture.xlsx"
        workbook.save(original)
        workbook.close()
        if not omit_dimensions:
            output.write(original.read_bytes())
            return

        namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        with ZipFile(original) as incoming, ZipFile(output, "w") as outgoing:
            for entry in incoming.infolist():
                data = incoming.read(entry)
                if entry.filename == "xl/worksheets/sheet1.xml":
                    root = ET.fromstring(data)
                    root.remove(root.find(namespace + "dimension"))
                    data = ET.tostring(root, encoding="utf-8")
                outgoing.writestr(entry, data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--header-row", type=int, default=20, choices=(20, 21))
    parser.add_argument("--keep-dimensions", action="store_true")
    args = parser.parse_args()
    make_sample(args.output, header_row=args.header_row, omit_dimensions=not args.keep_dimensions)
