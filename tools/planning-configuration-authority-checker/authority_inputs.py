"""Read strict, bounded development policy and authority evidence."""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import stat
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationError, model_validator


MAX_SOURCE_BYTES = 2 * 1024 * 1024
PartNumber = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Z0-9][A-Z0-9._/-]*$")]


class PTLAGateBError(ValueError):
    """A controlled configuration source could not be verified."""


class InputModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PartIdentity(InputModel):
    part_number: PartNumber
    modality: str = Field(min_length=3, max_length=12)


class AuthoritativeFlexPlanningPolicy(InputModel):
    policy_id: str = Field(min_length=1, max_length=80)
    policy_revision: str = Field(min_length=1, max_length=40)
    configured_products: tuple[PartIdentity, ...] = Field(max_length=500)
    fail_closed_products: tuple[PartIdentity, ...] = Field(max_length=500)

    @model_validator(mode="after")
    def validate_identities(self) -> "AuthoritativeFlexPlanningPolicy":
        identities = self.configured_products + self.fail_closed_products
        if not identities or len({item.part_number for item in identities}) != len(identities):
            raise ValueError("each policy part must have exactly one authority state")
        return self


class DetailedProduct(PartIdentity):
    expected_lot_start_quantity: int = Field(strict=True, gt=0, le=10_000)
    flow_name: str = Field(min_length=1, max_length=256)
    route_version: int = Field(strict=True, gt=0)
    operation_to_kanban: dict[str, Annotated[int, Field(strict=True, ge=1, le=7)]] = Field(min_length=1, max_length=500)
    kanban_days_remaining: dict[int, Annotated[int, Field(strict=True, ge=0)]]
    timing_exceptions: tuple[dict, ...] = Field(max_length=100)
    uncovered_demand_start_factor: Decimal = Field(ge=Decimal("1"), le=Decimal("2"))

    @model_validator(mode="after")
    def validate_kanban_days(self) -> "DetailedProduct":
        if set(self.kanban_days_remaining) != set(range(1, 8)):
            raise ValueError("detailed configuration must define K1 through K7")
        return self


class PlanningConfiguration(InputModel):
    products: tuple[DetailedProduct, ...] = Field(max_length=500)

    @model_validator(mode="after")
    def validate_identities(self) -> "PlanningConfiguration":
        if len({item.part_number for item in self.products}) != len(self.products):
            raise ValueError("detailed part numbers must be unique")
        return self


class PartModalityConfiguration(InputModel):
    part_to_modality: dict[PartNumber, Annotated[str, Field(min_length=3, max_length=12)]] = Field(max_length=500)


AuthorityStatus = Literal[
    "APPROVED_DEVELOPMENT_BASELINE",
    "USER_CONFIRMED",
    "LEGACY_REFERENCE_ONLY",
    "NOT_PROVIDED",
]


class ProductReviewRecord(BaseModel):
    status: Literal[
        "APPROVED_DEVELOPMENT_BASELINE",
        "SUBMITTED_FOR_BUSINESS_REVIEW",
        "NOT_PROVIDED",
    ]
    reviewer: str | None = Field(default=None, max_length=160)
    reviewed_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence_reference: str | None = Field(default=None, max_length=300)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_evidence(self) -> "ProductReviewRecord":
        populated = (
            self.reviewer,
            self.reviewed_on,
            self.evidence_reference,
        )
        if self.status == "APPROVED_DEVELOPMENT_BASELINE" and not all(populated):
            raise ValueError("approved product review requires complete evidence")
        if self.status == "NOT_PROVIDED" and any(populated):
            raise ValueError("unreviewed product cannot carry approval evidence")
        return self


class TechnicalValidationRecord(BaseModel):
    status: Literal["PASS", "NOT_VALIDATED"]
    validator: str | None = Field(default=None, max_length=160)
    validated_on: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    evidence_reference: str | None = Field(default=None, max_length=300)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_evidence(self) -> "TechnicalValidationRecord":
        populated = (
            self.validator,
            self.validated_on,
            self.evidence_reference,
        )
        if self.status == "PASS" and not all(populated):
            raise ValueError("technical PASS requires complete evidence")
        if self.status == "NOT_VALIDATED" and any(populated):
            raise ValueError("unvalidated product cannot carry validation evidence")
        return self


class ProductAuthorityEntry(BaseModel):
    modality: str = Field(min_length=3, max_length=12)
    canonical_part_number: PartNumber
    product_name: str | None = Field(default=None, max_length=160)
    accepted_part_aliases: tuple[str, ...] = ()
    demand_authority: str = Field(min_length=1, max_length=100)
    lot_prefix: str | None = Field(default=None, max_length=20)
    lot_size_circuits: int | None = Field(default=None, strict=True, gt=0, le=10_000)
    legacy_reference_lot_size_circuits: int | None = Field(
        default=None, strict=True, gt=0, le=10_000
    )
    lot_size_authority: AuthorityStatus
    flow_name: str | None = Field(default=None, max_length=256)
    route_version: int | None = Field(default=None, gt=0)
    route_authority: AuthorityStatus
    operation_to_kanban_count: int | None = Field(default=None, ge=1, le=500)
    operation_to_kanban_authority: AuthorityStatus
    kanban_days_remaining: dict[int, int] | None = None
    lead_time_days: int | None = Field(default=None, gt=0, le=365)
    legacy_reference_lead_time_days: int | None = Field(
        default=None, gt=0, le=365
    )
    timing_authority: AuthorityStatus
    timing_exception_count: int | None = Field(default=None, ge=0, le=100)
    coverage_state: Literal[
        "DETAILED_CONFIGURATION",
        "TIMING_REVIEW_PENDING",
        "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED",
    ]
    coverage_reason: str = Field(min_length=10, max_length=500)
    business_review: ProductReviewRecord
    technical_validation: TechnicalValidationRecord

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_coverage_state(self) -> "ProductAuthorityEntry":
        if len(self.accepted_part_aliases) != len(set(self.accepted_part_aliases)):
            raise ValueError("accepted part aliases must be unique")
        if self.canonical_part_number in self.accepted_part_aliases:
            raise ValueError("the canonical part number is not an alias")

        if self.coverage_state == "DETAILED_CONFIGURATION":
            required = (
                self.lot_prefix,
                self.lot_size_circuits,
                self.flow_name,
                self.route_version,
                self.operation_to_kanban_count,
                self.kanban_days_remaining,
                self.lead_time_days,
                self.timing_exception_count,
            )
            if not all(value is not None for value in required):
                raise ValueError("detailed configuration is missing a required value")
            if set(self.kanban_days_remaining or {}) != set(range(1, 8)):
                raise ValueError("detailed configuration must define K1 through K7")
            approved_statuses = {
                "APPROVED_DEVELOPMENT_BASELINE",
                "USER_CONFIRMED",
            }
            if self.lot_size_authority not in approved_statuses:
                raise ValueError("detailed lot size is not approved")
            if self.route_authority != "APPROVED_DEVELOPMENT_BASELINE":
                raise ValueError("detailed route is not approved")
            if self.operation_to_kanban_authority != "APPROVED_DEVELOPMENT_BASELINE":
                raise ValueError("detailed operation map is not approved")
            if self.timing_authority != "APPROVED_DEVELOPMENT_BASELINE":
                raise ValueError("detailed timing is not approved")
            if self.business_review.status != "APPROVED_DEVELOPMENT_BASELINE":
                raise ValueError("detailed product lacks business review")
            if self.technical_validation.status != "PASS":
                raise ValueError("detailed product lacks technical validation")

        elif self.coverage_state == "TIMING_REVIEW_PENDING":
            if self.lot_prefix is None or self.lot_size_circuits is None:
                raise ValueError("timing-pending product requires identity and lot size")
            if self.lot_size_authority not in {
                "APPROVED_DEVELOPMENT_BASELINE",
                "USER_CONFIRMED",
            }:
                raise ValueError("timing-pending product lot size is not controlled")
            if any(
                value is not None
                for value in (
                    self.flow_name,
                    self.route_version,
                    self.operation_to_kanban_count,
                    self.kanban_days_remaining,
                    self.lead_time_days,
                    self.timing_exception_count,
                )
            ):
                raise ValueError("pending route or timing values cannot be executable")
            if self.route_authority != "NOT_PROVIDED":
                raise ValueError("pending route must remain not provided")
            if self.operation_to_kanban_authority != "NOT_PROVIDED":
                raise ValueError("pending operation map must remain not provided")
            if self.timing_authority not in {
                "LEGACY_REFERENCE_ONLY",
                "NOT_PROVIDED",
            }:
                raise ValueError("pending timing cannot be executable")

        else:
            if any(
                value is not None
                for value in (
                    self.lot_size_circuits,
                    self.flow_name,
                    self.route_version,
                    self.operation_to_kanban_count,
                    self.kanban_days_remaining,
                    self.lead_time_days,
                    self.timing_exception_count,
                )
            ):
                raise ValueError("fail-closed product contains an executable value")
            if self.lot_size_authority not in {
                "LEGACY_REFERENCE_ONLY",
                "NOT_PROVIDED",
            }:
                raise ValueError("fail-closed lot size cannot be executable")
            if self.route_authority != "NOT_PROVIDED":
                raise ValueError("fail-closed route cannot be executable")
            if self.operation_to_kanban_authority != "NOT_PROVIDED":
                raise ValueError("fail-closed operation map cannot be executable")
            if self.timing_authority != "NOT_PROVIDED":
                raise ValueError("fail-closed timing cannot be executable")
        return self


class MatrixSource(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    role: str = Field(min_length=1, max_length=240)

    model_config = ConfigDict(frozen=True, extra="forbid")


class PTLAProductAuthorityMatrix(BaseModel):
    matrix_id: str = Field(min_length=1, max_length=80)
    matrix_revision: str = Field(min_length=1, max_length=40)
    status: Literal[
        "DEVELOPMENT_AUTHORITY_MATRIX_PARTIAL",
        "DEVELOPMENT_AUTHORITY_MATRIX_COMPLETE",
    ]
    prepared_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    technical_owner: str = Field(min_length=1, max_length=160)
    production_authority: StrictBool
    recommendation_factor: Literal["1.00"]
    legacy_comparison_factor: Literal["1.10"]
    legacy_comparison_factor_status: Literal["COMPARISON_ONLY_NOT_EXECUTABLE"]
    early_wip_loss_rate: Literal["0.20"]
    early_wip_loss_authority: Literal["LEGACY_REFERENCE_ONLY_GATE_C_PENDING"]
    products: tuple[ProductAuthorityEntry, ...] = Field(min_length=1, max_length=500)
    sources: tuple[MatrixSource, ...] = Field(min_length=1, max_length=64)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_matrix(self) -> "PTLAProductAuthorityMatrix":
        if self.production_authority:
            raise ValueError("the authority matrix must be development-only")
        modalities = [item.modality for item in self.products]
        parts = [item.canonical_part_number for item in self.products]
        if len(modalities) != len(set(modalities)):
            raise ValueError("product modalities must be unique")
        if len(parts) != len(set(parts)):
            raise ValueError("canonical part numbers must be unique")
        aliases = [alias for item in self.products for alias in item.accepted_part_aliases]
        if len(aliases) != len(set(aliases)):
            raise ValueError("accepted aliases must be globally unique")
        if set(parts) & set(aliases):
            raise ValueError("an alias conflicts with a canonical part number")
        source_paths = [source.path for source in self.sources]
        if len(source_paths) != len(set(source_paths)):
            raise ValueError("matrix source paths must be unique")
        return self


def _ordinary(info: Any) -> bool:
    return not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT


def read_source(path: Path) -> bytes:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or not _ordinary(info):
            raise PTLAGateBError("A controlled configuration source must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_SOURCE_BYTES + 1)
    except OSError as exc:
        raise PTLAGateBError("A controlled configuration source is unavailable.") from exc
    if not 0 < len(content) <= MAX_SOURCE_BYTES:
        raise PTLAGateBError("A controlled configuration source is empty or oversized.")
    return content


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise PTLAGateBError("A controlled configuration JSON source has duplicate fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise PTLAGateBError("A controlled configuration JSON source has a non-finite value.")


def load_source[Model: BaseModel](path: Path, model: type[Model]) -> tuple[Model, str]:
    content = read_source(path)
    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                           parse_constant=_invalid_constant)
        return model.model_validate(value), sha256(content).hexdigest()
    except (ValidationError, ValueError, RecursionError) as exc:
        raise PTLAGateBError(f"A controlled configuration is invalid: {model.__name__}.") from exc


def validate_matrix_source_hashes(matrix: PTLAProductAuthorityMatrix, root: Path) -> None:
    root = root.resolve()
    for source in matrix.sources:
        name = PurePosixPath(source.path)
        if (name.is_absolute() or name.as_posix() != source.path or ".." in name.parts
                or any(character in source.path for character in "\\\x00:")
                or not name.name):
            raise PTLAGateBError("A product authority source must be relative to the supplied root.")
        parent = root
        try:
            for part in name.parts[:-1]:
                parent /= part
                info = parent.lstat()
                if not stat.S_ISDIR(info.st_mode) or not _ordinary(info):
                    raise PTLAGateBError("Product authority sources must use ordinary directories.")
        except OSError as exc:
            raise PTLAGateBError("A product authority source is unavailable.") from exc
        path = parent / name.name
        if not path.resolve().is_relative_to(root):
            raise PTLAGateBError("A product authority source escaped the supplied root.")
        if sha256(read_source(path)).hexdigest() != source.sha256:
            raise PTLAGateBError("A product authority source checksum does not match.")
