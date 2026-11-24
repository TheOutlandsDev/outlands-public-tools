"""Report ordered column metadata for a saved order grid view."""

import argparse
import json
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field


class OrderGridColumn(BaseModel):
    """One column in the saved order grid."""

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    label: str = Field(min_length=1, max_length=80)
    group: Literal[
        "identity", "orders", "shipping", "handoff", "notes", "controls"
    ]
    data_type: Literal["text", "integer", "date", "status"] = "text"
    source_column: str | None = Field(default=None, max_length=40)
    editable: bool = False
    calculated: bool = False
    pinned: bool = False

    model_config = ConfigDict(frozen=True)


ORDER_GRID_COLUMNS = (
    OrderGridColumn(key="status", label="Status", group="identity", data_type="status", calculated=True, pinned=True),
    OrderGridColumn(key="source_sheet", label="Source", group="identity", source_column="tab + row", pinned=True),
    OrderGridColumn(key="order_date", label="Order date", group="orders", data_type="date", source_column="B"),
    OrderGridColumn(key="part_number", label="Part number", group="orders", source_column="C", pinned=True),
    OrderGridColumn(key="modality", label="Modality", group="orders", calculated=True),
    OrderGridColumn(key="purchase_order", label="Purchase order", group="orders", source_column="D", editable=True),
    OrderGridColumn(key="po_line", label="PO line", group="orders", source_column="E", editable=True),
    OrderGridColumn(key="quantity", label="Qty", group="orders", data_type="integer", source_column="F", editable=True),
    OrderGridColumn(key="requested_ship_date", label="Requested ship date", group="orders", data_type="date", source_column="G"),
    OrderGridColumn(key="organization", label="Org", group="orders", source_column="H"),
    OrderGridColumn(key="commit_date", label="Commit date", group="orders", data_type="date", source_column="I", editable=True),
    OrderGridColumn(key="ship_quantity", label="Ship qty", group="shipping", data_type="integer", source_column="J", editable=True),
    OrderGridColumn(key="ship_date", label="Ship date", group="shipping", data_type="date", source_column="K", editable=True),
    OrderGridColumn(key="shipment_number", label="Shipment number", group="shipping", source_column="L"),
    OrderGridColumn(key="checked_by", label="Checked by", group="shipping", source_column="M"),
    OrderGridColumn(key="dock_date", label="Dock date", group="shipping", data_type="date", source_column="N", editable=True),
    OrderGridColumn(key="lot_ids", label="Lot IDs", group="shipping", source_column="O", editable=True),
    OrderGridColumn(key="lot_quantities", label="Lot quantities", group="shipping", source_column="P"),
    OrderGridColumn(key="flex_handoff_state", label="Handoff state", group="handoff", data_type="status", calculated=True),
    OrderGridColumn(key="flex_ready_quantity", label="Ready quantity", group="handoff", data_type="integer", calculated=True),
    OrderGridColumn(key="production_remaining_quantity", label="Production qty remaining", group="handoff", data_type="integer", calculated=True),
    OrderGridColumn(key="flex_ready_lot_ids", label="Cleared lot IDs", group="handoff", calculated=True),
    OrderGridColumn(key="flex_ready_at", label="Cleared at", group="handoff", calculated=True),
    OrderGridColumn(key="flex_ready_by", label="Cleared by", group="handoff", calculated=True),
    OrderGridColumn(key="logistics_mes_status", label="Logistics status", group="handoff", data_type="status", calculated=True),
    OrderGridColumn(key="work_request_flow", label="Work request flow", group="shipping", source_column="Q", editable=True),
    OrderGridColumn(key="carrier", label="Carrier", group="shipping", source_column="R"),
    OrderGridColumn(key="tracking_number", label="Tracking number", group="shipping", source_column="S"),
    OrderGridColumn(key="customer_notes", label="Customer remarks / notes", group="notes", source_column="T", editable=True),
    OrderGridColumn(key="planning_notes", label="Planning notes", group="notes", source_column="U", editable=True),
    OrderGridColumn(key="lead_time_calculation", label="Planned lead-time date", group="controls", data_type="date", source_column="V", calculated=True),
    OrderGridColumn(key="admin_1_open", label="Admin #1 open", group="controls", source_column="W", calculated=True),
    OrderGridColumn(key="admin_2_used", label="Admin #2 used", group="controls", source_column="X", calculated=True),
    OrderGridColumn(key="admin_3_used", label="Admin #3 used", group="controls", source_column="Y", calculated=True),
)

OrderGridView = Literal["all", "orders", "shipping", "notes"]


def order_grid_columns_for_view(view: OrderGridView) -> tuple[OrderGridColumn, ...]:
    """Return a deterministic full-file or task-focused column projection."""

    if view == "all":
        return ORDER_GRID_COLUMNS
    included_groups = {
        "orders": {"identity", "orders"},
        "shipping": {"identity", "orders", "shipping", "handoff"},
        "notes": {"identity", "notes", "controls"},
    }[view]
    return tuple(
        column
        for column in ORDER_GRID_COLUMNS
        if column.pinned or column.group in included_groups
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--view", choices=get_args(OrderGridView), default="all")
    args = parser.parse_args(argv)
    columns = order_grid_columns_for_view(args.view)
    print(json.dumps({
        "selected_view": args.view,
        "visible_columns": [column.model_dump() for column in columns],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
