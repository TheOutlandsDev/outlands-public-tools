"""Verify and load a development-only planning snapshot from two saved XLSX files."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Annotated, Literal
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from defusedxml.common import DefusedXmlException
from openpyxl.utils.exceptions import InvalidFileException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from order_mapping_workbook import (
    PTLAInputContractError as OrderError,
    PTLAMappingRecord,
    PTLAOrderRecord,
    extract_verified_workbook,
)
from snapshot_manifest import (
    MAX_COLUMNS, MAX_MANIFEST_BYTES, SnapshotError, _unique_fields, _workbook_path,
    inspect_inventory_shape,
)
from wip_supply import FPCWIPRecord
from wip_workbook import INVENTORY_HEADERS, PTLAInputContractError as InventoryError, extract_verified_inventory
from workbook_preflight import WorkbookError, _load_workbook, _ordinary_file


class SnapshotContractError(ValueError):
    """The planning snapshot did not pass its manifest contract."""


class ManifestModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class WorkbookPin(ManifestModel):
    path: Annotated[str, Field(min_length=1, max_length=240)]
    sha256: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{64}$")]


class OrdersPin(WorkbookPin):
    customer_order_count: Annotated[int, Field(ge=0, le=500)]
    panel_order_count: Annotated[int, Field(ge=0, le=500)]
    mapping_count: Annotated[int, Field(ge=0, le=100)]


class InventoryPin(WorkbookPin):
    kind: Literal["inventory"]
    sheet_name: Literal["FPC_Production_Inventory"]
    header_start_column: Literal[2]
    expected_headers: list[str]
    row_count_mode: Literal["normalized_wip"]
    worksheet_rows: Annotated[int, Field(ge=1, le=10_000)]
    worksheet_columns: Annotated[int, Field(ge=11, le=MAX_COLUMNS)]
    expected_normalized_rows: Annotated[int, Field(ge=0, le=10_000)]
    formula_count: Annotated[int, Field(ge=0, le=100_000)]
    external_link_count: Annotated[int, Field(ge=0, le=2_000)]


class ActivationGate(ManifestModel):
    production_included: bool
    source_revision_accepted: bool


class Manifest(ManifestModel):
    status: Annotated[str, Field(pattern=r"^DEVELOPMENT_INTEGRITY_VALIDATED_.+$")]
    environment: Literal["development-only"]
    activation_gate: ActivationGate
    orders: OrdersPin
    sources: Annotated[list[dict], Field(min_length=1, max_length=16)]


class PTLAInputSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["PASS"] = "PASS"
    orders_source_sha256: str
    inventory_source_sha256: str
    customer_order_count: int
    panel_order_count: int
    mapping_count: int
    wip_record_count: int
    source_mode: Literal["read-only manifest-backed snapshot"] = "read-only manifest-backed snapshot"
    database_writes: Literal[False] = False


class PTLAInputDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: PTLAInputSummary
    customer_orders: tuple[PTLAOrderRecord, ...]
    panel_orders: tuple[PTLAOrderRecord, ...]
    mappings: tuple[PTLAMappingRecord, ...]
    wip_records: tuple[FPCWIPRecord, ...]


def _read_contract(path: Path) -> tuple[OrdersPin, InventoryPin]:
    if not _ordinary_file(path.lstat()):
        raise SnapshotContractError("The snapshot contract must be an ordinary file.")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise SnapshotContractError("The snapshot contract exceeds the size limit.")
    try:
        contract = Manifest.model_validate(json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields))
    except (ValidationError, ValueError, RecursionError) as exc:
        raise SnapshotContractError("The development snapshot contract is invalid.") from exc
    if contract.activation_gate.production_included or not contract.activation_gate.source_revision_accepted:
        raise SnapshotContractError("The snapshot contract must exclude production and accept the source revision.")
    inventory = [source for source in contract.sources if source.get("kind") == "inventory"]
    if len(inventory) != 1:
        raise SnapshotContractError("The snapshot contract must contain exactly one inventory source.")
    try:
        selected = InventoryPin.model_validate(inventory[0])
    except ValidationError as exc:
        raise SnapshotContractError("The inventory source contract is invalid.") from exc
    if tuple(selected.expected_headers) != INVENTORY_HEADERS:
        raise SnapshotContractError("The inventory header contract is invalid.")
    return contract.orders, selected


def _verified_bytes(root: Path, pin: WorkbookPin, configured: Path | None, label: str) -> tuple[bytes, str]:
    try:
        path = _workbook_path(root, pin.path)
    except SnapshotError as exc:
        raise SnapshotContractError(f"The {label} path must stay within the supplied root.") from exc
    except OSError as exc:
        raise SnapshotContractError(f"The {label} workbook is unavailable.") from exc
    if not path.resolve().is_relative_to(root):
        raise SnapshotContractError(f"The {label} path escapes the supplied root.")
    if configured is not None and configured.absolute() != path:
        raise SnapshotContractError(f"The configured {label} path differs from the governed source.")
    try:
        content = _load_workbook(path)
    except OSError as exc:
        raise SnapshotContractError(f"The {label} workbook is unavailable.") from exc
    digest = sha256(content).hexdigest()
    if digest != pin.sha256.lower():
        raise SnapshotContractError(f"The {label} workbook failed its checksum gate.")
    return content, digest.upper()


def load_manifest_backed_ptla_inputs(
    orders_path: Path | None = None,
    inventory_path: Path | None = None,
    *,
    contract_path: Path,
    project_root: Path,
) -> PTLAInputDataset:
    """Read admitted development workbooks from verified bytes."""
    orders_pin, inventory_pin = _read_contract(contract_path)
    root = project_root.resolve(strict=True)
    if Path(inventory_pin.path) == Path(orders_pin.path):
        raise SnapshotContractError("The orders and inventory must be distinct workbook inputs.")
    inventory_bytes, inventory_hash = _verified_bytes(root, inventory_pin, inventory_path, "inventory")
    order_bytes, order_hash = _verified_bytes(root, orders_pin, orders_path, "orders")

    try:
        wip = extract_verified_inventory(inventory_bytes, expected_count=inventory_pin.expected_normalized_rows)
        shape = inspect_inventory_shape(
            inventory_bytes, inventory_pin.model_dump(), INVENTORY_HEADERS, inventory_pin.header_start_column,
        )
    except (InventoryError, SnapshotError, WorkbookError, ValueError, KeyError, BadZipFile,
            ParseError, DefusedXmlException, InvalidFileException) as exc:
        raise SnapshotContractError(f"The inventory contract failed: {exc}" if isinstance(
            exc, (InventoryError, SnapshotError, WorkbookError)
        ) else "The inventory workbook could not be inspected.") from exc
    for field in ("formula_count", "external_link_count"):
        if shape[field] != getattr(inventory_pin, field):
            raise SnapshotContractError(f"The inventory snapshot failed its {field} gate.")

    try:
        customer, panel, mappings = extract_verified_workbook(order_bytes)
    except (OrderError, WorkbookError) as exc:
        raise SnapshotContractError("The order workbook failed its extraction contract.") from exc
    counts = (len(customer), len(panel), len(mappings))
    if counts != (orders_pin.customer_order_count, orders_pin.panel_order_count, orders_pin.mapping_count):
        raise SnapshotContractError("The extracted order and mapping counts changed.")
    return PTLAInputDataset(
        summary=PTLAInputSummary(
            orders_source_sha256=order_hash,
            inventory_source_sha256=inventory_hash,
            customer_order_count=counts[0],
            panel_order_count=counts[1],
            mapping_count=counts[2],
            wip_record_count=len(wip),
        ),
        customer_orders=customer,
        panel_orders=panel,
        mappings=mappings,
        wip_records=wip,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Root containing the manifest-pinned workbooks")
    parser.add_argument("manifest", type=Path, help="Trusted development snapshot manifest")
    parser.add_argument("--orders", type=Path, help="Assert which order workbook is configured")
    parser.add_argument("--inventory", type=Path, help="Assert which inventory workbook is configured")
    args = parser.parse_args()
    try:
        dataset = load_manifest_backed_ptla_inputs(
            args.orders, args.inventory, contract_path=args.manifest, project_root=args.root,
        )
    except (SnapshotContractError, WorkbookError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError):
        print("The snapshot root or manifest is unavailable.", file=sys.stderr)
        return 2
    print(dataset.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
