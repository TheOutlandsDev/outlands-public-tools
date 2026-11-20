"""Generate a fictional workbook with customer orders, panel orders, and part mappings."""

import argparse
from datetime import date
from pathlib import Path
import sys

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from order_mapping_workbook import MAPPING_HEADERS, ORDER_HEADERS


def make_orders(path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name, count in (("C", 118), ("P", 2)):
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(["Fictional orders"])
        sheet.append([None])
        sheet.append([None, *ORDER_HEADERS])
        for index in range(1, count + 1):
            row = [None] * 25
            row[1:9] = [date(2030, 8, 1), f"DEMO-{sheet_name}-{index:03}", f"DEMO-PO-{index:03}",
                        "1", index + 10, date(2030, 8, 20), "DEMO", date(2030, 9, 1)]
            if index == 1:
                row[21] = date(2030, 9, 13)
            elif index == 2:
                row[21] = "#REF!"
            sheet.append(row)
    sheet = workbook.create_sheet("Mapping")
    sheet.append(["Fictional part mappings"])
    sheet.append([None])
    sheet.append([None, *MAPPING_HEADERS, None, None, "Production Revision", "Validation Revision"])
    for index in range(1, 10):
        sheet.append([None, f"DEMO-MAP-{index}", f"DEMO-C-{index:03}", f"DEMO-SUPPLIER-{index}",
                      "A", 1.25, "DEMO-CODE", None, None, 1, None])
    with path.open("xb") as stream:
        workbook.save(stream)
    workbook.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    make_orders(args.workbook)
