"""Nine original baseline tests with a fictional reviewed transfer history."""

import json
from pathlib import Path
import sys

import pytest

from transfer_baseline import (
    InternalPanelFlexBaselineError,
    load_internal_panel_flex_transfer_baseline,
    summarize_internal_panel_flex_transfer_baseline,
    transfer_event_identity,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_transfers import make_transfers


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    root = tmp_path / "fictional"
    make_transfers(root)
    return root


def _load(root: Path):
    return load_internal_panel_flex_transfer_baseline(root / "baseline.json", assembly_path=root / "approved-assemblies.json")


def _write_candidate(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_reviewed_baseline_matches_record_and_quantity_gates(sample: Path) -> None:
    baseline = _load(sample)

    assert len(baseline.records) == 29
    assert sum(record.quantity for record in baseline.records) == 1305
    assert [record.source_row_number for record in baseline.records] == list(
        range(1, 30)
    )
    assert all(record.status == "CLOSED" for record in baseline.records)
    assert baseline.database_ingestion_authorized is False
    assert baseline.proves_hla_consumption is False


def test_reviewed_baseline_preserves_totals_by_assembly(sample: Path) -> None:
    summary = summarize_internal_panel_flex_transfer_baseline(_load(sample))

    assert summary.totals_by_assembly == {
        "9900001": 243, "9900002": 261, "9900003": 279, "9900004": 297, "9900005": 225,
    }
    assert summary.record_count == 29
    assert summary.total_quantity == 1305
    assert summary.database_writes is False
    assert summary.proves_hla_consumption is False


def test_reviewed_baseline_preserves_observed_event_window(sample: Path) -> None:
    summary = summarize_internal_panel_flex_transfer_baseline(_load(sample))

    assert summary.first_observed_event.isoformat() == "2031-01-01T12:00:00-05:00"
    assert summary.last_observed_event.isoformat() == "2031-01-29T12:00:00-04:00"


def test_transfer_event_identity_is_deterministic_and_row_specific(sample: Path) -> None:
    baseline = _load(sample)

    first = transfer_event_identity(baseline.source_sha256, 1)
    replay = transfer_event_identity(baseline.source_sha256, 1)
    second = transfer_event_identity(baseline.source_sha256, 2)
    assert first == replay
    assert first != second
    assert len(first) == 64


def test_transfer_identity_rejects_unapproved_event_type(sample: Path) -> None:
    baseline = _load(sample)

    with pytest.raises(InternalPanelFlexBaselineError, match="not authorized"):
        transfer_event_identity(baseline.source_sha256, 1, "HLA_CONSUMPTION")


def test_baseline_rejects_unknown_product(sample: Path, tmp_path: Path) -> None:
    payload = json.loads((sample / "baseline.json").read_bytes())
    payload["records"][0]["assembly"] = "9999999"

    with pytest.raises(InternalPanelFlexBaselineError):
        load_internal_panel_flex_transfer_baseline(
            _write_candidate(tmp_path, payload), assembly_path=sample / "approved-assemblies.json",
        )


def test_baseline_rejects_duplicate_or_reordered_source_rows(sample: Path, tmp_path: Path) -> None:
    payload = json.loads((sample / "baseline.json").read_bytes())
    payload["records"][1]["source_row_number"] = 1

    with pytest.raises(InternalPanelFlexBaselineError):
        load_internal_panel_flex_transfer_baseline(
            _write_candidate(tmp_path, payload), assembly_path=sample / "approved-assemblies.json",
        )


def test_baseline_rejects_checksum_drift(sample: Path, tmp_path: Path) -> None:
    payload = json.loads((sample / "baseline.json").read_bytes())
    payload["records"][0]["quantity"] += 1

    with pytest.raises(InternalPanelFlexBaselineError):
        load_internal_panel_flex_transfer_baseline(
            _write_candidate(tmp_path, payload), assembly_path=sample / "approved-assemblies.json",
        )


def test_baseline_rejects_ingestion_authority_expansion(sample: Path, tmp_path: Path) -> None:
    payload = json.loads((sample / "baseline.json").read_bytes())
    payload["database_ingestion_authorized"] = True

    with pytest.raises(InternalPanelFlexBaselineError):
        load_internal_panel_flex_transfer_baseline(
            _write_candidate(tmp_path, payload), assembly_path=sample / "approved-assemblies.json",
        )
