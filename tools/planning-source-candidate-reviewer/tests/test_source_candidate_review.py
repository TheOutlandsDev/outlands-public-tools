"""Adapted reference-only review and checksum assertions with fictional data."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_bundle import make_bundle
import source_candidate_review as reviewer


def test_candidate_bundle_is_reference_only_and_reconciles_baseline_orders(tmp_path):
    directory = tmp_path / "fictional"
    make_bundle(directory)
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    baseline = reviewer.SavedBaseline.model_validate_json(before["baseline.json"])
    report = reviewer.inspect_source_candidates(directory, active_orders=baseline.orders)
    assert {path.name: path.read_bytes() for path in directory.iterdir()} == before

    assert report["manifest"]["production_included"] is False
    assert report["orders"]["exact_panel_identities_present"] is True
    comparison = report["orders"]["comparison"]
    assert comparison["added"] == 1
    assert comparison["removed"] == 0
    assert comparison["moved_source_rows"] == 32
    assert comparison["shipping_updates"] == 4
    assert comparison["dock_updates"] == 1
    assert report["wip"]["row_count"] == 64
    assert report["wip"]["raw_circuits"] == 640
    assert report["wip"]["primary_circuits"] == 128
    assert report["wip"]["held_rows"] == 8
    assert report["wip"]["panel_rows"] == 7
    assert report["lot_log"]["material_count"] == 129
    assert report["lot_log"]["visible_months"] == (1, 2, 3)
    assert report["lot_log"]["wip_lots_started_after_cutoff"] == 41
    assert report["lot_log"]["registry_next_id_collisions"] == ("DEMO-01", "DEMO-02", "DEMO-03")


def test_candidate_bundle_fails_closed_on_checksum_mismatch(tmp_path, monkeypatch):
    directory = tmp_path / "fictional"
    make_bundle(directory)

    def unexpected(_content):
        pytest.fail("A workbook was parsed before all candidate assets were verified")

    monkeypatch.setattr(reviewer, "extract_verified_workbook", unexpected)
    path = directory / "wip.csv"
    original = path.read_bytes()
    path.write_bytes(original + bytes([10]))
    with pytest.raises(reviewer.SourceCandidateError, match="candidate file is unavailable"):
        reviewer.inspect_source_candidates(directory)
    path.write_bytes(b"X" + original[1:])
    with pytest.raises(reviewer.SourceCandidateError, match="candidate checksum changed"):
        reviewer.inspect_source_candidates(directory)
