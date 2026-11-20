"""Generate a new fictional inventory and scrap workbook pair and its manifest."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from openpyxl import Workbook


def make_snapshots(root: Path, *, inventory_rows: int = 3, scrap_rows: int = 5) -> Path:
    root.mkdir()
    records = []
    for kind, count in (("inventory", inventory_rows), ("scrap", scrap_rows)):
        path = root / f"{kind}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Fictional Data"
        sheet.append(["Fictional snapshot"])
        sheet.append([None, "Lot\n  ID", "Quantity"])
        for index in range(1, count + 1):
            sheet.append([None, f"DEMO-{index:02}", 5 * index])
        workbook.save(path)
        workbook.close()
        records.append(dict(
            kind=kind, path=path.name, sha256=sha256(path.read_bytes()).hexdigest(),
            sheet_name="Fictional Data", expected_headers=["Lot ID", "Quantity"],
            header_start_column=2, worksheet_rows=count + 2, worksheet_columns=3,
            data_rows=count, formula_count=0, external_link_count=0,
        ))
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"schema": 1, "sources": records}, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    make_snapshots(args.directory)
