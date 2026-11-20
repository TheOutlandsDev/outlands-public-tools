"""Reconcile saved planning configuration and product authority without creating a plan."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from authority_inputs import (
    AuthoritativeFlexPlanningPolicy,
    PTLAGateBError,
    PTLAProductAuthorityMatrix,
    PartModalityConfiguration,
    PlanningConfiguration,
    load_source,
    validate_matrix_source_hashes,
)


class GateBProductCoverage(BaseModel):
    """One retained product and its exact planning-authority state."""

    modality: str = Field(min_length=3, max_length=12)
    part_number: str = Field(min_length=1, max_length=40)
    product_name: str | None = Field(default=None, max_length=160)
    accepted_part_aliases: tuple[str, ...] = ()
    demand_authority: str = Field(min_length=1, max_length=100)
    lot_prefix: str | None = Field(default=None, max_length=20)
    coverage_state: Literal[
        "DETAILED_CONFIGURATION",
        "TIMING_REVIEW_PENDING",
        "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED",
    ]
    lot_size: int | None = Field(default=None, gt=0, le=10_000)
    legacy_reference_lot_size: int | None = Field(default=None, gt=0, le=10_000)
    lot_size_authority: str = Field(min_length=1, max_length=80)
    flow_name: str | None = Field(default=None, max_length=256)
    route_version: int | None = Field(default=None, gt=0)
    route_authority: str = Field(min_length=1, max_length=80)
    operation_to_kanban_count: int | None = Field(default=None, ge=1, le=500)
    operation_to_kanban_authority: str = Field(min_length=1, max_length=80)
    lead_time_days: int | None = Field(default=None, gt=0, le=365)
    legacy_reference_lead_time_days: int | None = Field(
        default=None, gt=0, le=365
    )
    timing_authority: str = Field(min_length=1, max_length=80)
    timing_exception_count: int | None = Field(default=None, ge=0, le=100)
    business_review_status: str = Field(min_length=1, max_length=80)
    technical_validation_status: str = Field(min_length=1, max_length=80)
    observed_in_os: bool
    reason: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateBIssue(BaseModel):
    """One bounded Gate B conflict or outstanding business input."""

    code: str = Field(min_length=1, max_length=80)
    severity: Literal["CONFLICT", "BUSINESS_INPUT_REQUIRED"]
    subject: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class GateBConfigurationCoverage(BaseModel):
    """Deterministic, read-only evidence for the all-product Gate B boundary."""

    audit_id: Literal["planning-configuration-authority-v1"]
    integrity_status: Literal["PASS", "FAIL"]
    gate_b_status: Literal["COMPLETE", "BLOCKED"]
    policy_id: str
    policy_revision: str
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    product_authority_matrix_id: str
    product_authority_matrix_revision: str
    product_authority_matrix_status: str
    product_authority_matrix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    detailed_configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    part_mapping_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retained_product_count: int = Field(ge=0)
    configured_product_count: int = Field(ge=0)
    detailed_product_count: int = Field(ge=0)
    timing_review_pending_count: int = Field(ge=0)
    fail_closed_product_count: int = Field(ge=0)
    observed_os_part_numbers: tuple[str, ...]
    observed_fail_closed_part_numbers: tuple[str, ...]
    unknown_observed_part_numbers: tuple[str, ...]
    comparison_factor_products: int = Field(ge=0)
    recommendation_factor: Literal["1.00"]
    legacy_comparison_factor: Literal["1.10"]
    legacy_comparison_factor_status: Literal["COMPARISON_ONLY_NOT_EXECUTABLE"]
    early_wip_loss_rate: Literal["0.20"]
    early_wip_loss_authority: Literal["LEGACY_REFERENCE_ONLY_GATE_C_PENDING"]
    silent_fallback_count: Literal[0] = 0
    plans_generated: Literal[0] = 0
    database_writes: Literal[False] = False
    production_authority: Literal[False] = False
    products: tuple[GateBProductCoverage, ...]
    issues: tuple[GateBIssue, ...]
    result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")


def _result_sha256(values: dict[str, object]) -> str:
    return sha256(
        json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _append_issue(
    issues: list[GateBIssue],
    *,
    code: str,
    severity: Literal["CONFLICT", "BUSINESS_INPUT_REQUIRED"],
    subject: str,
    detail: str,
) -> None:
    issues.append(
        GateBIssue(
            code=code,
            severity=severity,
            subject=subject,
            detail=detail,
        )
    )


def build_gate_b_configuration_coverage(
    *,
    policy_path: Path,
    detailed_configuration_path: Path,
    part_mapping_path: Path,
    product_authority_matrix_path: Path,
    evidence_root: Path,
    observed_part_numbers: Iterable[str] = (),
) -> GateBConfigurationCoverage:
    """Reconcile all retained product identities without calculating a plan."""
    policy, policy_digest = load_source(policy_path, AuthoritativeFlexPlanningPolicy)
    matrix, matrix_digest = load_source(product_authority_matrix_path, PTLAProductAuthorityMatrix)
    validate_matrix_source_hashes(matrix, evidence_root)
    detailed, detail_digest = load_source(detailed_configuration_path, PlanningConfiguration)
    part_mapping, mapping_digest = load_source(part_mapping_path, PartModalityConfiguration)

    observed = tuple(
        sorted({value.strip().upper() for value in observed_part_numbers if value.strip()})
    )
    observed_set = set(observed)
    configured_by_part = {item.part_number: item for item in policy.configured_products}
    fail_closed_by_part = {
        item.part_number: item for item in policy.fail_closed_products
    }
    authority_by_part = {**configured_by_part, **fail_closed_by_part}
    detailed_by_part = {item.part_number: item for item in detailed.products}
    matrix_by_part = {
        item.canonical_part_number: item for item in matrix.products
    }

    issues: list[GateBIssue] = []
    products: list[GateBProductCoverage] = []

    # The retained part map must agree exactly with the policy catalog.
    mapping_parts = set(part_mapping.part_to_modality)
    authority_parts = set(authority_by_part)
    for part in sorted(authority_parts - mapping_parts):
        _append_issue(
            issues,
            code="AUTHORITY_PART_MISSING_FROM_RETAINED_MAP",
            severity="CONFLICT",
            subject=part,
            detail="The authoritative product is absent from the retained part map.",
        )
    for part in sorted(mapping_parts - authority_parts):
        _append_issue(
            issues,
            code="RETAINED_MAP_PART_MISSING_FROM_AUTHORITY",
            severity="CONFLICT",
            subject=part,
            detail="The retained part map contains no authoritative policy state.",
        )
    for part in sorted(authority_parts & mapping_parts):
        expected_modality = authority_by_part[part].modality
        if part_mapping.part_to_modality[part] != expected_modality:
            _append_issue(
                issues,
                code="PART_MODALITY_CONFLICT",
                severity="CONFLICT",
                subject=part,
                detail=(
                    "The retained part map and authoritative policy assign different "
                    "modalities."
                ),
            )

    # The field-level matrix must cover the exact same retained catalog.
    for part in sorted(set(authority_by_part) - set(matrix_by_part)):
        _append_issue(
            issues,
            code="AUTHORITY_PART_MISSING_FROM_PRODUCT_MATRIX",
            severity="CONFLICT",
            subject=part,
            detail="The active policy product is absent from the authority matrix.",
        )
    for part in sorted(set(matrix_by_part) - set(authority_by_part)):
        _append_issue(
            issues,
            code="PRODUCT_MATRIX_PART_OUTSIDE_AUTHORITY",
            severity="CONFLICT",
            subject=part,
            detail="The authority matrix contains a product outside the active policy.",
        )

    # Detailed planning values may exist only for configured authority products.
    for part in sorted(set(detailed_by_part) - set(configured_by_part)):
        _append_issue(
            issues,
            code="DETAIL_CONFIGURATION_OUTSIDE_AUTHORITY",
            severity="CONFLICT",
            subject=part,
            detail="A detailed planning configuration exists outside the configured policy set.",
        )

    comparison_factor_products = 0
    for entry in matrix.products:
        policy_item = authority_by_part.get(entry.canonical_part_number)
        detail = detailed_by_part.get(entry.canonical_part_number)
        if policy_item is None:
            continue
        if entry.modality != policy_item.modality:
            _append_issue(
                issues,
                code="MATRIX_MODALITY_CONFLICT",
                severity="CONFLICT",
                subject=entry.canonical_part_number,
                detail="The product matrix and active policy modalities disagree.",
            )

        if entry.coverage_state == "DETAILED_CONFIGURATION":
            if entry.canonical_part_number not in configured_by_part or detail is None:
                _append_issue(
                    issues,
                    code="DETAILED_MATRIX_PRODUCT_NOT_CONFIGURED",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="A detailed matrix product lacks configured policy detail.",
                )
            elif detail.modality != entry.modality:
                _append_issue(
                    issues,
                    code="DETAIL_MODALITY_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="Detailed planning and policy modalities disagree.",
                )
            elif detail.expected_lot_start_quantity != entry.lot_size_circuits:
                _append_issue(
                    issues,
                    code="DETAIL_LOT_SIZE_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="Detailed planning and authoritative lot quantities disagree.",
                )
            elif (
                detail.flow_name != entry.flow_name
                or detail.route_version != entry.route_version
                or len(detail.operation_to_kanban)
                != entry.operation_to_kanban_count
                or detail.kanban_days_remaining
                != entry.kanban_days_remaining
                or len(detail.timing_exceptions) != entry.timing_exception_count
            ):
                _append_issue(
                    issues,
                    code="DETAIL_ROUTE_OR_TIMING_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="Detailed route, K1-K7, or timing values disagree with the matrix.",
                )
            if detail is not None and str(detail.uncovered_demand_start_factor) == "1.10":
                comparison_factor_products += 1
            elif detail is not None:
                _append_issue(
                    issues,
                    code="DETAIL_COMPARISON_FACTOR_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail=(
                        "The detailed reference must retain 1.10 only for the final "
                        "legacy comparison while runtime authority remains 1.00."
                    ),
                )
        elif entry.coverage_state == "TIMING_REVIEW_PENDING":
            if entry.canonical_part_number not in configured_by_part or detail is not None:
                _append_issue(
                    issues,
                    code="TIMING_PENDING_MATRIX_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="The timing-pending matrix state conflicts with configured detail.",
                )
            _append_issue(
                issues,
                code="PRODUCT_TIMING_REVIEW_PENDING",
                severity="BUSINESS_INPUT_REQUIRED",
                subject=entry.canonical_part_number,
                detail=entry.coverage_reason,
            )
        else:
            if entry.canonical_part_number not in fail_closed_by_part or detail is not None:
                _append_issue(
                    issues,
                    code="FAIL_CLOSED_MATRIX_CONFLICT",
                    severity="CONFLICT",
                    subject=entry.canonical_part_number,
                    detail="The fail-closed matrix state conflicts with active policy detail.",
                )
            _append_issue(
                issues,
                code="PRODUCT_FAIL_CLOSED",
                severity="BUSINESS_INPUT_REQUIRED",
                subject=entry.canonical_part_number,
                detail=entry.coverage_reason,
            )

        products.append(
            GateBProductCoverage(
                modality=entry.modality,
                part_number=entry.canonical_part_number,
                product_name=entry.product_name,
                accepted_part_aliases=entry.accepted_part_aliases,
                demand_authority=entry.demand_authority,
                lot_prefix=entry.lot_prefix,
                coverage_state=entry.coverage_state,
                lot_size=entry.lot_size_circuits,
                legacy_reference_lot_size=entry.legacy_reference_lot_size_circuits,
                lot_size_authority=entry.lot_size_authority,
                flow_name=entry.flow_name,
                route_version=entry.route_version,
                route_authority=entry.route_authority,
                operation_to_kanban_count=entry.operation_to_kanban_count,
                operation_to_kanban_authority=entry.operation_to_kanban_authority,
                lead_time_days=entry.lead_time_days,
                legacy_reference_lead_time_days=(
                    entry.legacy_reference_lead_time_days
                ),
                timing_authority=entry.timing_authority,
                timing_exception_count=entry.timing_exception_count,
                business_review_status=entry.business_review.status,
                technical_validation_status=entry.technical_validation.status,
                observed_in_os=entry.canonical_part_number in observed_set,
                reason=entry.coverage_reason,
            )
        )

    unknown_observed = tuple(sorted(observed_set - authority_parts))
    for part in unknown_observed:
        _append_issue(
            issues,
            code="OBSERVED_OS_PART_OUTSIDE_AUTHORITY",
            severity="CONFLICT",
            subject=part,
            detail="The saved order observations contain a part with no authoritative planning state.",
        )

    observed_fail_closed = tuple(
        sorted(observed_set & set(fail_closed_by_part))
    )
    ordered_products = tuple(sorted(products, key=lambda row: (row.modality, row.part_number)))
    ordered_issues = tuple(
        sorted(issues, key=lambda row: (row.severity, row.code, row.subject))
    )
    conflicts = tuple(issue for issue in ordered_issues if issue.severity == "CONFLICT")
    timing_pending_count = sum(
        row.coverage_state == "TIMING_REVIEW_PENDING" for row in ordered_products
    )
    fail_closed_count = sum(
        row.coverage_state == "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
        for row in ordered_products
    )
    detailed_count = sum(
        row.coverage_state == "DETAILED_CONFIGURATION" for row in ordered_products
    )
    gate_complete = (
        not ordered_issues
        and detailed_count == len(ordered_products)
        and matrix.status == "DEVELOPMENT_AUTHORITY_MATRIX_COMPLETE"
    )

    values: dict[str, object] = {
        "audit_id": "planning-configuration-authority-v1",
        "integrity_status": "PASS" if not conflicts else "FAIL",
        "gate_b_status": "COMPLETE" if gate_complete else "BLOCKED",
        "policy_id": policy.policy_id,
        "policy_revision": policy.policy_revision,
        "policy_sha256": policy_digest,
        "product_authority_matrix_id": matrix.matrix_id,
        "product_authority_matrix_revision": matrix.matrix_revision,
        "product_authority_matrix_status": matrix.status,
        "product_authority_matrix_sha256": matrix_digest,
        "detailed_configuration_sha256": detail_digest,
        "part_mapping_sha256": mapping_digest,
        "retained_product_count": len(ordered_products),
        "configured_product_count": len(policy.configured_products),
        "detailed_product_count": detailed_count,
        "timing_review_pending_count": timing_pending_count,
        "fail_closed_product_count": fail_closed_count,
        "observed_os_part_numbers": observed,
        "observed_fail_closed_part_numbers": observed_fail_closed,
        "unknown_observed_part_numbers": unknown_observed,
        "comparison_factor_products": comparison_factor_products,
        "recommendation_factor": matrix.recommendation_factor,
        "legacy_comparison_factor": matrix.legacy_comparison_factor,
        "legacy_comparison_factor_status": matrix.legacy_comparison_factor_status,
        "early_wip_loss_rate": matrix.early_wip_loss_rate,
        "early_wip_loss_authority": matrix.early_wip_loss_authority,
        "silent_fallback_count": 0,
        "plans_generated": 0,
        "database_writes": False,
        "production_authority": False,
        "products": [row.model_dump(mode="json") for row in ordered_products],
        "issues": [row.model_dump(mode="json") for row in ordered_issues],
    }
    return GateBConfigurationCoverage(
        **values,
        result_sha256=_result_sha256(values),
    )


def authority_summary(result: GateBConfigurationCoverage) -> dict[str, str | int]:
    """Return the Program Authority Verifier's configuration coverage report."""
    return {
        "integrity_status": result.integrity_status,
        "gate_status": result.gate_b_status,
        "retained_products": result.retained_product_count,
        "configured_products": result.configured_product_count,
        "detailed_products": result.detailed_product_count,
        "timing_review_pending_products": result.timing_review_pending_count,
        "fail_closed_products": result.fail_closed_product_count,
        "fingerprint": result.result_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing the four JSON sources and pinned evidence")
    parser.add_argument("--observed-part", action="append", default=[], help="Part observed in saved orders")
    parser.add_argument("--authority-summary", action="store_true", help="Emit a configuration coverage report")
    args = parser.parse_args()
    try:
        if len(args.observed_part) > 500 or any(len(part.strip()) > 40 for part in args.observed_part):
            raise PTLAGateBError("Observed part numbers exceed the supported limits.")
        result = build_gate_b_configuration_coverage(
            policy_path=args.root / "policy.json",
            detailed_configuration_path=args.root / "detail.json",
            part_mapping_path=args.root / "part-map.json",
            product_authority_matrix_path=args.root / "product-matrix.json",
            evidence_root=args.root,
            observed_part_numbers=args.observed_part,
        )
    except PTLAGateBError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (ValidationError, OSError, RuntimeError):
        print("A controlled configuration could not be reconciled.", file=sys.stderr)
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
