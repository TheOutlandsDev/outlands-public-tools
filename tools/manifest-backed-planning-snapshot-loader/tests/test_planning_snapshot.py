"""Original manifest-backed test cases with fictional saved workbooks."""

from hashlib import sha256
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_snapshot import make_snapshot
import planning_snapshot as snapshot


def test_manifest_backed_summary_uses_accepted_inventory(tmp_path):
    root = tmp_path / "fictional"
    orders, inventory, manifest = make_snapshot(root)
    result = snapshot.load_manifest_backed_ptla_inputs(
        orders, inventory, contract_path=manifest, project_root=root,
    )
    summary = result.summary
    assert summary.status == "PASS"
    assert summary.orders_source_sha256 == sha256(orders.read_bytes()).hexdigest().upper()
    assert summary.inventory_source_sha256 == sha256(inventory.read_bytes()).hexdigest().upper()
    assert summary.wip_record_count == 130
    assert summary.source_mode == "read-only manifest-backed snapshot"
    assert summary.database_writes is False
    assert (len(result.customer_orders), len(result.panel_orders), len(result.mappings)) == (118, 2, 9)
    assert len(result.wip_records) == 130


def test_manifest_backed_summary_fails_closed_when_inventory_is_missing(tmp_path):
    root = tmp_path / "fictional"
    orders, inventory, manifest = make_snapshot(root)
    inventory.unlink()
    with pytest.raises(snapshot.SnapshotContractError, match="unavailable"):
        snapshot.load_manifest_backed_ptla_inputs(
            orders, inventory, contract_path=manifest, project_root=root,
        )


def test_manifest_backed_summary_fails_closed_when_inventory_is_altered(tmp_path, monkeypatch):
    root = tmp_path / "fictional"
    orders, inventory, manifest = make_snapshot(root)
    inventory.write_bytes(inventory.read_bytes() + b"fictional alteration")

    def unexpected(*args, **kwargs):
        pytest.fail("The workbook was parsed before verification")

    monkeypatch.setattr(snapshot, "extract_verified_inventory", unexpected)
    monkeypatch.setattr(snapshot, "extract_verified_workbook", unexpected)
    with pytest.raises(snapshot.SnapshotContractError, match="checksum gate"):
        snapshot.load_manifest_backed_ptla_inputs(
            orders, inventory, contract_path=manifest, project_root=root,
        )


def test_manifest_backed_summary_is_repeatable_and_does_not_mutate_sources(tmp_path):
    root = tmp_path / "fictional"
    orders, inventory, manifest = make_snapshot(root)
    before = {path: sha256(path.read_bytes()).hexdigest() for path in (orders, inventory, manifest)}
    first = snapshot.load_manifest_backed_ptla_inputs(
        orders, inventory, contract_path=manifest, project_root=root,
    )
    second = snapshot.load_manifest_backed_ptla_inputs(
        orders, inventory, contract_path=manifest, project_root=root,
    )
    assert first.summary == second.summary
    assert first == second
    assert {path: sha256(path.read_bytes()).hexdigest() for path in before} == before
