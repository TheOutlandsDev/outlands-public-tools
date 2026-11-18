"""Determine open shipment demand from local planning records."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LEGACY_SOURCE_SHA256 = (
    "a91482e30764c491c232c43ddb1242b80682c9513d565df67a8cfe408dfb0af0"
)


class WhatIsNeededValidationError(ValueError):
    """Raised when the controlled demand-selection contract cannot be proven."""


def _canonical_part_number(value: Any) -> str:
    """Normalize Excel-style numeric identifiers without hiding malformed values."""

    if isinstance(value, bool):
        raise ValueError("part number cannot be boolean")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("numeric part number must be a whole number")
        return str(int(value))
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError("part number cannot be blank")
        return normalized
    raise ValueError("part number must be a string or whole number")


class ShipmentNeedInput(BaseModel):
    """One normalized shipment input row."""

    source_id: str = Field(min_length=1, max_length=100)
    date_to_ship: date
    quantity_due: int = Field(strict=True, ge=-1_000_000_000, le=1_000_000_000)
    ship_date: date | None = None
    ship_quantity: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        le=1_000_000_000,
    )
    part_number: str = Field(min_length=1, max_length=40)
    dock_date: date | None = None

    model_config = ConfigDict(frozen=True)

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source ID cannot be blank")
        return normalized

    @field_validator("part_number", mode="before")
    @classmethod
    def normalize_part_number(cls, value: Any) -> str:
        return _canonical_part_number(value)


class DueProductInput(BaseModel):
    """One normalized due-product input row."""

    source_id: str = Field(min_length=1, max_length=100)
    due_date: date
    part_number: str = Field(min_length=1, max_length=40)

    model_config = ConfigDict(frozen=True)

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source ID cannot be blank")
        return normalized

    @field_validator("part_number", mode="before")
    @classmethod
    def normalize_part_number(cls, value: Any) -> str:
        return _canonical_part_number(value)


class PartModalityConfiguration(BaseModel):
    """Version-controlled part-to-modality mapping."""

    configuration_id: str = Field(min_length=1, max_length=100)
    configuration_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    legacy_source_file: str = Field(pattern=r"^DEMO_SHIPMENT_NEEDS\.m$")
    legacy_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str = Field(pattern=r"^APPROVED_DEVELOPMENT_CONTRACT$")
    part_to_modality: dict[str, str] = Field(min_length=1, max_length=100)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_mapping(self) -> "PartModalityConfiguration":
        if self.legacy_source_sha256 != LEGACY_SOURCE_SHA256:
            raise ValueError("legacy source checksum does not match the contract")
        canonical: dict[str, str] = {}
        for raw_part, raw_modality in self.part_to_modality.items():
            part = _canonical_part_number(raw_part)
            modality = raw_modality.strip()
            if not modality:
                raise ValueError("modality cannot be blank")
            if part in canonical:
                raise ValueError("duplicate normalized part number mapping")
            canonical[part] = modality
        object.__setattr__(self, "part_to_modality", canonical)
        return self


class PartToShip(BaseModel):
    """One retained open shipment need."""

    source_id: str
    date_to_ship: date
    part_number: str
    modality: str
    quantity_due: int = Field(gt=0)

    model_config = ConfigDict(frozen=True)


class WhatIsNeededResult(BaseModel):
    """Auditable output of the deterministic demand-selection stage."""

    parts_to_ship: tuple[PartToShip, ...]
    active_products: tuple[str, ...]
    active_cutoff_date: date | None
    input_count: int = Field(ge=0)
    open_need_count: int = Field(ge=0)
    excluded_nonpositive_count: int = Field(ge=0)
    excluded_shipped_count: int = Field(ge=0)
    excluded_docked_count: int = Field(ge=0)
    retained_demand_quantity: int = Field(ge=0)
    mapping_configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    model_config = ConfigDict(frozen=True)


class EvaluatedWhatIsNeededCase(BaseModel):
    """Validated comparison metadata and deterministic result for display."""

    case_id: str
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: str
    matlab_execution_status: str
    review_status: str
    authority: str
    legacy_source_file: str
    legacy_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_configuration_id: str
    mapping_configuration_version: str
    result: WhatIsNeededResult

    model_config = ConfigDict(frozen=True)


def load_part_modality_configuration(path: Path) -> PartModalityConfiguration:
    """Load and validate the version-controlled mapping without fallback."""

    try:
        return PartModalityConfiguration.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise WhatIsNeededValidationError(
            "part-to-modality configuration is invalid"
        ) from exc


def _configuration_sha256(configuration: PartModalityConfiguration) -> str:
    canonical = json.dumps(
        configuration.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


def _require_unique_source_ids(records: tuple[BaseModel, ...], label: str) -> None:
    source_ids = [str(getattr(record, "source_id")) for record in records]
    if len(source_ids) != len(set(source_ids)):
        raise WhatIsNeededValidationError(f"duplicate {label} source ID")


def determine_parts_to_ship(
    *,
    shipment_records: tuple[ShipmentNeedInput, ...],
    due_products: tuple[DueProductInput, ...],
    mapping: PartModalityConfiguration,
) -> WhatIsNeededResult:
    """Apply shipment demand filtering with deterministic ordering and diagnostics."""

    _require_unique_source_ids(shipment_records, "shipment")
    _require_unique_source_ids(due_products, "due/product")

    retained: list[PartToShip] = []
    excluded_nonpositive = 0
    excluded_shipped = 0
    excluded_docked = 0

    for record in shipment_records:
        if record.quantity_due <= 0:
            excluded_nonpositive += 1
            continue
        if record.ship_quantity is not None:
            excluded_shipped += 1
            continue
        if record.dock_date is not None:
            excluded_docked += 1
            continue

        modality = mapping.part_to_modality.get(record.part_number)
        if modality is None:
            raise WhatIsNeededValidationError(
                f"unsupported retained part number: {record.part_number!r}"
            )
        retained.append(
            PartToShip(
                source_id=record.source_id,
                date_to_ship=record.date_to_ship,
                part_number=record.part_number,
                modality=modality,
                quantity_due=record.quantity_due,
            )
        )

    parts_to_ship = tuple(
        sorted(retained, key=lambda item: (item.date_to_ship, item.source_id))
    )
    cutoff = parts_to_ship[0].date_to_ship if parts_to_ship else None
    active_products = (
        tuple(
            sorted(
                {
                    item.part_number
                    for item in due_products
                    if cutoff is not None and item.due_date >= cutoff
                }
            )
        )
        if cutoff is not None
        else ()
    )

    return WhatIsNeededResult(
        parts_to_ship=parts_to_ship,
        active_products=active_products,
        active_cutoff_date=cutoff,
        input_count=len(shipment_records),
        open_need_count=len(parts_to_ship),
        excluded_nonpositive_count=excluded_nonpositive,
        excluded_shipped_count=excluded_shipped,
        excluded_docked_count=excluded_docked,
        retained_demand_quantity=sum(item.quantity_due for item in parts_to_ship),
        mapping_configuration_sha256=_configuration_sha256(mapping),
    )


def evaluate_comparison_case(
    *,
    case_path: Path,
    mapping_path: Path,
) -> EvaluatedWhatIsNeededCase:
    """Validate the frozen stage fixture and prove every expected result field."""

    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        mapping = load_part_modality_configuration(mapping_path)
        legacy_source = case["legacy_source"]
        acceptance = case["acceptance"]
        if case["status"] != "APPROVED_DEVELOPMENT_REFERENCE":
            raise WhatIsNeededValidationError("comparison case is not approved")
        if acceptance["review_status"] != "APPROVED_BY_OWNER":
            raise WhatIsNeededValidationError("owner review is not recorded")
        if legacy_source["file"] != mapping.legacy_source_file:
            raise WhatIsNeededValidationError("legacy source filename does not match")
        if legacy_source["sha256"].lower() != mapping.legacy_source_sha256:
            raise WhatIsNeededValidationError("legacy source checksum does not match")

        fixture_mapping = {
            _canonical_part_number(part): modality
            for part, modality in case["input_contract"]["part_to_modality"].items()
        }
        if any(
            mapping.part_to_modality.get(part) != modality
            for part, modality in fixture_mapping.items()
        ):
            raise WhatIsNeededValidationError("fixture mapping does not match configuration")

        shipment_records = tuple(
            ShipmentNeedInput.model_validate(record)
            for record in case["input_contract"]["shipment_records"]
        )
        due_products = tuple(
            DueProductInput.model_validate(record)
            for record in case["input_contract"]["due_products"]
        )
        result = determine_parts_to_ship(
            shipment_records=shipment_records,
            due_products=due_products,
            mapping=mapping,
        )
        expected = case["expected"]
        actual = result.model_dump(mode="json")
        actual.pop("mapping_configuration_sha256")
        if actual != expected:
            raise WhatIsNeededValidationError(
                "controlled expected result does not match calculation"
            )
        return EvaluatedWhatIsNeededCase(
            case_id=case["case_id"],
            fixture_sha256=sha256(case_path.read_bytes()).hexdigest(),
            status=case["status"],
            matlab_execution_status=case["matlab_execution_status"],
            review_status=acceptance["review_status"],
            authority=acceptance["authority"],
            legacy_source_file=legacy_source["file"],
            legacy_source_sha256=legacy_source["sha256"].lower(),
            mapping_configuration_id=mapping.configuration_id,
            mapping_configuration_version=mapping.configuration_version,
            result=result,
        )
    except WhatIsNeededValidationError:
        raise
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise WhatIsNeededValidationError("comparison case validation failed") from exc
