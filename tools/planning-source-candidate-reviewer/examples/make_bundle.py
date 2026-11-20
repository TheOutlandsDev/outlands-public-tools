"""Write a new directory containing only fictional review inputs."""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys

from openpyxl import Workbook

from make_orders import make_orders
from order_mapping_workbook import extract_verified_workbook
from source_candidate_review import EXPECTED_FILES, WIP_HEADERS, _row_id


def make_bundle(directory: Path) -> None:
    directory.mkdir()
    orders = directory / "orders.xlsx"
    make_orders(orders)
    customer, panel, mappings = extract_verified_workbook(orders.read_bytes())

    with (directory / "wip.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(WIP_HEADERS)
        for number in range(1, 65):
            month = "04" if number <= 41 else "03"
            lot_number = 200 if number == 64 else number
            writer.writerow([
                f"DEMO-MATERIAL-{number}", f"LOT{lot_number:07}", 10, 2, "Assembly", "",
                "DEMO-PANEL" if number <= 7 else "DEMO-STANDARD", "", "",
                "Fictional hold" if number <= 8 else "", "", f"{month}/01/2030 01:00 PM",
            ])

    log = Workbook()
    log.active.title = "LotStartLog"
    for row in ([None], [None], [1, 2, 3], [None]):
        log.active.append(row)
    for number in range(1, 130):
        log.active.append([None, None, None, f"LOT{number:07}"])
    log.save(directory / "lot-log.xlsx")
    log.close()

    registry = Workbook()
    registry.active.title = "LastLotStarted"
    registry.active.append(["Fictional lot registry"])
    registry.active.append(["Product Group", "Material Template", "Prefix", "Last Lot Started",
                            None, "Next Lot To Start"])
    for number in range(1, 22):
        following = {1: 1, 2: 2, 3: 200}.get(number, number + 200)
        registry.active.append(["Fictional", "Template", f"DEMO-{number:02}",
                                f"OLD{number:07}", None, f"LOT{following:07}"])
    registry.save(directory / "last-lot.xlsx")
    registry.close()

    sources = []
    for name in EXPECTED_FILES:
        data = (directory / name).read_bytes()
        sources.append(dict(filename=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(
        status="PRESERVED_PENDING_SOURCE_REVIEW",
        production_included=False,
        sources=sources,
        order_counts=[len(customer), len(panel), len(mappings)],
        panel_identities={row.part_number: dict(source_row=row.source_row, quantity=row.quantity,
                                                row_id=_row_id(row)) for row in panel},
        panel_products=["DEMO-PANEL"],
        wip_count=64, log_count=129, registry_count=21,
        overlap_year=2030, overlap_after_month=3,
    )
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    baseline = []
    for index, order in enumerate(customer[:-1]):
        row = order.model_dump(mode="json")
        if index < 32:
            row["source_row"] += 150
        if index < 4:
            row["ship_quantity"] = 1
        if index == 4:
            row["dock_date"] = "2030-08-31"
        baseline.append(row)
    (directory / "baseline.json").write_text(json.dumps({"orders": baseline}), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_bundle(parser.parse_args().directory)
