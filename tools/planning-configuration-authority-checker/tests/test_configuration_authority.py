"""Six original offline reconciliation cases adapted to fictional inputs."""

from pathlib import Path
import json
import sys

import pytest

from configuration_authority import build_gate_b_configuration_coverage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_configuration import make_configuration


@pytest.fixture
def root(tmp_path: Path) -> Path:
    bundle = tmp_path / "fictional"
    make_configuration(bundle)
    return bundle


def result(root: Path, *observed: str):
    return build_gate_b_configuration_coverage(
        policy_path=root / "policy.json",
        detailed_configuration_path=root / "detail.json",
        part_mapping_path=root / "part-map.json",
        product_authority_matrix_path=root / "product-matrix.json",
        evidence_root=root,
        observed_part_numbers=observed,
    )


def test_gate_b_inventory_is_complete_explicit_and_fail_closed(root):
    report = result(root)
    assert report.integrity_status == "PASS"
    assert report.gate_b_status == "BLOCKED"
    assert report.audit_id == "planning-configuration-authority-v1"
    assert report.product_authority_matrix_revision == "2.0.0"
    assert report.product_authority_matrix_status == "DEVELOPMENT_AUTHORITY_MATRIX_PARTIAL"
    assert report.retained_product_count == 23
    assert report.configured_product_count == 12
    assert report.detailed_product_count == 4
    assert report.timing_review_pending_count == 8
    assert report.fail_closed_product_count == 11
    assert report.comparison_factor_products == 4
    assert report.recommendation_factor == "1.00"
    assert report.legacy_comparison_factor == "1.10"
    assert report.early_wip_loss_rate == "0.20"
    assert report.silent_fallback_count == 0
    assert report.plans_generated == 0
    assert report.database_writes is False
    assert report.production_authority is False


def test_gate_b_reconciles_current_os_parts_without_inventing_values(root):
    report = result(root, "DEMO-01", "DEMO-02", "DEMO-03", "DEMO-05", "DEMO-13", "DEMO-14", "DEMO-14")
    assert report.integrity_status == "PASS"
    assert report.unknown_observed_part_numbers == ()
    assert report.observed_fail_closed_part_numbers == ("DEMO-13", "DEMO-14")
    assert report.observed_os_part_numbers == ("DEMO-01", "DEMO-02", "DEMO-03", "DEMO-05", "DEMO-13", "DEMO-14")
    observed_closed = [row for row in report.products if row.part_number in {"DEMO-13", "DEMO-14"}]
    assert len(observed_closed) == 2
    assert all(row.coverage_state == "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED" for row in observed_closed)
    assert all(row.lot_size is None and row.lead_time_days is None for row in observed_closed)


def test_unknown_living_os_part_is_a_conflict_not_a_fallback(root):
    report = result(root, "UNKNOWN-123")
    assert report.integrity_status == "FAIL"
    assert report.gate_b_status == "BLOCKED"
    assert report.unknown_observed_part_numbers == ("UNKNOWN-123",)
    assert any(issue.code == "OBSERVED_OS_PART_OUTSIDE_AUTHORITY" and issue.severity == "CONFLICT"
               for issue in report.issues)
    assert report.silent_fallback_count == 0


def test_part_modality_drift_fails_integrity(root):
    path = root / "part-map.json"
    payload = json.loads(path.read_bytes())
    payload["part_to_modality"]["DEMO-01"] = "TYPE-04"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = result(root)
    assert report.integrity_status == "FAIL"
    assert any(issue.code == "PART_MODALITY_CONFLICT" for issue in report.issues)


def test_detailed_lot_quantity_drift_fails_integrity(root):
    path = root / "detail.json"
    payload = json.loads(path.read_bytes())
    payload["products"][0]["expected_lot_start_quantity"] = 97
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = result(root)
    assert report.integrity_status == "FAIL"
    assert any(issue.code == "DETAIL_LOT_SIZE_CONFLICT" for issue in report.issues)


def test_gate_b_evidence_is_deterministic(root):
    first = result(root, "DEMO-01", "DEMO-13")
    second = result(root, "DEMO-13", " demo-01 ")
    assert first == second
    assert first.result_sha256 == second.result_sha256
    assert len(first.result_sha256) == 64
