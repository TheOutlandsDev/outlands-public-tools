"""All eleven original fixture coverage cases using fictional evidence."""

from inspect import getsource
import json
from pathlib import Path
import sys

import pytest

import fixture_coverage as gate_c_module
from fixture_coverage import build_gate_c_fixture_coverage, load_configuration_report

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_fixture_catalog import make_fixture_catalog


@pytest.fixture
def root(tmp_path: Path) -> Path:
    directory = tmp_path / "fictional"
    make_fixture_catalog(directory)
    return directory


def _result(root: Path, *, catalog_path: Path | None = None):
    return build_gate_c_fixture_coverage(
        project_root=root, catalog_path=catalog_path or root / "fixture-catalog.json",
        gate_b=load_configuration_report(root / "configuration-report.json"),
    )


def _candidate_catalog(root: Path, mutate) -> Path:
    payload = json.loads((root / "fixture-catalog.json").read_bytes())
    mutate(payload)
    candidate = root / "candidate.json"
    candidate.write_text(json.dumps(payload), encoding="utf-8")
    return candidate


def test_gate_c_scaffold_is_integral_explicit_and_fail_closed(root: Path) -> None:
    result = _result(root)

    assert result.integrity_status == "PASS"
    assert result.gate_c_status == "BLOCKED"
    assert result.gate_b_status == "BLOCKED"
    assert result.retained_product_count == 23
    assert result.detailed_product_count == 4
    assert result.gate_b_timing_review_pending_count == 8
    assert result.gate_b_fail_closed_product_count == 11
    assert result.gate_b_pending_product_count == 19
    assert result.catalog_product_evidence_count == 4
    assert result.dedicated_fixture_count == 3
    assert result.authoritative_expected_value_fixture_count == 0
    assert result.legacy_comparison_fixture_count == 3
    assert result.snapshot_comparison_count == 1
    assert result.dedicated_fixture_products == (
        "DEMO-01",
        "DEMO-02",
        "DEMO-03",
    )
    assert result.snapshot_comparison_products == ("DEMO-04",)
    assert result.detailed_without_dedicated_fixture == ("DEMO-04",)
    assert len(result.retained_without_dedicated_fixture) == 20
    assert result.required_scenario_count == 11
    assert result.scenario_evidence_count == 11
    assert result.reusable_scenario_count == 4
    assert result.partial_scenario_count == 7
    assert result.missing_scenarios == ()
    assert result.test_source_count == 3
    assert result.test_node_reference_count == 16
    assert result.unique_test_node_count == 15
    assert result.business_values_created is False
    assert result.calculations_executed == 0
    assert result.expected_values_generated == 0
    assert result.plans_generated == 0
    assert result.test_nodes_executed == 0
    assert result.database_reads is False
    assert result.database_writes is False
    assert result.silent_fallback_count == 0
    assert result.production_authority is False


def test_gate_c_scenario_gaps_remain_visible(root: Path) -> None:
    result = _result(root)

    assert result.reusable_scenarios == (
        "EDITED",
        "EXACT_BOUNDARY",
        "SHIPPED",
        "WIP_SHORTAGE",
    )
    assert result.partial_scenarios == (
        "CANCELLED",
        "FUTURE",
        "LATE",
        "PARTIALLY_SHIPPED",
        "REPEATED_INGESTION",
        "VERIFICATION_LOT",
        "WIP_SURPLUS",
    )
    partial_issues = {
        issue.subject
        for issue in result.issues
        if issue.code == "SCENARIO_EVIDENCE_PARTIAL"
    }
    assert partial_issues == set(result.partial_scenarios)


def test_legacy_recommendation_values_are_comparison_only(root: Path) -> None:
    result = _result(root)

    expectation_issues = {
        issue.subject
        for issue in result.issues
        if issue.code == "AUTHORITATIVE_EXPECTATION_FIXTURE_REQUIRED"
    }
    assert expectation_issues == {
        "DEMO-01",
        "DEMO-02",
        "DEMO-03",
    }
    assert result.authoritative_expected_value_fixture_count == 0


def test_gate_c_evidence_is_deterministic(root: Path) -> None:
    first = _result(root)
    second = _result(root)

    assert first == second
    assert first.result_sha256 == second.result_sha256
    assert len(first.result_sha256) == 64


def test_fixture_hash_tampering_fails_integrity(root: Path) -> None:
    candidate = _candidate_catalog(
        root,
        lambda payload: payload["product_evidence"][0].__setitem__(
            "source_sha256", "0" * 64
        ),
    )

    result = _result(root, catalog_path=candidate)

    assert result.integrity_status == "FAIL"
    assert result.gate_c_status == "BLOCKED"
    assert any(
        issue.code == "EVIDENCE_SOURCE_HASH_MISMATCH" for issue in result.issues
    )
    assert "DEMO-01" in result.retained_without_dedicated_fixture
    assert result.dedicated_fixture_count == 2


def test_missing_scenario_test_node_fails_integrity(root: Path) -> None:
    def mutate(payload) -> None:
        payload["scenario_evidence"][0]["test_nodes"] = [
            "tests/test_scenario_0.py::test_does_not_exist"
        ]

    result = _result(root, catalog_path=_candidate_catalog(root, mutate))

    assert result.integrity_status == "FAIL"
    assert any(
        issue.code == "SCENARIO_TEST_NODE_UNAVAILABLE" for issue in result.issues
    )


def test_missing_scenario_is_an_explicit_blocker(root: Path) -> None:
    def mutate(payload) -> None:
        payload["scenario_evidence"] = payload["scenario_evidence"][:-1]

    result = _result(root, catalog_path=_candidate_catalog(root, mutate))

    assert result.integrity_status == "FAIL"
    assert result.gate_c_status == "BLOCKED"
    assert result.missing_scenarios == ("VERIFICATION_LOT",)
    assert any(
        issue.code == "SCENARIO_FIXTURE_REQUIRED"
        and issue.subject == "VERIFICATION_LOT"
        for issue in result.issues
    )


def test_scenario_order_drift_fails_integrity(root: Path) -> None:
    def mutate(payload) -> None:
        payload["scenario_evidence"][0], payload["scenario_evidence"][1] = (
            payload["scenario_evidence"][1],
            payload["scenario_evidence"][0],
        )

    result = _result(root, catalog_path=_candidate_catalog(root, mutate))

    assert result.integrity_status == "FAIL"
    assert any(issue.code == "SCENARIO_EVIDENCE_ORDER_DRIFT" for issue in result.issues)


def test_partial_scenario_without_gap_fails_integrity(root: Path) -> None:
    def mutate(payload) -> None:
        partial = next(
            row
            for row in payload["scenario_evidence"]
            if row["coverage_status"] == "PARTIAL"
        )
        partial["gap"] = None

    result = _result(root, catalog_path=_candidate_catalog(root, mutate))

    assert result.integrity_status == "FAIL"
    assert any(issue.code == "PARTIAL_SCENARIO_GAP_MISSING" for issue in result.issues)


def test_dedicated_fixture_cannot_claim_authoritative_expectations(
    root: Path,
) -> None:
    def mutate(payload) -> None:
        payload["product_evidence"][0][
            "recommendation_expectation_authority"
        ] = "AGGREGATE_SNAPSHOT_ONLY"

    result = _result(root, catalog_path=_candidate_catalog(root, mutate))

    assert result.integrity_status == "FAIL"
    assert any(
        issue.code == "DEDICATED_EXPECTATION_AUTHORITY_CONFLICT"
        for issue in result.issues
    )


def test_gate_c_module_has_no_runtime_database_network_or_planner_imports() -> None:
    source = getsource(gate_c_module)

    forbidden_imports = (
        "import httpx",
        "import requests",
        "import socket",
        "import psycopg",
        "import clickhouse",
        "from .repository",
        "from .flex_planning import build",
        "from .automatic_lot_starts",
    )
    assert all(value not in source for value in forbidden_imports)
    assert "ast.parse" in source
