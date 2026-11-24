"""Project a saved policy onto a checksum-pinned detailed planning configuration."""

from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


DETAILED_CONFIGURATION_PATH = "data/flex_planning/configuration_v1.json"
MAX_POLICY_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024


class AuthoritativeFlexPolicyError(ValueError):
    """A saved policy or source cannot be used for the overlay."""


class PlanningValidationError(ValueError):
    """Raised when planning input cannot be evaluated safely."""


class ReviewStatus(str, Enum):
    """Manufacturing-authority status for a controlled planning value."""

    DRAFT_LEGACY_SOURCE = "DRAFT_LEGACY_SOURCE"


class ParameterProvenance(BaseModel):
    """Traceability attached to one reviewed group of planning values."""

    source: str = Field(min_length=1, max_length=256)
    review_status: ReviewStatus
    reviewed_by: str = Field(min_length=1, max_length=120)
    reviewed_on: date

    model_config = ConfigDict(frozen=True)


class PriorityRuleConfiguration(BaseModel):
    """Explicit replacement for the legacy priority thresholds."""

    severe_schedule_lateness_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_min_days: int = Field(gt=0, le=365)
    moderate_schedule_lateness_max_days: int = Field(gt=0, le=365)
    future_shipment_rank_limit: int = Field(ge=2, le=8)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "PriorityRuleConfiguration":
        if (
            self.moderate_schedule_lateness_min_days
            > self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("moderate schedule-lateness thresholds are reversed")
        if (
            self.severe_schedule_lateness_days
            <= self.moderate_schedule_lateness_max_days
        ):
            raise ValueError("severe lateness must exceed the moderate range")
        return self


class TimingException(BaseModel):
    """One explicit product/operation timing override, if later approved."""

    exception_id: str = Field(min_length=1, max_length=100)
    operation: str | None = Field(default=None, min_length=1, max_length=256)
    lot_prefix: str | None = Field(default=None, min_length=1, max_length=40)
    days_remaining_override: int = Field(ge=0, le=365)
    provenance: ParameterProvenance

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_selector(self) -> "TimingException":
        if self.operation is None and self.lot_prefix is None:
            raise ValueError("timing exception requires an operation or lot prefix")
        return self


class ProductPlanningConfiguration(BaseModel):
    """Reviewed planning constants for one supported product."""

    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    flow_name: str = Field(min_length=1, max_length=256)
    route_version: int = Field(gt=0)
    expected_lot_start_quantity: int = Field(gt=0)
    uncovered_demand_start_factor: Decimal = Field(ge=Decimal("1"), le=Decimal("2"))
    operation_to_kanban: dict[str, int] = Field(min_length=1)
    kanban_days_remaining: dict[int, int]
    priority_rules: PriorityRuleConfiguration
    timing_exceptions: tuple[TimingException, ...]
    parameter_provenance: dict[str, ParameterProvenance]

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_controlled_mappings(self) -> "ProductPlanningConfiguration":
        if set(self.kanban_days_remaining) != set(range(1, 8)):
            raise ValueError("kanban_days_remaining must define Kanbans 1 through 7")
        if any(value < 0 for value in self.kanban_days_remaining.values()):
            raise ValueError("kanban days remaining must not be negative")
        if any(value not in range(1, 8) for value in self.operation_to_kanban.values()):
            raise ValueError("every operation must map to Kanban 1 through 7")
        required_provenance = {
            "expected_lot_start_quantity",
            "uncovered_demand_start_factor",
            "operation_to_kanban",
            "kanban_days_remaining",
            "priority_rules",
            "timing_exceptions",
        }
        if set(self.parameter_provenance) != required_provenance:
            raise ValueError("parameter provenance keys are incomplete or unexpected")
        exception_ids = [item.exception_id for item in self.timing_exceptions]
        if len(exception_ids) != len(set(exception_ids)):
            raise ValueError("timing exception IDs must be unique")
        return self


class PlanningConfiguration(BaseModel):
    """Versioned collection of reviewed product configurations."""

    configuration_id: str = Field(min_length=1, max_length=100)
    configuration_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    effective_date: date
    source_set: str = Field(min_length=1, max_length=256)
    status: str = Field(pattern=r"^APPROVED_MANUAL_GATE_1$")
    products: tuple[ProductPlanningConfiguration, ...] = Field(min_length=1)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "PlanningConfiguration":
        modalities = [product.modality for product in self.products]
        part_numbers = [product.part_number for product in self.products]
        if len(modalities) != len(set(modalities)):
            raise ValueError("product modalities must be unique")
        if len(part_numbers) != len(set(part_numbers)):
            raise ValueError("product part numbers must be unique")
        return self

    def product(self, modality: str, part_number: str) -> ProductPlanningConfiguration:
        matches = [
            product
            for product in self.products
            if product.modality == modality and product.part_number == part_number
        ]
        if len(matches) != 1:
            raise PlanningValidationError(
                f"unsupported product identity: modality={modality!r}, part_number={part_number!r}"
            )
        return matches[0]


class CalculationRules(BaseModel):
    recommendation_factor: Literal["1.00"]
    legacy_comparison_factor: Literal["1.10"]
    legacy_comparison_factor_status: Literal["COMPARISON_ONLY_NOT_EXECUTABLE"]

    model_config = ConfigDict(frozen=True, extra="forbid")


class ConfiguredProduct(BaseModel):
    modality: str = Field(min_length=1, max_length=40)
    part_number: str = Field(min_length=1, max_length=40)
    lot_size: int = Field(gt=0, le=10_000, strict=True)

    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceFileReconciliation(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_relative_path(self):
        path = PurePosixPath(self.path)
        if (
            path.as_posix() != self.path
            or path.is_absolute()
            or not path.parts
            or any(
                part in (".", "..")
                or part.endswith(".")
                or re.fullmatch(r"[A-Za-z0-9_.-]+", part) is None
                for part in path.parts
            )
        ):
            raise ValueError("Reconciled sources require portable relative paths.")
        return self


class AuthoritativeFlexPlanningPolicy(BaseModel):
    policy_id: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    policy_revision: str = Field(pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    status: Literal["CANDIDATE_NOT_ACTIVE"]
    production_authority: Literal[False]
    calculation_rules: CalculationRules
    configured_products: tuple[ConfiguredProduct, ...] = Field(min_length=1)
    source_file_reconciliation: tuple[SourceFileReconciliation, ...] = Field(min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_unique_entries(self):
        for items in (
            [product.modality.casefold() for product in self.configured_products],
            [product.part_number.casefold() for product in self.configured_products],
            [source.path.casefold() for source in self.source_file_reconciliation],
        ):
            if len(items) != len(set(items)):
                raise ValueError("Product identities and reconciled source paths must be unique.")
        return self


def _read_bounded(path: Path, maximum_bytes: int) -> bytes:
    try:
        if not path.is_file():
            raise AuthoritativeFlexPolicyError("A controlled input must be a regular file.")
        with path.open("rb") as stream:
            raw = stream.read(maximum_bytes + 1)
    except OSError as exc:
        raise AuthoritativeFlexPolicyError("A controlled input is unavailable.") from exc
    if not raw or len(raw) > maximum_bytes:
        raise AuthoritativeFlexPolicyError("A controlled input is empty or exceeds its size limit.")
    return raw


def _unique_fields(pairs):
    fields = {}
    for name, value in pairs:
        if name in fields:
            raise AuthoritativeFlexPolicyError("A controlled input contains a duplicate JSON field.")
        fields[name] = value
    return fields


def _reject_nonfinite(_value):
    raise AuthoritativeFlexPolicyError("A controlled input contains a nonfinite JSON value.")


def _parse_json(raw: bytes):
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_fields,
            parse_constant=_reject_nonfinite,
            parse_float=Decimal,
        )
    except AuthoritativeFlexPolicyError:
        raise
    except (ValueError, ArithmeticError, RecursionError) as exc:
        raise AuthoritativeFlexPolicyError("A controlled input is not valid UTF-8 JSON.") from exc


def load_authoritative_flex_policy(path: Path) -> AuthoritativeFlexPlanningPolicy:
    payload = _parse_json(_read_bounded(path, MAX_POLICY_BYTES))
    try:
        return AuthoritativeFlexPlanningPolicy.model_validate(payload)
    except ValidationError as exc:
        raise AuthoritativeFlexPolicyError("The saved policy does not match the overlay schema.") from exc


def _load_verified_configuration(
    policy: AuthoritativeFlexPlanningPolicy, project_root: Path
) -> PlanningConfiguration:
    root = project_root.resolve(strict=True)
    if not root.is_dir():
        raise AuthoritativeFlexPolicyError("The project root must be a directory.")
    configuration = None
    for source in policy.source_file_reconciliation:
        source_path = (root / source.path).resolve(strict=True)
        if not source_path.is_relative_to(root):
            raise AuthoritativeFlexPolicyError("A reconciled policy source escapes the project root.")
        raw = _read_bounded(source_path, MAX_SOURCE_BYTES)
        if sha256(raw).hexdigest() != source.sha256:
            raise AuthoritativeFlexPolicyError(
                "A reconciled policy source does not match its approved hash."
            )
        if source.path == DETAILED_CONFIGURATION_PATH:
            configuration = raw
    if configuration is None:
        raise AuthoritativeFlexPolicyError(
            "The detailed planning configuration is not governed by the policy."
        )
    try:
        return PlanningConfiguration.model_validate(_parse_json(configuration))
    except ValidationError as exc:
        raise AuthoritativeFlexPolicyError("The detailed planning configuration is invalid.") from exc


def project_detailed_planning_configuration(
    policy: AuthoritativeFlexPlanningPolicy,
    *,
    project_root: Path,
) -> PlanningConfiguration:
    """Overlay authoritative lot sizes/factor on hash-pinned planning detail."""

    legacy = _load_verified_configuration(policy, project_root)
    authority_by_modality = {item.modality: item for item in policy.configured_products}
    products = []
    for product in legacy.products:
        authority = authority_by_modality.get(product.modality)
        if authority is None or authority.part_number != product.part_number:
            raise AuthoritativeFlexPolicyError(
                "A detailed planning product is absent from the authority."
            )
        parameter_provenance = dict(product.parameter_provenance)
        parameter_provenance["uncovered_demand_start_factor"] = (
            parameter_provenance["uncovered_demand_start_factor"].model_copy(
                update={
                    "source": (
                        f"{policy.policy_id}@{policy.policy_revision} factor 1.00; "
                        "legacy 1.10 retained as comparison only"
                    )
                }
            )
        )
        products.append(
            product.model_copy(
                update={
                    "expected_lot_start_quantity": authority.lot_size,
                    "uncovered_demand_start_factor": Decimal(
                        policy.calculation_rules.recommendation_factor
                    ),
                    "parameter_provenance": parameter_provenance,
                }
            )
        )
    return PlanningConfiguration.model_validate(
        legacy.model_copy(
            update={
                "source_set": (
                    f"{legacy.source_set}; {policy.policy_id}@{policy.policy_revision} "
                    "shadow overlay"
                ),
                "products": tuple(products),
            }
        ).model_dump()
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("policy", type=Path, help="Saved policy in the overlay JSON format")
    parser.add_argument("--project-root", type=Path, required=True, help="Directory containing the pinned sources")
    args = parser.parse_args(argv)
    try:
        policy = load_authoritative_flex_policy(args.policy)
        result = project_detailed_planning_configuration(policy, project_root=args.project_root)
    except AuthoritativeFlexPolicyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValidationError:
        print("ERROR: The projected configuration is invalid.", file=sys.stderr)
        return 2
    except (OSError, RuntimeError):
        print("ERROR: A controlled input path could not be resolved.", file=sys.stderr)
        return 2
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
