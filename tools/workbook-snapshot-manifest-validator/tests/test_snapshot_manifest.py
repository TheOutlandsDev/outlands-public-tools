"""Fictional adaptations of the two original snapshot workbook checks."""

from hashlib import sha256
import json

import pytest

import snapshot_manifest as validator
from examples.make_snapshots import make_snapshots


def inspect(manifest):
    sources = json.loads(manifest.read_bytes())["sources"]
    return {source["kind"]: validator.inspect_snapshot_source(source, manifest.parent) for source in sources}


def test_snapshot_sources_match_hash_shape_and_count_gates(tmp_path):
    reports = inspect(make_snapshots(tmp_path / "first"))
    assert set(reports) == {"inventory", "scrap"}
    assert reports["inventory"]["data_rows"] == 3
    assert reports["scrap"]["worksheet_rows"] == 7
    assert reports["scrap"]["data_rows"] == 5
    assert all(report["formula_count"] == 0 and report["external_link_count"] == 0 for report in reports.values())


def test_second_snapshot_sources_match_declared_revision_gates(tmp_path):
    root = tmp_path / "second"
    reports = inspect(make_snapshots(root, inventory_rows=4, scrap_rows=6))
    assert set(reports) == {"inventory", "scrap"}
    assert reports["inventory"]["sha256"] == sha256((root / "inventory.xlsx").read_bytes()).hexdigest()
    assert reports["inventory"]["data_rows"] == 4
    assert reports["scrap"]["sha256"] == sha256((root / "scrap.xlsx").read_bytes()).hexdigest()
    assert reports["scrap"]["worksheet_rows"] == 8
    assert reports["scrap"]["data_rows"] == 6
    assert all(report["formula_count"] == 0 and report["external_link_count"] == 0 for report in reports.values())


def test_checksum_failure_precedes_any_parser(tmp_path, monkeypatch):
    root = tmp_path / "changed"
    manifest = make_snapshots(root)
    source = json.loads(manifest.read_bytes())["sources"][0]
    (root / "inventory.xlsx").write_bytes(b"fictional changed bytes")

    def unexpected(_content):
        pytest.fail("Parser must not be called when the checksum differs")

    monkeypatch.setattr(validator, "inspect_workbook", unexpected)
    with pytest.raises(validator.SnapshotError, match="checksum gate"):
        validator.inspect_snapshot_source(source, root)


def test_matching_hash_still_requires_headers_dimensions_and_counts(tmp_path):
    root = tmp_path / "conditions"
    manifest = make_snapshots(root)
    source = json.loads(manifest.read_bytes())["sources"][0]
    for field, value, reason in (
        ("expected_headers", ["Incorrect Header", "Quantity"], "header contract"),
        ("worksheet_rows", 19, "dimensions gate"),
        ("data_rows", 19, "data_rows gate"),
        ("formula_count", 19, "formula_count gate"),
        ("external_link_count", 19, "external_link_count gate"),
    ):
        with pytest.raises(validator.SnapshotError, match=reason):
            validator.inspect_snapshot_source(dict(source, **{field: value}), root)
