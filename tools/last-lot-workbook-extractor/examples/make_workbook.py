"""Generate a fictional XLSX with 21 last-lot mappings."""

from pathlib import Path
import sys

from openpyxl import Workbook


def make_workbook(sheet_name="LastLotStarted"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet.append(["Fictional lot start mappings"])
    sheet.append(["Product Group", "Material Template", "Prefix", "Last Lot Started", None, "Next Lot To Start"])
    for number in range(1, 22):
        prefix = f"DEMO-{number:02d}-"
        product = f" DEMO-ITEM-{number:02d} " if number != 2 else None
        material = f" Fictional  Template {number:02d} " if number != 2 else None
        sheet.append([product, material, f" {prefix} ", prefix + "AAAZ", None, prefix + "AABA"])
    return workbook


if __name__ == "__main__":
    workbook = make_workbook()
    try:
        with Path(sys.argv[1]).open("xb") as output:
            workbook.save(output)
    finally:
        workbook.close()
