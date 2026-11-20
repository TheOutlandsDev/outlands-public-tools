"""Verify legacy and candidate policy identities for saved order states."""

from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


MAX_INPUT_BYTES = 2 * 1024 * 1024


class AuthoritativeFlexCutoverError(ValueError):
    """A saved order identity cannot be verified."""


class IdentityNamespaces(BaseModel):
    """The two namespace values used to derive event fingerprints."""

    legacy_contract_version: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    candidate_policy_revision: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

    model_config = ConfigDict(frozen=True, extra="forbid")


class OSOrderState(BaseModel):
    """Canonical O&S demand state consumed by the automatic calculation."""

    order_id: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    row_version: int = Field(gt=0)
    source_revision_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    part_number: str = Field(min_length=1, max_length=40)
    ordered_quantity: int = Field(gt=0, le=10_000_000)
    accepted_ship_quantity: int = Field(ge=0, le=10_000_000)
    requested_ship_date: date
    cancelled: bool = False

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_quantity_conservation(self):
        if self.accepted_ship_quantity > self.ordered_quantity:
            raise ValueError("Accepted ship quantity cannot exceed ordered quantity.")
        return self

    @property
    def remaining_quantity(self) -> int:
        if self.cancelled:
            return 0
        return self.ordered_quantity - self.accepted_ship_quantity

    def fingerprint(self, contract_version: str) -> str:
        payload = {
            "contract_version": contract_version,
            **self.model_dump(mode="json"),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(canonical.encode("utf-8")).hexdigest()


class LegacyOrderIdentityRecord(BaseModel):
    legacy_event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    order: OSOrderState

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityAlias(BaseModel):
    order_id: str
    row_version: int = Field(gt=0)
    legacy_event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    mapping_status: Literal["VERIFIED_COMPATIBLE"] = "VERIFIED_COMPATIBLE"

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityMappingGateResult(BaseModel):
    status: Literal["PASS"]
    mapped_records: int = Field(ge=0)
    distinct_legacy_identities: int = Field(ge=0)
    distinct_candidate_identities: int = Field(ge=0)
    distinct_semantic_identities: int = Field(ge=0)
    collisions: Literal[0]
    conflicting_order_versions: Literal[0]
    database_writes: Literal[False] = False
    schema_migration_applied: Literal[False] = False
    runtime_readers_changed: Literal[False] = False
    policy_activated: Literal[False] = False
    production_changed: Literal[False] = False

    model_config = ConfigDict(frozen=True, extra="forbid")


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def semantic_fingerprint(order: OSOrderState) -> str:
    return sha256(_canonical(order.model_dump(mode="json"))).hexdigest()


def candidate_fingerprint(order: OSOrderState, policy_revision: str) -> str:
    return sha256(
        _canonical({"policy_revision": policy_revision, **order.model_dump(mode="json")})
    ).hexdigest()


def map_legacy_identity(
    record: LegacyOrderIdentityRecord,
    contract: IdentityNamespaces,
) -> IdentityAlias:
    recomputed = record.order.fingerprint(contract.legacy_contract_version)
    if recomputed != record.legacy_event_fingerprint:
        raise AuthoritativeFlexCutoverError(
            "A stored legacy fingerprint does not match its canonical order state."
        )
    candidate = candidate_fingerprint(
        record.order, contract.candidate_policy_revision
    )
    if candidate == record.legacy_event_fingerprint:
        raise AuthoritativeFlexCutoverError(
            "The candidate and legacy namespaces unexpectedly produced one identity."
        )
    return IdentityAlias(
        order_id=record.order.order_id,
        row_version=record.order.row_version,
        legacy_event_fingerprint=record.legacy_event_fingerprint,
        candidate_event_fingerprint=candidate,
        semantic_fingerprint=semantic_fingerprint(record.order),
    )


def _map_and_validate(
    records: tuple[LegacyOrderIdentityRecord, ...],
    contract: IdentityNamespaces,
) -> tuple[IdentityMappingGateResult, tuple[IdentityAlias, ...]]:
    aliases = tuple(map_legacy_identity(record, contract) for record in records)
    legacy = {alias.legacy_event_fingerprint for alias in aliases}
    candidate = {alias.candidate_event_fingerprint for alias in aliases}
    semantic = {alias.semantic_fingerprint for alias in aliases}
    order_versions: dict[tuple[str, int], str] = {}
    for alias in aliases:
        key = (alias.order_id, alias.row_version)
        prior = order_versions.setdefault(key, alias.semantic_fingerprint)
        if prior != alias.semantic_fingerprint:
            raise AuthoritativeFlexCutoverError(
                "One O&S order version represents conflicting canonical states."
            )
    expected = len(aliases)
    if len(legacy) != expected or len(candidate) != expected or len(semantic) != expected:
        raise AuthoritativeFlexCutoverError(
            "The A3 identity mapping contains a collision or duplicate alias."
        )
    report = IdentityMappingGateResult(
        status="PASS",
        mapped_records=expected,
        distinct_legacy_identities=len(legacy),
        distinct_candidate_identities=len(candidate),
        distinct_semantic_identities=len(semantic),
        collisions=0,
        conflicting_order_versions=0,
    )
    return report, aliases


def run_identity_mapping_gate(
    records: tuple[LegacyOrderIdentityRecord, ...],
    contract: IdentityNamespaces,
) -> IdentityMappingGateResult:
    report, _ = _map_and_validate(records, contract)
    return report


class SavedIdentityBatch(BaseModel):
    namespaces: IdentityNamespaces
    records: tuple[LegacyOrderIdentityRecord, ...] = Field(min_length=1, max_length=1000)

    model_config = ConfigDict(frozen=True, extra="forbid")


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise AuthoritativeFlexCutoverError("The saved JSON has duplicate fields.")
    return result


def _invalid_constant(_value: str) -> None:
    raise AuthoritativeFlexCutoverError("The saved JSON has a non-finite number.")


def load_saved_batch(path: Path) -> SavedIdentityBatch:
    try:
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise AuthoritativeFlexCutoverError("The saved order batch must be an ordinary file.")
        with path.open("rb") as stream:
            content = stream.read(MAX_INPUT_BYTES + 1)
    except OSError as exc:
        raise AuthoritativeFlexCutoverError("The saved order batch is unavailable.") from exc
    if not 0 < len(content) <= MAX_INPUT_BYTES:
        raise AuthoritativeFlexCutoverError("The saved order batch is empty or exceeds its size limit.")
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        return SavedIdentityBatch.model_validate(payload)
    except AuthoritativeFlexCutoverError:
        raise
    except (ValueError, RecursionError) as exc:
        raise AuthoritativeFlexCutoverError("The saved order batch schema is invalid.") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Saved JSON batch with namespaces and order states")
    parser.add_argument("--include-aliases", action="store_true", help="Include each verified alias in the report")
    args = parser.parse_args()
    try:
        saved = load_saved_batch(args.input)
        report, aliases = _map_and_validate(saved.records, saved.namespaces)
    except AuthoritativeFlexCutoverError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    output = report.model_dump(mode="json")
    if args.include_aliases:
        output["aliases"] = [alias.model_dump(mode="json") for alias in aliases]
    print(json.dumps(output, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
