"""Verify a saved development program authority index and its evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import stat
import sys
from typing import Any


INDEX_RELATIVE_PATH = Path("authority-index.json")
MAX_INDEX_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
SOURCE_PATHS = {
    "planning-authority": Path("reports/planning.json"),
    "configuration-coverage": Path("reports/configuration-coverage.json"),
    "business-input-register": Path("reports/business-input.csv"),
    "fixture-coverage": Path("reports/fixture-coverage.json"),
    "functional-parity-matrix": Path("reports/functional-parity.md"),
    "platform-module-registry": Path("reports/platform.json"),
    "database-migration-registry": Path("reports/migrations.json"),
    "system-logic": Path("reports/system-logic.json"),
}
REPORT_FIELDS = {
    "planning-authority": (
        ("artifact_count", int), ("recommendation_factor", str),
        ("legacy_comparison_factor", str), ("active", bool),
    ),
    "configuration-coverage": (
        ("integrity_status", str), ("gate_status", str), ("retained_products", int),
        ("configured_products", int), ("detailed_products", int),
        ("timing_review_pending_products", int), ("fail_closed_products", int),
    ),
    "fixture-coverage": (
        ("integrity_status", str), ("gate_status", str), ("authoritative_expected_value_fixtures", int),
        ("legacy_comparison_fixtures", int), ("required_scenarios", int),
        ("reusable_scenarios", int), ("partial_scenarios", int),
    ),
    "platform-module-registry": (("current_routes", int), ("planned_routes", int)),
    "database-migration-registry": (
        ("total", int), ("postgresql", int), ("clickhouse", int), ("live_execution_authorized", bool),
    ),
}
FINGERPRINT_KEYS = {
    "planning-authority": "planning_fingerprint",
    "configuration-coverage": "gate_b_fingerprint",
    "fixture-coverage": "gate_c_fingerprint",
    "database-migration-registry": "migration_fingerprint",
}
HEX_DIGEST = re.compile(r"[a-f0-9]{64}")


SAFE_STATUS = "DEVELOPMENT_AUTHORITY_INTEGRITY_PASS_BUSINESS_GATES_BLOCKED"
PARITY_ROW = re.compile(r"^\|\s*(IN|CALC|VIEW|AUTO|CTRL)-\d+\s*\|")


class ProgramAuthorityError(ValueError):
    """Raised when consolidated development authority cannot be proven."""


@dataclass(frozen=True)
class ProgramAuthorityIndex:
    contract_id: str
    contract_version: str
    status: str
    source_sha256: dict[str, str]
    source_fingerprint: str
    observed_state: dict[str, Any]
    authority_fingerprint: str


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _is_reparse(info: Any) -> bool:
    return bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _read_bounded(root: Path, relative_path: Path, limit: int) -> bytes:
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ProgramAuthorityError("A program authority path is outside the project root.")
    parent = root
    try:
        for part in relative_path.parts[:-1]:
            parent /= part
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or _is_reparse(info):
                raise ProgramAuthorityError("Program authority paths must use ordinary directories.")
        path = parent / relative_path.name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or _is_reparse(info):
            raise ProgramAuthorityError("A program authority source must be an ordinary file.")
        if not path.resolve().is_relative_to(root):
            raise ProgramAuthorityError("A program authority path escaped the project root.")
        with path.open("rb") as stream:
            content = stream.read(limit + 1)
    except OSError as exc:
        raise ProgramAuthorityError("A program authority source is unavailable.") from exc
    if not 0 < len(content) <= limit:
        raise ProgramAuthorityError("A program authority source is empty or oversized.")
    return content


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ProgramAuthorityError("A program authority JSON source has duplicate keys.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise ProgramAuthorityError("A program authority JSON source has a non-finite value.")


def _load_json(content: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        _canonical_json(payload)
    except (ValueError, RecursionError) as exc:
        raise ProgramAuthorityError("A program authority JSON source is invalid.") from exc
    if not isinstance(payload, dict):
        raise ProgramAuthorityError("A program authority JSON source must be an object.")
    return payload


def _saved_report(content: bytes, source_id: str) -> tuple[dict[str, Any], str | None]:
    report = _load_json(content)
    fields = REPORT_FIELDS[source_id]
    expected = {key for key, _ in fields}
    if source_id in FINGERPRINT_KEYS:
        expected.add("fingerprint")
    if set(report) != expected:
        raise ProgramAuthorityError(f"A saved report has invalid fields: {source_id}.")
    fingerprint = report.pop("fingerprint", None)
    if source_id in FINGERPRINT_KEYS and (
        not isinstance(fingerprint, str) or not HEX_DIGEST.fullmatch(fingerprint)
    ):
        raise ProgramAuthorityError(f"A saved report has an invalid fingerprint: {source_id}.")
    for key, expected_type in fields:
        value = report[key]
        if (type(value) is not expected_type
                or expected_type is int and value < 0
                or expected_type is str and not value.strip()):
            raise ProgramAuthorityError(f"A saved report has invalid values: {source_id}.")
    return report, fingerprint


def _parse_parity_matrix(content: str) -> dict[str, Any]:
    categories: Counter[str] = Counter()
    classifications: Counter[str] = Counter()
    for line in content.splitlines():
        match = PARITY_ROW.match(line)
        if match is None:
            continue
        columns = [column.strip().replace("**", "") for column in line.split("|")]
        if len(columns) < 7:
            raise ProgramAuthorityError("A functional-parity row is malformed.")
        categories[match.group(1)] += 1
        classifications[columns[5]] += 1
    if not categories:
        raise ProgramAuthorityError("The functional-parity matrix has no capability rows.")
    return {
        "capability_count": sum(categories.values()),
        "categories": dict(categories),
        "classifications": dict(classifications),
    }


def validate_program_authority_expectations(
    payload: dict[str, Any], observed_state: dict[str, Any]
) -> None:
    """Pure fail-closed validator used by the loader and tamper tests."""

    required = {
        "contract_id",
        "contract_version",
        "status",
        "technical_owner",
        "scope",
        "production_authority",
        "activation_authorized",
        "database_reads",
        "database_writes",
        "calculations_executed",
        "plans_generated",
        "sources",
        "expected_state",
        "blockers",
        "allowed_next_action",
    }
    if set(payload) != required:
        raise ProgramAuthorityError("The program authority index is incomplete.")
    if any(not isinstance(payload[key], str) or not payload[key].strip()
           for key in ("contract_id", "contract_version", "technical_owner")):
        raise ProgramAuthorityError("The program identity is invalid.")
    if payload["status"] != SAFE_STATUS or payload["scope"] != "DEVELOPMENT_ONLY_SOURCE_AUTHORITY":
        raise ProgramAuthorityError("The program authority index has an unsafe status or scope.")
    safe_values = (
        payload["production_authority"] is False,
        payload["activation_authorized"] is False,
        payload["database_reads"] is False,
        payload["database_writes"] is False,
        type(payload["calculations_executed"]) is int and payload["calculations_executed"] == 0,
        type(payload["plans_generated"]) is int and payload["plans_generated"] == 0,
    )
    if not all(safe_values):
        raise ProgramAuthorityError("The program authority index unexpectedly authorizes runtime work.")
    blockers = payload["blockers"]
    if not isinstance(blockers, list) or len(blockers) < 3 or not all(
        isinstance(blocker, str) and blocker.strip() for blocker in blockers
    ):
        raise ProgramAuthorityError("The program authority blockers are incomplete.")
    if payload["allowed_next_action"] != "REVIEWED_INCREMENTAL_BUSINESS_AUTHORITY_ONLY":
        raise ProgramAuthorityError("The program authority next action is unsafe.")
    if _canonical_json(payload["expected_state"]) != _canonical_json(observed_state):
        raise ProgramAuthorityError("The consolidated program authority state drifted.")


def load_program_authority(*, project_root: Path) -> ProgramAuthorityIndex:
    """Collect pinned saved reports and compare their state without executing the program."""
    root = project_root.resolve()
    payload = _load_json(_read_bounded(root, INDEX_RELATIVE_PATH, MAX_INDEX_BYTES))
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or len(raw_sources) != len(SOURCE_PATHS):
        raise ProgramAuthorityError("The program authority source catalog is incomplete.")
    source_sha256: dict[str, str] = {}
    sources: dict[str, bytes] = {}
    for raw in raw_sources:
        if not isinstance(raw, dict) or set(raw) != {"source_id", "path", "role", "sha256"}:
            raise ProgramAuthorityError("A program authority source entry is invalid.")
        source_id = raw["source_id"]
        if not isinstance(source_id, str) or source_id not in SOURCE_PATHS or source_id in source_sha256:
            raise ProgramAuthorityError("A program authority source identifier is invalid or duplicated.")
        if raw["path"] != SOURCE_PATHS[source_id].as_posix():
            raise ProgramAuthorityError("A program authority source path drifted.")
        if not isinstance(raw["role"], str) or not raw["role"].strip():
            raise ProgramAuthorityError("A program authority source role is missing.")
        source = _read_bounded(root, SOURCE_PATHS[source_id], MAX_SOURCE_BYTES)
        digest = sha256(source).hexdigest()
        if raw["sha256"] != digest:
            raise ProgramAuthorityError(f"Program authority source hash drifted: {source_id}")
        sources[source_id] = source
        source_sha256[source_id] = digest
    if set(source_sha256) != set(SOURCE_PATHS):
        raise ProgramAuthorityError("The program authority source catalog is incomplete.")

    try:
        parity = _parse_parity_matrix(sources["functional-parity-matrix"].decode("utf-8"))
    except UnicodeError as exc:
        raise ProgramAuthorityError("The functional-parity matrix is not UTF-8.") from exc
    reports = {}
    fingerprints = {}
    for source_id, state_name in (
        ("planning-authority", "planning_authority"),
        ("configuration-coverage", "gate_b"),
        ("fixture-coverage", "gate_c"),
        ("platform-module-registry", "platform"),
        ("database-migration-registry", "migrations"),
    ):
        reports[state_name], fingerprint = _saved_report(sources[source_id], source_id)
        if fingerprint is not None:
            fingerprints[FINGERPRINT_KEYS[source_id]] = fingerprint
    if reports["migrations"]["live_execution_authorized"]:
        raise ProgramAuthorityError("The migration evidence unexpectedly authorizes runtime work.")
    observed_state = {**reports, "functional_parity": parity}
    validate_program_authority_expectations(payload, observed_state)

    source_fingerprint = sha256(_canonical_json(source_sha256)).hexdigest()
    authority_fingerprint = sha256(_canonical_json({
        "source_fingerprint": source_fingerprint,
        **fingerprints,
        "observed_state": observed_state,
    })).hexdigest()
    return ProgramAuthorityIndex(
        contract_id=payload["contract_id"],
        contract_version=payload["contract_version"],
        status=payload["status"],
        source_sha256=source_sha256,
        source_fingerprint=source_fingerprint,
        observed_state=observed_state,
        authority_fingerprint=authority_fingerprint,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory containing authority-index.json and reports")
    args = parser.parse_args()
    try:
        report = load_program_authority(project_root=args.root)
    except ProgramAuthorityError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError):
        print("The authority index could not be read.", file=sys.stderr)
        return 2
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
