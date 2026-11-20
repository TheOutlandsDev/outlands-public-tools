"""Generate a fictional inventory workbook with 26 repeated blocks and 131 lots."""

import argparse
from pathlib import Path
import sys

from openpyxl import Workbook

# The fixture generator is launched from its examples directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wip_workbook import INVENTORY_HEADERS


def make_inventory(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "FPC_Production_Inventory"
    sheet.append(["Fictional inventory"])
    sheet.append([None])
    sheet.append([None])
    lot = 0
    for block in range(26):
        sheet.append([None, *INVENTORY_HEADERS])
        for _ in range(6 if block == 0 else 5):
            lot += 1
            sheet.append([None, f"DEMO-LOT-{lot:03}", 1, "Prepare", "Fictional Product", None, 10, 2, 1, 3, None])
        sheet.append([None, "Total"])
        sheet.append([None])
    with path.open("xb") as stream:
        workbook.save(stream)
    workbook.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    make_inventory(args.workbook)
