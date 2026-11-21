"""Validate a saved raw-material source definition that is pending approval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class RawMaterialContractError(ValueError):
    """Raised when the source definition is absent, altered, or prematurely enabled."""


class RawMaterialContract(BaseModel):
    schema_version: Literal["0.1.0"]
    contract_id: Literal["fictional-raw-material-source"]
    status: Literal["PENDING_AUTHORITATIVE_SOURCE"]
    scope: Literal["INTERNAL_PANEL_FLEX_RAW_MATERIAL"]
    authoritative_owner: Literal["PENDING_SITE_DECISION"]
    authoritative_system: Literal["PENDING_SITE_DECISION"]
    ingestion_enabled: Literal[False]
    database_writes: Literal[False]
    development_behavior: Literal["FAIL_CLOSED_NO_DATA"]
    allowed_source_interfaces: tuple[
        Literal[
            "CONTROLLED_XLSX_SNAPSHOT",
            "CONTROLLED_CSV_SNAPSHOT",
            "MES_READ_ONLY_QUERY",
        ],
        ...,
    ] = Field(min_length=3, max_length=3)
    required_fields: tuple[str, ...] = Field(min_length=7, max_length=20)
    optional_fields: tuple[str, ...] = Field(max_length=20)
    acceptance_requirements: tuple[str, ...] = Field(min_length=6, max_length=20)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_fail_closed_contract(self) -> "RawMaterialContract":
        if len(set(self.required_fields)) != len(self.required_fields):
            raise ValueError("Raw-material required fields must be unique.")
        if set(self.required_fields) & set(self.optional_fields):
            raise ValueError("Raw-material required and optional fields overlap.")
        return self

def load_raw_material_source_contract(path: Path) -> RawMaterialContract:
    """Load a saved JSON contract from an explicit path."""
    try:
        return RawMaterialContract.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        raise RawMaterialContractError("Raw-material source contract is invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path, help="Saved JSON contract")
    args = parser.parse_args()

    try:
        load_raw_material_source_contract(args.contract)
    except RawMaterialContractError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("PASS: raw-material source contract is pending approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
