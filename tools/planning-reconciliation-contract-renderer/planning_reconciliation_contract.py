"""Validate and render a saved planning reconciliation contract."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


MAX_CONTRACT_BYTES = 512 * 1024
SAFE_STATUS = "DOCUMENTED_BEFORE_RECONCILIATION_IMPLEMENTATION"


class ContractError(ValueError):
    """Raised when the documented system boundary is missing or unsafe."""


class AuthorityEntry(BaseModel):
    system: str = Field(min_length=1, max_length=120)
    owns: str = Field(min_length=1, max_length=500)
    write_policy: str = Field(min_length=1, max_length=300)
    counting_role: str = Field(min_length=1, max_length=500)
    notes: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class DataFreshnessEntry(BaseModel):
    source_id: str = Field(pattern=r"^[a-z][a-z0-9-]+$")
    source: str = Field(min_length=1, max_length=120)
    classification: Literal[
        "CURRENT_AUTHORITY",
        "ACCEPTED_SNAPSHOT",
        "HISTORICAL_REFERENCE",
        "FROZEN_COMPARISON",
        "PENDING_SOURCE",
    ]
    date_meaning: str = Field(min_length=1, max_length=500)
    operational_use: str = Field(min_length=1, max_length=500)
    review_policy: str = Field(min_length=1, max_length=500)
    audience_behavior: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class MetricAuthorityEntry(BaseModel):
    metric: str = Field(min_length=1, max_length=120)
    display_location: str = Field(min_length=1, max_length=120)
    authoritative_source: str = Field(min_length=1, max_length=300)
    formula: str = Field(min_length=1, max_length=500)
    includes: str = Field(min_length=1, max_length=500)
    excludes: str = Field(min_length=1, max_length=500)
    relationship: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class StateEntry(BaseModel):
    workflow: str = Field(min_length=1, max_length=120)
    state: str = Field(pattern=r"^[A-Z][A-Z0-9_]+$")
    meaning: str = Field(min_length=1, max_length=500)
    counting_bucket: str = Field(min_length=1, max_length=300)
    next_states: tuple[str, ...]
    implementation_status: Literal[
        "ACTIVE_SOURCE_OBSERVATION",
        "ACTIVE_WORKFLOW_STATE",
        "PLANNED_RECONCILIATION_STATE",
    ]

    model_config = ConfigDict(frozen=True, extra="forbid")


class CountingRule(BaseModel):
    rule_id: str = Field(pattern=r"^COUNT-[0-9]{3}$")
    title: str = Field(min_length=1, max_length=120)
    expression: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ReconciliationEntry(BaseModel):
    condition: str = Field(min_length=1, max_length=500)
    counting_result: str = Field(min_length=1, max_length=500)
    system_action: str = Field(min_length=1, max_length=500)
    human_action: str = Field(min_length=1, max_length=300)

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityRule(BaseModel):
    rule_id: str = Field(pattern=r"^IDENTITY-[0-9]{3}$")
    rule: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class FailureMode(BaseModel):
    condition: str = Field(min_length=1, max_length=300)
    behavior: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ChangeEntry(BaseModel):
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    application_version: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ReconciliationContract(BaseModel):
    contract_id: Literal["planning-reconciliation"]
    contract_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    status: Literal["DOCUMENTED_BEFORE_RECONCILIATION_IMPLEMENTATION"]
    effective_date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    technical_owner: str = Field(min_length=1, max_length=120)
    environment: Literal["development-only"]
    purpose: str = Field(min_length=1, max_length=800)
    development_only: Literal[True]
    database_writes: Literal[False]
    reconciliation_active: Literal[False]
    authority_matrix: tuple[AuthorityEntry, ...] = Field(min_length=5)
    data_freshness_matrix: tuple[DataFreshnessEntry, ...] = Field(min_length=5)
    metric_authority_matrix: tuple[MetricAuthorityEntry, ...] = Field(min_length=6)
    state_matrix: tuple[StateEntry, ...] = Field(min_length=6)
    counting_rules: tuple[CountingRule, ...] = Field(min_length=4)
    reconciliation_matrix: tuple[ReconciliationEntry, ...] = Field(min_length=5)
    identity_rules: tuple[IdentityRule, ...] = Field(min_length=4)
    failure_modes: tuple[FailureMode, ...] = Field(min_length=4)
    design_notes: tuple[str, ...] = Field(min_length=5)
    change_history: tuple[ChangeEntry, ...] = Field(min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_safe_semantics(self):
        if self.status != SAFE_STATUS:
            raise ValueError("The reconciliation contract status is unsafe.")
        for values, label in (
            ([row.rule_id for row in self.counting_rules], "counting rule"),
            ([row.rule_id for row in self.identity_rules], "identity rule"),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"A {label} identifier is duplicated.")
        states = {row.state for row in self.state_matrix}
        required_states = {
            "READY_FOR_LOGISTICS",
            "COMPLETE_AWAITING_TRANSFER",
            "TRANSFERRED",
            "RECONCILED",
            "BLOCKED_MISMATCH",
        }
        if not required_states.issubset(states):
            raise ValueError("The documented reconciliation states are incomplete.")
        metrics = {row.metric for row in self.metric_authority_matrix}
        required_metrics = {
            "Production demand",
            "Accepted planning WIP",
            "Completed-state WIP",
            "Late production lines",
            "Team-ready quantity",
            "Assembly WIP",
        }
        if not required_metrics.issubset(metrics):
            raise ValueError("The metric authority matrix is incomplete.")
        freshness_sources = {row.source_id for row in self.data_freshness_matrix}
        if freshness_sources != {
            "current-orders",
            "accepted-wip",
            "assembly-history",
            "planning-comparison",
            "external-evidence",
        }:
            raise ValueError("The source freshness matrix is incomplete.")
        formula = self.counting_rules[0].expression
        if "Current observed live WIP" not in formula or "team-cleared" not in formula:
            raise ValueError("The effective-WIP formula is incomplete.")
        return self


class SavedMetrics(BaseModel):
    observed_assembly_lots: int | None = Field(default=None, ge=0)
    observed_assembly_quantity: int | None = Field(default=None, ge=0)
    source_filename: str | None = None
    source_sha256: str | None = None
    source_revision_at: str | None = None
    lifecycle_records: int | None = Field(default=None, ge=0)
    awaiting_transfer: int | None = Field(default=None, ge=0)
    transferred: int | None = Field(default=None, ge=0)
    app_cleared_pending_source_sync: None = None
    reconciled_records: None = None
    blocked_mismatches: None = None
    ignored_duplicates: None = None
    reconciliation_mode: Literal["DOCUMENTED_NOT_ACTIVE"] = "DOCUMENTED_NOT_ACTIVE"
    database_writes: Literal[False] = False

    model_config = ConfigDict(frozen=True, extra="forbid")


class SavedFreshness(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    status: str = Field(min_length=1, max_length=120)
    freshness: str = Field(min_length=1, max_length=120)
    effective_display: str = Field(min_length=1, max_length=120)
    operational: bool
    detail: str = Field(min_length=1, max_length=500)

    model_config = ConfigDict(frozen=True, extra="forbid")


def _read_bounded(path: Path) -> bytes:
    if not path.is_file():
        raise ContractError("An input file is unavailable.")
    with path.open("rb") as stream:
        content = stream.read(MAX_CONTRACT_BYTES + 1)
    if not 0 < len(content) <= MAX_CONTRACT_BYTES:
        raise ContractError("An input file is empty or oversized.")
    return content


def load_contract(path: Path) -> ReconciliationContract:
    try:
        return ReconciliationContract.model_validate_json(_read_bounded(path))
    except ContractError:
        raise
    except (OSError, ValueError) as exc:
        raise ContractError("The planning reconciliation contract is invalid.") from exc


def render_contract_text(
    contract: ReconciliationContract,
    metrics: SavedMetrics | None = None,
    freshness: Sequence[SavedFreshness] | None = None,
) -> str:
    """Render the complete version-controlled contract as durable plain text."""

    lines = [
        "PLANNING RECONCILIATION CONTRACT",
        "=" * len("PLANNING RECONCILIATION CONTRACT"),
        f"Contract: {contract.contract_id} v{contract.contract_version}",
        f"Status: {contract.status}",
        f"Effective date: {contract.effective_date}",
        f"Technical owner: {contract.technical_owner}",
        f"Environment: {contract.environment}",
        f"Database writes: {str(contract.database_writes).lower()}",
        f"Reconciliation active: {str(contract.reconciliation_active).lower()}",
        "",
        "PURPOSE",
        contract.purpose,
    ]
    if metrics is not None:
        lines.extend(
            [
                "",
                "CURRENT READ-ONLY METRICS",
                f"Observed assembly lots: {metrics.observed_assembly_lots if metrics.observed_assembly_lots is not None else 'Unavailable'}",
                f"Observed assembly quantity: {metrics.observed_assembly_quantity if metrics.observed_assembly_quantity is not None else 'Unavailable'}",
                f"Lifecycle records: {metrics.lifecycle_records if metrics.lifecycle_records is not None else 'Unavailable'}",
                f"Awaiting transfer: {metrics.awaiting_transfer if metrics.awaiting_transfer is not None else 'Unavailable'}",
                f"Transferred: {metrics.transferred if metrics.transferred is not None else 'Unavailable'}",
                "Future reconciliation metrics: Not active",
            ]
        )
    if freshness is not None:
        lines.extend(["", "CURRENT SOURCE CLASSIFICATIONS"])
        for source in freshness:
            lines.extend(
                [
                    f"{source.label}: {source.status} / {source.freshness}",
                    f"  Effective date: {source.effective_display}",
                    f"  Operational: {str(source.operational).lower()}",
                    f"  Detail: {source.detail}",
                ]
            )

    def section(title: str) -> None:
        lines.extend(["", title, "-" * len(title)])

    section("AUTHORITY MATRIX")
    for row in contract.authority_matrix:
        lines.extend(
            [
                row.system,
                f"  Owns: {row.owns}",
                f"  Write policy: {row.write_policy}",
                f"  Counting role: {row.counting_role}",
                f"  Notes: {row.notes}",
            ]
        )
    section("DATA FRESHNESS POLICY")
    for row in contract.data_freshness_matrix:
        lines.extend(
            [
                f"{row.source} [{row.source_id}] \u2014 {row.classification}",
                f"  Date meaning: {row.date_meaning}",
                f"  Operational use: {row.operational_use}",
                f"  Review policy: {row.review_policy}",
                f"  Audience behavior: {row.audience_behavior}",
            ]
        )
    section("METRIC AUTHORITY MATRIX")
    for row in contract.metric_authority_matrix:
        lines.extend(
            [
                f"{row.metric} ({row.display_location})",
                f"  Source: {row.authoritative_source}",
                f"  Formula: {row.formula}",
                f"  Includes: {row.includes}",
                f"  Excludes: {row.excludes}",
                f"  Relationship: {row.relationship}",
            ]
        )
    section("STATE MATRIX")
    for row in contract.state_matrix:
        lines.extend(
            [
                f"{row.workflow} / {row.state} [{row.implementation_status}]",
                f"  Meaning: {row.meaning}",
                f"  Counting bucket: {row.counting_bucket}",
                f"  Next states: {', '.join(row.next_states) if row.next_states else 'None'}",
            ]
        )
    section("COUNTING LOGIC")
    for row in contract.counting_rules:
        lines.extend([f"{row.rule_id} \u2014 {row.title}", f"  {row.expression}", f"  {row.explanation}"])
    section("RECONCILIATION DECISION MATRIX")
    for row in contract.reconciliation_matrix:
        lines.extend(
            [
                f"Condition: {row.condition}",
                f"  Counting result: {row.counting_result}",
                f"  System action: {row.system_action}",
                f"  Human action: {row.human_action}",
            ]
        )
    section("IDENTITY RULES")
    lines.extend(f"{row.rule_id} \u2014 {row.rule}" for row in contract.identity_rules)
    section("FAILURE BEHAVIOR")
    for row in contract.failure_modes:
        lines.extend([f"{row.condition}", f"  Behavior: {row.behavior}", f"  Reason: {row.reason}"])
    section("DESIGN NOTES")
    lines.extend(f"- {note}" for note in contract.design_notes)
    section("CHANGE HISTORY")
    lines.extend(
        f"{row.date} | v{row.version} | app {row.application_version} | {row.summary}"
        for row in contract.change_history
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path, help="Saved reconciliation contract in JSON")
    parser.add_argument("--metrics", type=Path, help="Optional saved read-only metrics in JSON")
    parser.add_argument("--freshness", type=Path, help="Optional saved source classifications in JSON")
    args = parser.parse_args()
    try:
        contract = load_contract(args.contract)
        metrics = SavedMetrics.model_validate_json(_read_bounded(args.metrics)) if args.metrics else None
        freshness = (
            TypeAdapter(tuple[SavedFreshness, ...]).validate_json(_read_bounded(args.freshness))
            if args.freshness else None
        )
    except ContractError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("The saved metrics or classifications are invalid.", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(render_contract_text(contract, metrics, freshness).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
