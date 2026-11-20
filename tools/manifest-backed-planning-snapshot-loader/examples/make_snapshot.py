"""Generate a fictional development snapshot and its manifest in a new directory."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from openpyxl import load_workbook

from make_inventory import make_inventory
from make_orders import make_orders
from wip_workbook import INVENTORY_HEADERS


def make_snapshot(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir()
    workbooks = root / "workbooks"
    workbooks.mkdir()
    orders = workbooks / "orders.xlsx"
    inventory = workbooks / "inventory.xlsx"
    contract = root / "manifest.json"
    make_orders(orders)
    make_inventory(inventory)
    book = load_workbook(inventory, read_only=True)
    try:
        rows, columns = book.active.max_row, book.active.max_column
    finally:
        book.close()
    manifest = {
        "status": "DEVELOPMENT_INTEGRITY_VALIDATED_FICTIONAL",
        "environment": "development-only",
        "activation_gate": {"production_included": False, "source_revision_accepted": True},
        "orders": {
            "path": "workbooks/orders.xlsx",
            "sha256": sha256(orders.read_bytes()).hexdigest(),
            "customer_order_count": 118, "panel_order_count": 2, "mapping_count": 9,
        },
        "sources": [{
            "kind": "inventory",
            "path": "workbooks/inventory.xlsx",
            "sha256": sha256(inventory.read_bytes()).hexdigest(),
            "sheet_name": "FPC_Production_Inventory",
            "header_start_column": 2,
            "expected_headers": list(INVENTORY_HEADERS),
            "row_count_mode": "normalized_wip",
            "worksheet_rows": rows, "worksheet_columns": columns,
            "expected_normalized_rows": 130,
            "formula_count": 0, "external_link_count": 0,
        }],
    }
    contract.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return orders, inventory, contract


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_snapshot(parser.parse_args().directory)
