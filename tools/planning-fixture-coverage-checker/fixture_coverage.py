"""Read-only Gate C fixture inventory and integrity scaffold.

The scaffold inventories reviewed fixture evidence and existing scenario tests.
It never invents expected business values, executes a plan, writes a database,
or grants production authority. Missing product fixtures remain explicit and
fail closed until Gate B business inputs and reviewed expected results exist.
"""

from __future__ import annotations

import argparse
import ast
from datetime import date
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import stat
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, model_validator

MAX_INPUT_BYTES = 2 * 1024 * 1024


class ConfigurationProduct(BaseModel):
    part_number: str = Field(min_length=1, max_length=40)
    modality: str = Field(min_length=3, max_length=12)
    coverage_state: Literal["DETAILED_CONFIGURATION", "TIMING_REVIEW_PENDING",
                            "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"]


class GateBConfigurationCoverage(BaseModel):
    """Review fields used from the saved Configuration Authority Checker report."""

    integrity_status: Literal["PASS", "FAIL"]
    gate_b_status: Literal["COMPLETE", "BLOCKED"]
    products: tuple[ConfigurationProduct, ...] = Field(min_length=1, max_length=500)
    detailed_product_count: int = Field(strict=True, ge=0, le=500)
    timing_review_pending_count: int = Field(strict=True, ge=0, le=500)
    fail_closed_product_count: int = Field(strict=True, ge=0, le=500)
    comparison_factor_products: int = Field(strict=True, ge=0, le=500)
    result_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def check_product_counts(self) -> "GateBConfigurationCoverage":
        if len({row.part_number for row in self.products}) != len(self.products):
            raise ValueError("Configuration coverage has duplicate product identities.")
        for state, expected in (
            ("DETAILED_CONFIGURATION", self.detailed_product_count),
            ("TIMING_REVIEW_PENDING", self.timing_review_pending_count),
            ("FAIL_CLOSED_BUSINESS_INPUT_REQUIRED", self.fail_closed_product_count),
        ):
            if sum(row.coverage_state == state for row in self.products) != expected:
                raise ValueError("Configuration coverage counts disagree with the product rows.")
        return self


ScenarioName = Literal[
    "SHIPPED",
    "PARTIALLY_SHIPPED",
    "EDITED",
    "CANCELLED",
    "REPEATED_INGESTION",
    "FUTURE",
    "LATE",
    "EXACT_BOUNDARY",
    "WIP_SURPLUS",
    "WIP_SHORTAGE",
    "VERIFICATION_LOT",
]

REQUIRED_SCENARIOS: tuple[str, ...] = (
    "SHIPPED",
    "PARTIALLY_SHIPPED",
    "EDITED",
    "CANCELLED",
    "REPEATED_INGESTION",
    "FUTURE",
    "LATE",
    "EXACT_BOUNDARY",
    "WIP_SURPLUS",
    "WIP_SHORTAGE",
    "VERIFICATION_LOT",
)


class PTLAGateCError(ValueError):
    """Raised when the controlled Gate C catalog cannot be loaded."""


class GateCProductEvidence(BaseModel):
    modality: str = Field(min_length=3, max_length=12)
    part_number: str = Field(min_length=1, max_length=40)
    evidence_kind: Literal[
        "DEDICATED_REVIEWED_FIXTURE",
        "CONTROLLED_SNAPSHOT_COMPARISON",
    ]
    source_path: str = Field(min_length=1, max_length=240)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dedicated_fixture: StrictBool
    authority_status: str = Field(min_length=1, max_length=100)
    recommendation_expectation_authority: Literal[
        "LEGACY_1_10_COMPARISON_ONLY",
        "AGGREGATE_SNAPSHOT_ONLY",
    ]

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateCScenarioEvidence(BaseModel):
    scenario: ScenarioName
    coverage_status: Literal["REUSABLE", "PARTIAL"]
    gap: str | None = Field(default=None, max_length=500)
    test_nodes: tuple[str, ...] = Field(min_length=1, max_length=20)

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateCTestSource(BaseModel):
    source_path: str = Field(max_length=100, pattern=r"^tests/[A-Za-z0-9_./-]+\.py$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateCFixtureCatalog(BaseModel):
    catalog_id: Literal["planning-fixture-catalog-v1"]
    status: Literal["DEVELOPMENT_SCAFFOLD_NOT_PARITY_COMPLETE"]
    prepared_on: date
    technical_owner: str = Field(min_length=1, max_length=100)
    business_values_created: Literal[False]
    calculations_executed: Literal[0]
    expected_values_generated: Literal[0]
    plans_generated: Literal[0]
    test_nodes_executed: Literal[0]
    database_reads: Literal[False]
    database_writes: Literal[False]
    silent_fallback_count: Literal[0]
    production_authority: Literal[False]
    required_scenarios: tuple[ScenarioName, ...] = Field(max_length=32)
    test_sources: tuple[GateCTestSource, ...] = Field(min_length=1, max_length=20)
    product_evidence: tuple[GateCProductEvidence, ...] = Field(max_length=500)
    scenario_evidence: tuple[GateCScenarioEvidence, ...] = Field(max_length=32)

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateCIssue(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    severity: Literal["CONFLICT", "FIXTURE_REQUIRED", "GATE_BLOCKED"]
    subject: str = Field(min_length=1, max_length=100)
    detail: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateCFixtureCoverage(BaseModel):
    audit_id: Literal["planning-fixture-coverage-v1"]
    integrity_status: Literal["PASS", "FAIL"]
    gate_c_status: Literal["READY", "BLOCKED"]
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gate_b_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    gate_b_status: Literal["COMPLETE", "BLOCKED"]
    retained_product_count: int = Field(ge=0)
    detailed_product_count: int = Field(ge=0)
    gate_b_timing_review_pending_count: int = Field(ge=0)
    gate_b_fail_closed_product_count: int = Field(ge=0)
    gate_b_pending_product_count: int = Field(ge=0)
    catalog_product_evidence_count: int = Field(ge=0)
    dedicated_fixture_count: int = Field(ge=0)
    authoritative_expected_value_fixture_count: Literal[0] = 0
    legacy_comparison_fixture_count: int = Field(ge=0)
    snapshot_comparison_count: int = Field(ge=0)
    dedicated_fixture_products: tuple[str, ...]
    snapshot_comparison_products: tuple[str, ...]
    detailed_without_dedicated_fixture: tuple[str, ...]
    retained_without_dedicated_fixture: tuple[str, ...]
    required_scenario_count: int = Field(ge=0)
    scenario_evidence_count: int = Field(ge=0)
    reusable_scenario_count: int = Field(ge=0)
    partial_scenario_count: int = Field(ge=0)
    reusable_scenarios: tuple[str, ...]
    partial_scenarios: tuple[str, ...]
    missing_scenarios: tuple[str, ...]
    test_source_count: int = Field(ge=0)
    test_source_hashes: tuple[str, ...]
    test_node_reference_count: int = Field(ge=0)
    unique_test_node_count: int = Field(ge=0)
    business_values_created: Literal[False] = False
    calculations_executed: Literal[0] = 0
    expected_values_generated: Literal[0] = 0
    plans_generated: Literal[0] = 0
    test_nodes_executed: Literal[0] = 0
    database_reads: Literal[False] = False
    database_writes: Literal[False] = False
    silent_fallback_count: Literal[0] = 0
    production_authority: Literal[False] = False
    issues: tuple[GateCIssue, ...]
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")


def _read_source(path: Path) -> bytes:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise PTLAGateCError("A controlled evidence source must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise PTLAGateCError("A controlled evidence source is unavailable.") from exc
    if not 0 < len(content) <= MAX_INPUT_BYTES:
        raise PTLAGateCError("A controlled evidence source is empty or oversized.")
    return content


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise PTLAGateCError("A controlled JSON source has duplicate fields.")
    return fields


def _invalid_constant(_value):
    raise PTLAGateCError("A controlled JSON source has a non-finite number.")


def _load_json(content):
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
    except (ValueError, RecursionError) as exc:
        raise PTLAGateCError("A controlled JSON source is invalid.") from exc
    if not isinstance(payload, dict):
        raise PTLAGateCError("A controlled JSON source must be an object.")
    return payload


def _result_sha256(values: dict[str, object]) -> str:
    return sha256(
        json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _load_catalog(content: bytes) -> GateCFixtureCatalog:
    payload = _load_json(content)
    for key, expected in (
        ("business_values_created", False), ("calculations_executed", 0),
        ("expected_values_generated", 0), ("plans_generated", 0),
        ("test_nodes_executed", 0), ("database_reads", False),
        ("database_writes", False), ("silent_fallback_count", 0), ("production_authority", False),
    ):
        value = payload.get(key)
        if type(value) is not type(expected) or value != expected:
            raise PTLAGateCError("The evidence catalog must exclude runtime activity and production authority.")
    # Pydantic parses the catalog's ISO date from JSON.
    return GateCFixtureCatalog.model_validate(payload)


def load_configuration_report(path: Path) -> GateBConfigurationCoverage:
    payload = _load_json(_read_source(path))
    recorded = payload.pop("result_sha256", None)
    if not isinstance(recorded, str) or recorded != _result_sha256(payload):
        raise PTLAGateCError("The configuration report fingerprint does not match.")
    return GateBConfigurationCoverage.model_validate({**payload, "result_sha256": recorded})


def _append_issue(
    issues: list[GateCIssue],
    *,
    code: str,
    severity: Literal["CONFLICT", "FIXTURE_REQUIRED", "GATE_BLOCKED"],
    subject: str,
    detail: str,
) -> None:
    issues.append(
        GateCIssue(
            code=code,
            severity=severity,
            subject=subject,
            detail=detail,
        )
    )


def _controlled_path(root: Path, value: str) -> Path | None:
    name = PurePosixPath(value)
    if (not name.name or name.is_absolute() or ".." in name.parts
            or name.as_posix() != value or any(ch in value for ch in "\\\x00:")):
        return None
    directory = root
    try:
        for part in name.parts[:-1]:
            directory /= part
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                return None
        path = directory / name.name
        return path if path.resolve().is_relative_to(root) else None
    except (OSError, ValueError, RuntimeError):
        return None


def _fixture_identity(content: bytes) -> tuple[str | None, str | None, str | None]:
    payload = _load_json(content)
    return payload.get("modality"), payload.get("part_number"), payload.get("status")


def _test_functions(content: bytes) -> set[str]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError, RecursionError):
        return set()
    return {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def build_gate_c_fixture_coverage(
    *,
    project_root: Path,
    catalog_path: Path,
    gate_b: GateBConfigurationCoverage,
) -> GateCFixtureCoverage:
    """Validate fixture provenance and gaps without running calculations."""

    root = project_root.resolve()
    try:
        relative_catalog = catalog_path.absolute().relative_to(root).as_posix()
    except ValueError as exc:
        raise PTLAGateCError("The fixture catalog must reside inside the supplied root.") from exc
    controlled_catalog = _controlled_path(root, relative_catalog)
    if controlled_catalog is None:
        raise PTLAGateCError("The fixture catalog must reside inside the supplied root.")
    catalog_bytes = _read_source(controlled_catalog)
    catalog = _load_catalog(catalog_bytes)
    issues: list[GateCIssue] = []

    gate_b_products = {row.part_number: row for row in gate_b.products}
    retained_parts = set(gate_b_products)
    detailed_parts = {
        row.part_number
        for row in gate_b.products
        if row.coverage_state == "DETAILED_CONFIGURATION"
    }
    seen_products: set[str] = set()
    dedicated_parts: set[str] = set()
    snapshot_parts: set[str] = set()
    legacy_comparison_parts: set[str] = set()

    for evidence in catalog.product_evidence:
        evidence_valid = True
        if evidence.part_number in seen_products:
            _append_issue(
                issues,
                code="DUPLICATE_PRODUCT_EVIDENCE",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="The Gate C catalog contains duplicate product evidence.",
            )
            evidence_valid = False
        seen_products.add(evidence.part_number)

        authority = gate_b_products.get(evidence.part_number)
        if authority is None:
            _append_issue(
                issues,
                code="EVIDENCE_OUTSIDE_RETAINED_AUTHORITY",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="Fixture evidence exists outside the retained Gate B catalog.",
            )
            evidence_valid = False
        elif authority.modality != evidence.modality:
            _append_issue(
                issues,
                code="EVIDENCE_MODALITY_CONFLICT",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="Fixture evidence and Gate B authority assign different modalities.",
            )
            evidence_valid = False
        elif evidence.part_number not in detailed_parts:
            _append_issue(
                issues,
                code="EVIDENCE_PRECEDES_DETAILED_AUTHORITY",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="Product fixture evidence cannot precede detailed Gate B authority.",
            )
            evidence_valid = False

        source = _controlled_path(root, evidence.source_path)
        try:
            if source is None:
                raise PTLAGateCError("The fixture path is uncontrolled.")
            source_bytes = _read_source(source)
        except PTLAGateCError:
            _append_issue(
                issues,
                code="EVIDENCE_SOURCE_UNAVAILABLE",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="The fixture source is missing or outside the project root.",
            )
            continue
        if sha256(source_bytes).hexdigest() != evidence.source_sha256:
            _append_issue(
                issues,
                code="EVIDENCE_SOURCE_HASH_MISMATCH",
                severity="CONFLICT",
                subject=evidence.part_number,
                detail="The fixture source no longer matches its tracked SHA-256.",
            )
            continue

        if evidence.evidence_kind == "DEDICATED_REVIEWED_FIXTURE":
            if not evidence.dedicated_fixture:
                _append_issue(
                    issues,
                    code="DEDICATED_FIXTURE_FLAG_CONFLICT",
                    severity="CONFLICT",
                    subject=evidence.part_number,
                    detail="Dedicated fixture evidence must carry a true fixture flag.",
                )
                evidence_valid = False
            try:
                modality, part_number, status = _fixture_identity(source_bytes)
            except PTLAGateCError:
                _append_issue(
                    issues,
                    code="DEDICATED_FIXTURE_INVALID",
                    severity="CONFLICT",
                    subject=evidence.part_number,
                    detail="The dedicated fixture is not a valid JSON object.",
                )
                evidence_valid = False
            else:
                if (modality, part_number, status) != (
                    evidence.modality,
                    evidence.part_number,
                    evidence.authority_status,
                ):
                    _append_issue(
                        issues,
                        code="DEDICATED_FIXTURE_IDENTITY_CONFLICT",
                        severity="CONFLICT",
                        subject=evidence.part_number,
                        detail="The fixture identity or approval status has drifted.",
                    )
                    evidence_valid = False
            if (
                evidence.recommendation_expectation_authority
                != "LEGACY_1_10_COMPARISON_ONLY"
            ):
                _append_issue(
                    issues,
                    code="DEDICATED_EXPECTATION_AUTHORITY_CONFLICT",
                    severity="CONFLICT",
                    subject=evidence.part_number,
                    detail=(
                        "Existing dedicated fixture recommendation values are legacy "
                        "1.10 comparison evidence only."
                    ),
                )
                evidence_valid = False
            if evidence_valid:
                dedicated_parts.add(evidence.part_number)
                legacy_comparison_parts.add(evidence.part_number)
                _append_issue(
                    issues,
                    code="AUTHORITATIVE_EXPECTATION_FIXTURE_REQUIRED",
                    severity="FIXTURE_REQUIRED",
                    subject=evidence.part_number,
                    detail=(
                        "The legacy 1.10 comparison result must not certify the active "
                        "1.00 policy; an owner-reviewed authoritative result is required."
                    ),
                )
        else:
            if evidence.dedicated_fixture:
                _append_issue(
                    issues,
                    code="SNAPSHOT_FIXTURE_FLAG_CONFLICT",
                    severity="CONFLICT",
                    subject=evidence.part_number,
                    detail="Snapshot comparison evidence is not a dedicated product fixture.",
                )
                evidence_valid = False
            if (
                evidence.recommendation_expectation_authority
                != "AGGREGATE_SNAPSHOT_ONLY"
            ):
                _append_issue(
                    issues,
                    code="SNAPSHOT_EXPECTATION_AUTHORITY_CONFLICT",
                    severity="CONFLICT",
                    subject=evidence.part_number,
                    detail=(
                        "Aggregate snapshot evidence cannot be presented as a reviewed "
                        "product-specific expected result."
                    ),
                )
                evidence_valid = False
            if evidence_valid:
                snapshot_parts.add(evidence.part_number)

    scenario_names = [row.scenario for row in catalog.scenario_evidence]
    test_source_paths: dict[str, GateCTestSource] = {}
    test_functions: dict[str, set[str]] = {}
    for test_source in catalog.test_sources:
        if test_source.source_path in test_source_paths:
            _append_issue(
                issues,
                code="DUPLICATE_TEST_SOURCE",
                severity="CONFLICT",
                subject=test_source.source_path,
                detail="A scenario test source is pinned more than once.",
            )
        test_source_paths[test_source.source_path] = test_source
        source_path = _controlled_path(root, test_source.source_path)
        try:
            if source_path is None:
                raise PTLAGateCError("The test path is uncontrolled.")
            test_bytes = _read_source(source_path)
        except PTLAGateCError:
            _append_issue(
                issues,
                code="TEST_SOURCE_UNAVAILABLE",
                severity="CONFLICT",
                subject=test_source.source_path,
                detail="A pinned scenario test source is missing or uncontrolled.",
            )
            continue
        if sha256(test_bytes).hexdigest() != test_source.source_sha256:
            _append_issue(
                issues,
                code="TEST_SOURCE_HASH_MISMATCH",
                severity="CONFLICT",
                subject=test_source.source_path,
                detail="A scenario test source no longer matches its tracked SHA-256.",
            )
        else:
            test_functions[test_source.source_path] = _test_functions(test_bytes)
    if tuple(catalog.required_scenarios) != REQUIRED_SCENARIOS:
        _append_issue(
            issues,
            code="REQUIRED_SCENARIO_CONTRACT_DRIFT",
            severity="CONFLICT",
            subject="scenario-catalog",
            detail="The required Gate C scenario list has changed or been reordered.",
        )
    if len(scenario_names) != len(set(scenario_names)):
        _append_issue(
            issues,
            code="DUPLICATE_SCENARIO_EVIDENCE",
            severity="CONFLICT",
            subject="scenario-catalog",
            detail="The Gate C catalog contains duplicate scenario evidence.",
        )
    if tuple(scenario_names) != REQUIRED_SCENARIOS:
        _append_issue(
            issues,
            code="SCENARIO_EVIDENCE_ORDER_DRIFT",
            severity="CONFLICT",
            subject="scenario-catalog",
            detail="Scenario evidence must retain the controlled required-scenario order.",
        )

    missing_scenarios = tuple(sorted(set(REQUIRED_SCENARIOS) - set(scenario_names)))
    for scenario_name in missing_scenarios:
        _append_issue(
            issues,
            code="SCENARIO_FIXTURE_REQUIRED",
            severity="FIXTURE_REQUIRED",
            subject=scenario_name,
            detail="Required Gate C scenario evidence is missing.",
        )
    for scenario in catalog.scenario_evidence:
        if scenario.coverage_status == "REUSABLE" and scenario.gap is not None:
            _append_issue(
                issues,
                code="REUSABLE_SCENARIO_GAP_CONFLICT",
                severity="CONFLICT",
                subject=scenario.scenario,
                detail="A reusable scenario cannot carry an unresolved evidence gap.",
            )
        if scenario.coverage_status == "PARTIAL":
            if not scenario.gap:
                _append_issue(
                    issues,
                    code="PARTIAL_SCENARIO_GAP_MISSING",
                    severity="CONFLICT",
                    subject=scenario.scenario,
                    detail="Partial scenario coverage requires a bounded gap statement.",
                )
            _append_issue(
                issues,
                code="SCENARIO_EVIDENCE_PARTIAL",
                severity="FIXTURE_REQUIRED",
                subject=scenario.scenario,
                detail=scenario.gap or "Scenario evidence remains incomplete.",
            )
        for node_id in scenario.test_nodes:
            try:
                relative_path, function_name = node_id.split("::", 1)
            except ValueError:
                relative_path, function_name = "", ""
            if relative_path not in test_source_paths:
                _append_issue(
                    issues,
                    code="SCENARIO_TEST_SOURCE_UNPINNED",
                    severity="CONFLICT",
                    subject=scenario.scenario,
                    detail="Every referenced scenario test file requires a pinned SHA-256.",
                )
            if (
                not relative_path.startswith("tests/")
                or not function_name.startswith("test_")
                or function_name not in test_functions.get(relative_path, ())
            ):
                _append_issue(
                    issues,
                    code="SCENARIO_TEST_NODE_UNAVAILABLE",
                    severity="CONFLICT",
                    subject=scenario.scenario,
                    detail="A referenced scenario test node is missing or invalid.",
                )

    detailed_without_dedicated = tuple(sorted(detailed_parts - dedicated_parts))
    retained_without_dedicated = tuple(sorted(retained_parts - dedicated_parts))
    for part_number in retained_without_dedicated:
        _append_issue(
            issues,
            code="DEDICATED_PRODUCT_FIXTURE_REQUIRED",
            severity="FIXTURE_REQUIRED",
            subject=part_number,
            detail=(
                "A reviewed product-specific Gate C source-to-result fixture is "
                "not yet available."
            ),
        )
    if gate_b.gate_b_status != "COMPLETE":
        _append_issue(
            issues,
            code="GATE_B_NOT_COMPLETE",
            severity="GATE_BLOCKED",
            subject="gate-b",
            detail="Gate C cannot complete before all required Gate B authority exists.",
        )
    if gate_b.integrity_status != "PASS":
        _append_issue(
            issues,
            code="GATE_B_INTEGRITY_FAILED",
            severity="CONFLICT",
            subject="gate-b",
            detail="Gate C cannot rely on a Gate B result whose integrity failed.",
        )
    if gate_b.comparison_factor_products != gate_b.detailed_product_count:
        _append_issue(
            issues,
            code="GATE_B_COMPARISON_FACTOR_COVERAGE_CONFLICT",
            severity="CONFLICT",
            subject="gate-b",
            detail=(
                "Every detailed fixture product must retain 1.10 only as legacy "
                "comparison evidence while runtime authority remains 1.00."
            ),
        )

    reusable_scenarios = tuple(
        sorted(
            row.scenario
            for row in catalog.scenario_evidence
            if row.coverage_status == "REUSABLE"
        )
    )
    partial_scenarios = tuple(
        sorted(
            row.scenario
            for row in catalog.scenario_evidence
            if row.coverage_status == "PARTIAL"
        )
    )

    ordered_issues = tuple(
        sorted(issues, key=lambda row: (row.severity, row.code, row.subject))
    )
    conflicts = tuple(issue for issue in ordered_issues if issue.severity == "CONFLICT")
    gate_ready = (
        not ordered_issues
        and gate_b.gate_b_status == "COMPLETE"
        and not retained_without_dedicated
        and not missing_scenarios
        and not partial_scenarios
        and len(legacy_comparison_parts) == 0
    )
    values: dict[str, object] = {
        "audit_id": "planning-fixture-coverage-v1",
        "integrity_status": "PASS" if not conflicts else "FAIL",
        "gate_c_status": "READY" if gate_ready else "BLOCKED",
        "catalog_sha256": sha256(catalog_bytes).hexdigest(),
        "gate_b_result_sha256": gate_b.result_sha256,
        "gate_b_status": gate_b.gate_b_status,
        "retained_product_count": len(retained_parts),
        "detailed_product_count": len(detailed_parts),
        "gate_b_timing_review_pending_count": gate_b.timing_review_pending_count,
        "gate_b_fail_closed_product_count": gate_b.fail_closed_product_count,
        "gate_b_pending_product_count": (
            gate_b.timing_review_pending_count + gate_b.fail_closed_product_count
        ),
        "catalog_product_evidence_count": len(catalog.product_evidence),
        "dedicated_fixture_count": len(dedicated_parts),
        "authoritative_expected_value_fixture_count": 0,
        "legacy_comparison_fixture_count": len(legacy_comparison_parts),
        "snapshot_comparison_count": len(snapshot_parts),
        "dedicated_fixture_products": tuple(sorted(dedicated_parts)),
        "snapshot_comparison_products": tuple(sorted(snapshot_parts)),
        "detailed_without_dedicated_fixture": detailed_without_dedicated,
        "retained_without_dedicated_fixture": retained_without_dedicated,
        "required_scenario_count": len(REQUIRED_SCENARIOS),
        "scenario_evidence_count": len(set(scenario_names)),
        "reusable_scenario_count": len(reusable_scenarios),
        "partial_scenario_count": len(partial_scenarios),
        "reusable_scenarios": reusable_scenarios,
        "partial_scenarios": partial_scenarios,
        "missing_scenarios": missing_scenarios,
        "test_source_count": len(test_source_paths),
        "test_source_hashes": tuple(
            f"{path}:{test_source_paths[path].source_sha256}"
            for path in sorted(test_source_paths)
        ),
        "test_node_reference_count": sum(
            len(scenario.test_nodes) for scenario in catalog.scenario_evidence
        ),
        "unique_test_node_count": len(
            {
                node_id
                for scenario in catalog.scenario_evidence
                for node_id in scenario.test_nodes
            }
        ),
        "business_values_created": False,
        "calculations_executed": 0,
        "expected_values_generated": 0,
        "plans_generated": 0,
        "test_nodes_executed": 0,
        "database_reads": False,
        "database_writes": False,
        "silent_fallback_count": 0,
        "production_authority": False,
        "issues": [issue.model_dump(mode="json") for issue in ordered_issues],
    }
    return GateCFixtureCoverage(
        **values,
        result_sha256=_result_sha256(values),
    )


def authority_summary(result: GateCFixtureCoverage) -> dict[str, str | int]:
    """Build the saved fixture coverage report consumed by the Program Authority Verifier."""
    return {
        "integrity_status": result.integrity_status,
        "gate_status": result.gate_c_status,
        "authoritative_expected_value_fixtures": result.authoritative_expected_value_fixture_count,
        "legacy_comparison_fixtures": result.legacy_comparison_fixture_count,
        "required_scenarios": result.required_scenario_count,
        "reusable_scenarios": result.reusable_scenario_count,
        "partial_scenarios": result.partial_scenario_count,
        "fingerprint": result.result_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing the fixture catalog and evidence")
    parser.add_argument("--configuration-report", required=True, type=Path, help="Saved full configuration report JSON")
    parser.add_argument("--authority-summary", action="store_true", help="Emit a fixture coverage summary")
    args = parser.parse_args()
    try:
        result = build_gate_c_fixture_coverage(
            project_root=args.root,
            catalog_path=args.root / "fixture-catalog.json",
            gate_b=load_configuration_report(args.configuration_report),
        )
    except PTLAGateCError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValidationError, OSError, ValueError, RuntimeError, RecursionError):
        print("A saved report or fixture catalog is invalid.", file=sys.stderr)
        return 2
    if args.authority_summary:
        if result.integrity_status == "FAIL":
            print("Resolve integrity conflicts before exporting an authority summary.", file=sys.stderr)
            return 2
        print(json.dumps(authority_summary(result), sort_keys=True))
    else:
        print(result.model_dump_json())
    return 0 if result.integrity_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
