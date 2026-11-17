"""Static MES query-contract validation and runtime safety defaults.

This module does not connect to MES or execute SQL.  It is a fail-closed
preflight gate for project-owned query files and their review metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from program_data.config import PROJECT_ROOT

POLICY_VERSION = "1.0"
MES_DATABASE_NAME = "DemoManufacturing"
DEFAULT_READ_ONLY_PROFILE = "DEMO_READ_ONLY_REPORTING"

HARD_FAILURE_THRESHOLD_SECONDS = 300
DEFAULT_CONNECTION_TIMEOUT_SECONDS = 30
DEFAULT_QUERY_TIMEOUT_SECONDS = 300
DEFAULT_TOTAL_REFRESH_DEADLINE_SECONDS = 300
DEFAULT_WARNING_THRESHOLD_SECONDS = 240
DEFAULT_PER_QUERY_RETRY = 0

ALLOWED_SCOPE_TYPES = frozenset(
    {
        "report",
        "area",
        "product",
        "date",
        "lot",
        "candidate_list",
        "resource",
        "planning",
    }
)

REQUIRED_TELEMETRY_FIELDS = frozenset(
    {
        "program_name",
        "report_family",
        "query_file",
        "query_version",
        "parameters",
        "connection_profile",
        "start_time",
        "end_time",
        "elapsed_seconds",
        "row_count",
        "raw_output_path",
        "processed_output_path",
        "published_output_path",
        "status",
        "error_number",
        "error_state",
        "error_message",
        "previous_published_data_remained_active",
    }
)

_IDENTIFIER = r"(?:\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_$#]*)"
_TARGET_IDENTIFIER = (
    r"(?:##?[A-Za-z_][A-Za-z0-9_$#]*|"
    + _IDENTIFIER
    + r")"
)
_THREE_PART_NAME = re.compile(
    rf"(?<![@#])(?P<database>{_IDENTIFIER})\s*\.\s*"
    rf"{_IDENTIFIER}\s*\.\s*{_IDENTIFIER}",
    re.IGNORECASE,
)
_PARAMETER_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\r\n]*")
_STRING_LITERAL = re.compile(r"N?'(?:''|[^'])*'", re.IGNORECASE)


@dataclass(frozen=True)
class RuntimeGuardrails:
    """MES runner settings, including an overall wall-clock deadline."""

    live_mes_enabled: bool = False
    read_only_profile: str = DEFAULT_READ_ONLY_PROFILE
    connection_timeout_seconds: int = DEFAULT_CONNECTION_TIMEOUT_SECONDS
    query_timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS
    total_refresh_deadline_seconds: int = (
        DEFAULT_TOTAL_REFRESH_DEADLINE_SECONDS
    )
    warning_threshold_seconds: int = DEFAULT_WARNING_THRESHOLD_SECONDS
    hard_failure_threshold_seconds: int = HARD_FAILURE_THRESHOLD_SECONDS
    per_query_retry: int = DEFAULT_PER_QUERY_RETRY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueryValidationReport:
    """Machine-readable result from the static query-contract gate."""

    contract_path: Path
    query_path: Path | None
    evidence_path: Path | None
    query_sha256: str | None
    static_gate_passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    runtime_guardrails: RuntimeGuardrails

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": POLICY_VERSION,
            "contract_path": str(self.contract_path),
            "query_path": (
                str(self.query_path) if self.query_path is not None else None
            ),
            "evidence_path": (
                str(self.evidence_path)
                if self.evidence_path is not None
                else None
            ),
            "query_sha256": self.query_sha256,
            "static_gate_passed": self.static_gate_passed,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "runtime_guardrails": self.runtime_guardrails.to_dict(),
            "required_telemetry_fields": sorted(REQUIRED_TELEMETRY_FIELDS),
            "important_boundary": (
                "A static pass is necessary but is not production approval. "
                "Live read-only validation evidence and owner review remain "
                "required before app wiring or scheduling."
            ),
        }


def _environment_bool(
    environment: Mapping[str, str], name: str, default: bool
) -> bool:
    value = environment.get(name)
    if value is None:
        return default
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _environment_int(
    environment: Mapping[str, str], name: str, default: int
) -> int:
    value = environment.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def get_runtime_guardrails(
    environment: Mapping[str, str] | None = None,
) -> RuntimeGuardrails:
    """Load guardrails without allowing environment values to relax policy."""

    source = os.environ if environment is None else environment
    profile = source.get(
        "PROGRAM_DATA_MES_READ_ONLY_PROFILE",
        DEFAULT_READ_ONLY_PROFILE,
    ).strip()
    if not profile:
        raise ValueError(
            "PROGRAM_DATA_MES_READ_ONLY_PROFILE must not be empty"
        )

    guardrails = RuntimeGuardrails(
        live_mes_enabled=_environment_bool(
            source,
            "PROGRAM_DATA_MES_LIVE_ENABLED",
            False,
        ),
        read_only_profile=profile,
        connection_timeout_seconds=_environment_int(
            source,
            "PROGRAM_DATA_MES_CONNECTION_TIMEOUT_SECONDS",
            DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        ),
        query_timeout_seconds=_environment_int(
            source,
            "PROGRAM_DATA_MES_QUERY_TIMEOUT_SECONDS",
            DEFAULT_QUERY_TIMEOUT_SECONDS,
        ),
        total_refresh_deadline_seconds=_environment_int(
            source,
            "PROGRAM_DATA_MES_TOTAL_REFRESH_DEADLINE_SECONDS",
            DEFAULT_TOTAL_REFRESH_DEADLINE_SECONDS,
        ),
        warning_threshold_seconds=_environment_int(
            source,
            "PROGRAM_DATA_MES_WARNING_THRESHOLD_SECONDS",
            DEFAULT_WARNING_THRESHOLD_SECONDS,
        ),
        per_query_retry=_environment_int(
            source,
            "PROGRAM_DATA_MES_PER_QUERY_RETRY",
            DEFAULT_PER_QUERY_RETRY,
        ),
    )

    if not 0 < guardrails.connection_timeout_seconds <= 30:
        raise ValueError(
            "MES connection timeout must be between 1 and 30 seconds"
        )
    if not 0 < guardrails.query_timeout_seconds <= 300:
        raise ValueError("MES query timeout must be between 1 and 300 seconds")
    if not 0 < guardrails.total_refresh_deadline_seconds <= 300:
        raise ValueError(
            "MES total refresh deadline must be between 1 and 300 seconds"
        )
    if not (
        0
        < guardrails.warning_threshold_seconds
        < guardrails.total_refresh_deadline_seconds
        <= guardrails.hard_failure_threshold_seconds
    ):
        raise ValueError(
            "MES warning threshold must be lower than the total refresh "
            "deadline, which cannot exceed 300 seconds"
        )
    if guardrails.per_query_retry not in {0, 1}:
        raise ValueError("MES per-query retry must be 0 or 1")
    return guardrails


def _mapping(
    value: Any, label: str, errors: list[str]
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    errors.append(f"{label} must be a JSON object.")
    return {}


def _required_text(
    value: Any, label: str, errors: list[str]
) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    errors.append(f"{label} must be a non-empty string.")
    return None


def _strict_bool(
    value: Any, label: str, errors: list[str]
) -> bool | None:
    if type(value) is bool:
        return value
    errors.append(f"{label} must be true or false.")
    return None


def _number(
    value: Any, label: str, errors: list[str]
) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    errors.append(f"{label} must be numeric.")
    return None


def _integer(
    value: Any, label: str, errors: list[str]
) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    errors.append(f"{label} must be an integer.")
    return None


def _normalize_identifier(value: str) -> str:
    return value.strip().strip("[]").casefold()


def _is_temp_target(value: str) -> bool:
    return value.strip().strip("[]").startswith("#")


def _strip_comments_and_literals(sql_text: str) -> str:
    without_blocks = _BLOCK_COMMENT.sub(" ", sql_text)
    without_lines = _LINE_COMMENT.sub(" ", without_blocks)
    return _STRING_LITERAL.sub("''", without_lines)


def _where_clauses(clean_sql: str) -> list[str]:
    return [
        match.group("body")
        for match in re.finditer(
            r"\bWHERE\b(?P<body>.*?)(?="
            r"\bGROUP\s+BY\b|\bORDER\s+BY\b|\bHAVING\b|"
            r"\bUNION\b|\bOPTION\b|;|$)",
            clean_sql,
            re.IGNORECASE | re.DOTALL,
        )
    ]


def _contains_select_star(clean_sql: str) -> bool:
    star_projection = re.compile(
        r"(?:^|,)\s*"
        r"(?:DISTINCT\s+)?"
        r"(?:TOP\s*(?:\([^)]*\)|\d+)\s+)?"
        rf"(?:{_IDENTIFIER}\s*\.\s*)?"
        r"\*"
        r"(?:\s+AS\s+" + _IDENTIFIER + r")?"
        r"\s*(?=,|$)",
        re.IGNORECASE | re.DOTALL,
    )
    for match in re.finditer(
        r"\bSELECT\b(?P<projection>.*?)\bFROM\b",
        clean_sql,
        re.IGNORECASE | re.DOTALL,
    ):
        if star_projection.search(match.group("projection")):
            return True
    return False


def _validate_write_targets(clean_sql: str, errors: list[str]) -> None:
    always_forbidden = (
        "MERGE",
        "TRUNCATE",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "GRANT",
        "DENY",
        "REVOKE",
        "DBCC",
        "BACKUP",
        "RESTORE",
        "KILL",
        "SHUTDOWN",
        "WAITFOR",
        "OPENQUERY",
        "OPENROWSET",
        "OPENDATASOURCE",
        "BULK INSERT",
        "CREATE VIEW",
        "CREATE PROCEDURE",
        "CREATE FUNCTION",
        "CREATE TRIGGER",
        "CREATE SCHEMA",
        "CREATE DATABASE",
        "DROP VIEW",
        "DROP PROCEDURE",
        "DROP FUNCTION",
        "DROP TRIGGER",
        "DROP SCHEMA",
        "DROP DATABASE",
        "DROP INDEX",
    )
    for keyword in always_forbidden:
        keyword_pattern = r"\s+".join(
            re.escape(part) for part in keyword.split()
        )
        if re.search(
            rf"\b{keyword_pattern}\b",
            clean_sql,
            re.IGNORECASE,
        ):
            errors.append(f"SQL contains forbidden operation: {keyword}.")

    target_patterns = {
        "INSERT": (
            rf"\bINSERT\s+(?:INTO\s+)?(?P<target>{_TARGET_IDENTIFIER})"
        ),
        "SELECT INTO": rf"\bINTO\s+(?P<target>{_TARGET_IDENTIFIER})",
        "UPDATE": rf"\bUPDATE\s+(?P<target>{_TARGET_IDENTIFIER})",
        "DELETE": (
            rf"\bDELETE\s+FROM\s+(?P<target>{_TARGET_IDENTIFIER})"
        ),
        "DELETE alias": (
            rf"\bDELETE\s+(?P<target>{_TARGET_IDENTIFIER})\s+FROM\b"
        ),
        "CREATE TABLE": (
            rf"\bCREATE\s+TABLE\s+(?P<target>{_TARGET_IDENTIFIER})"
        ),
        "DROP TABLE": (
            rf"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?"
            rf"(?P<target>{_TARGET_IDENTIFIER})"
        ),
    }
    for operation, pattern in target_patterns.items():
        for match in re.finditer(pattern, clean_sql, re.IGNORECASE):
            target = match.group("target")
            if not _is_temp_target(target):
                errors.append(
                    f"{operation} may target only a local #temp table; "
                    f"found {target}."
                )

    for match in re.finditer(
        rf"\bCREATE\s+(?:UNIQUE\s+)?INDEX\s+{_IDENTIFIER}\s+"
        rf"ON\s+(?P<target>{_TARGET_IDENTIFIER})",
        clean_sql,
        re.IGNORECASE,
    ):
        if not _is_temp_target(match.group("target")):
            errors.append(
                "CREATE INDEX may target only a local #temp table."
            )


def _validate_output_target(
    value: Any,
    label: str,
    required_prefix: tuple[str, ...],
    errors: list[str],
) -> None:
    text_value = _required_text(value, label, errors)
    if text_value is None:
        return
    normalized_text = text_value.replace("\\", "/")
    path = PurePosixPath(normalized_text)
    parts = tuple(part.casefold() for part in path.parts)
    if (
        path.is_absolute()
        or re.match(r"^[A-Za-z]:", normalized_text)
        or ".." in path.parts
    ):
        errors.append(f"{label} must be a project-relative safe path.")
        return
    if parts[: len(required_prefix)] != required_prefix:
        expected = "/".join(required_prefix)
        errors.append(f"{label} must be under {expected}/.")
    elif len(parts) == len(required_prefix):
        errors.append(f"{label} must name a report-specific target.")


def _validate_class_a_evidence(
    evidence: Mapping[str, Any],
    *,
    evidence_path: Path | None,
    root: Path,
    program_name: str | None,
    report_family: str | None,
    query_version: str | None,
    query_path: Path | None,
    query_sha256: str | None,
    database_name: str | None,
    connection_profile: str | None,
    parameter_defaults: Mapping[str, Any],
    declared_elapsed_seconds: float | None,
    known_rows: int | None,
    expected_min: int | None,
    expected_max: int | None,
    errors: list[str],
) -> None:
    if evidence_path is None or not evidence:
        errors.append(
            "Class A requires a readable validation evidence JSON file."
        )
        return

    status = _required_text(
        evidence.get("status"),
        "evidence.status",
        errors,
    )
    if status is not None and status.casefold() != "pass":
        errors.append("Class A evidence status must be PASS.")

    expected_text_fields = {
        "program_name": program_name,
        "report_family": report_family,
        "query_version": query_version,
        "database_name": database_name,
        "connection_profile": connection_profile,
    }
    for field, expected_value in expected_text_fields.items():
        evidence_value = _required_text(
            evidence.get(field),
            f"evidence.{field}",
            errors,
        )
        if (
            evidence_value is not None
            and expected_value is not None
            and evidence_value != expected_value
        ):
            errors.append(
                f"evidence.{field} does not match the query contract."
            )

    evidence_query_file = _required_text(
        evidence.get("query_file"),
        "evidence.query_file",
        errors,
    )
    if query_path is not None and evidence_query_file is not None:
        try:
            expected_query_file = query_path.relative_to(root).as_posix()
        except ValueError:
            expected_query_file = query_path.as_posix()
        if (
            evidence_query_file.replace("\\", "/").casefold()
            != expected_query_file.casefold()
        ):
            errors.append(
                "evidence.query_file does not identify the governed query."
            )

    evidence_sha = _required_text(
        evidence.get("query_sha256"),
        "evidence.query_sha256",
        errors,
    )
    if (
        evidence_sha is not None
        and query_sha256 is not None
        and evidence_sha.casefold() != query_sha256.casefold()
    ):
        errors.append(
            "Evidence query SHA-256 does not match the current query file."
        )

    evidence_parameters = evidence.get("parameters")
    if not isinstance(evidence_parameters, Mapping):
        errors.append("evidence.parameters must be a JSON object.")
    elif parameter_defaults and dict(evidence_parameters) != dict(
        parameter_defaults
    ):
        errors.append(
            "Evidence parameters do not match scope.parameter_defaults."
        )

    _required_text(
        evidence.get("start_time"),
        "evidence.start_time",
        errors,
    )
    _required_text(
        evidence.get("end_time"),
        "evidence.end_time",
        errors,
    )

    evidence_elapsed = _number(
        evidence.get("elapsed_seconds"),
        "evidence.elapsed_seconds",
        errors,
    )
    if evidence_elapsed is not None:
        if not 0 <= evidence_elapsed < HARD_FAILURE_THRESHOLD_SECONDS:
            errors.append(
                "Evidence full-refresh time must be under 300 seconds."
            )
        if (
            declared_elapsed_seconds is not None
            and abs(evidence_elapsed - declared_elapsed_seconds) > 0.001
        ):
            errors.append(
                "Evidence elapsed time does not match contract validation."
            )

    timing_includes = _mapping(
        evidence.get("timing_includes"),
        "evidence.timing_includes",
        errors,
    )
    for phase in (
        "connection",
        "execution",
        "fetch",
        "raw_archive_write",
    ):
        if (
            _strict_bool(
                timing_includes.get(phase),
                f"evidence.timing_includes.{phase}",
                errors,
            )
            is not True
        ):
            errors.append(
                f"Class A evidence timing must include {phase}."
            )

    evidence_rows = _integer(
        evidence.get("row_count"),
        "evidence.row_count",
        errors,
    )
    if evidence_rows is not None:
        if (
            expected_min is not None
            and expected_max is not None
            and not expected_min <= evidence_rows <= expected_max
        ):
            errors.append(
                "Evidence row count is outside the expected range."
            )
        if known_rows is not None and evidence_rows != known_rows:
            errors.append(
                "Evidence row count does not match the contract test case."
            )

    for field in ("raw_output_path", "processed_output_path"):
        _required_text(
            evidence.get(field),
            f"evidence.{field}",
            errors,
        )

    audit = _mapping(evidence.get("audit"), "evidence.audit", errors)
    if not audit:
        errors.append("Class A evidence must contain at least one audit.")
    for audit_name, audit_value in audit.items():
        if not isinstance(audit_name, str) or not audit_name.strip():
            errors.append("Evidence audit names must be non-empty strings.")
            continue
        if (
            _strict_bool(
                audit_value,
                f"evidence.audit.{audit_name}",
                errors,
            )
            is not True
        ):
            errors.append(
                f"Class A evidence audit must pass {audit_name}."
            )
    if audit.get("dashboard_visibility_passed") is not True:
        errors.append(
            "Class A evidence must pass dashboard_visibility_passed."
        )

    if (
        _strict_bool(
            evidence.get("previous_published_data_remained_active"),
            "evidence.previous_published_data_remained_active",
            errors,
        )
        is not True
    ):
        errors.append(
            "Evidence must confirm previous published data remained active."
        )

    _required_text(
        evidence.get("reviewed_by"),
        "evidence.reviewed_by",
        errors,
    )
    _required_text(
        evidence.get("reviewed_at"),
        "evidence.reviewed_at",
        errors,
    )

    for error_field in ("error_number", "error_state", "error_message"):
        if evidence.get(error_field) not in {None, ""}:
            errors.append(
                f"PASS evidence must leave {error_field} empty."
            )


def _validate_sql(
    sql_text: str,
    *,
    parameters: list[str],
    bound_parameters: list[str],
    scope: Mapping[str, Any],
    errors: list[str],
) -> None:
    clean_sql = _strip_comments_and_literals(sql_text)
    if not re.search(r"\bSELECT\b", clean_sql, re.IGNORECASE):
        errors.append("SQL must contain a SELECT result set.")
    if re.search(r"\bUSE\b", clean_sql, re.IGNORECASE):
        errors.append(
            "SQL must not contain USE; the runner pins the DemoManufacturing database."
        )
    if _contains_select_star(clean_sql):
        errors.append("SQL must not use SELECT * or alias.* projections.")

    _validate_write_targets(clean_sql, errors)

    for match in _THREE_PART_NAME.finditer(clean_sql):
        database = _normalize_identifier(match.group("database"))
        if database != MES_DATABASE_NAME.casefold():
            errors.append(
                "SQL contains a three-part name outside DemoManufacturing: "
                f"{match.group('database')}."
            )

    where_clauses = _where_clauses(clean_sql)
    if not where_clauses:
        errors.append("SQL must contain a bounded WHERE predicate.")

    for parameter in parameters:
        if not re.search(
            rf"@{re.escape(parameter)}\b",
            clean_sql,
            re.IGNORECASE,
        ):
            errors.append(
                f"Declared parameter @{parameter} is not referenced in SQL."
            )

    for parameter in bound_parameters:
        if not any(
            re.search(
                rf"@{re.escape(parameter)}\b",
                clause,
                re.IGNORECASE,
            )
            for clause in where_clauses
        ):
            errors.append(
                f"Bound parameter @{parameter} is not used in a WHERE "
                "predicate."
            )

    scope_type = str(scope.get("type", "")).strip().casefold()
    if scope_type == "date":
        start_parameter = scope.get("start_parameter")
        end_parameter = scope.get("end_parameter")
        predicate_sql = "\n".join(where_clauses)
        if not isinstance(start_parameter, str) or not start_parameter.strip():
            errors.append(
                "scope.start_parameter is required for date-scoped SQL."
            )
        elif not re.search(
            rf">=\s*@{re.escape(start_parameter.strip())}\b",
            predicate_sql,
            re.IGNORECASE,
        ):
            errors.append(
                "Date-scoped SQL must use "
                f">= @{start_parameter.strip()}."
            )
        if not isinstance(end_parameter, str) or not end_parameter.strip():
            errors.append(
                "scope.end_parameter is required for date-scoped SQL."
            )
        elif not re.search(
            rf"(?<![<>=!])<(?!=)\s*"
            rf"@{re.escape(end_parameter.strip())}\b",
            predicate_sql,
            re.IGNORECASE,
        ):
            errors.append(
                "Date-scoped SQL must use the exclusive upper bound "
                f"< @{end_parameter.strip()}."
            )

    detail_cap = scope.get("detail_cap_parameter")
    if detail_cap is not None:
        if not isinstance(detail_cap, str) or not detail_cap.strip():
            errors.append(
                "scope.detail_cap_parameter must be a parameter name."
            )
        else:
            cap_name = re.escape(detail_cap.strip())
            has_cap = re.search(
                rf"\bTOP\s*\(\s*@{cap_name}\s*\)",
                clean_sql,
                re.IGNORECASE,
            ) or re.search(
                rf"\bFETCH\s+NEXT\s+@{cap_name}\s+ROWS\b",
                clean_sql,
                re.IGNORECASE,
            )
            if not has_cap:
                errors.append(
                    "The detail cap must be applied with TOP "
                    f"(@{detail_cap.strip()}) or FETCH NEXT."
                )

    indexed_columns = scope.get("indexed_filter_columns", [])
    if not isinstance(indexed_columns, list) or not all(
        isinstance(column, str) and column.strip()
        for column in indexed_columns
    ):
        errors.append(
            "scope.indexed_filter_columns must be a list of column names."
        )
        indexed_columns = []

    for clause in where_clauses:
        for function_name, arguments in _function_calls(clause):
            if function_name in {
                "and",
                "as",
                "case",
                "else",
                "exists",
                "having",
                "in",
                "not",
                "on",
                "or",
                "over",
                "then",
                "values",
                "when",
                "where",
            }:
                continue
            for column in indexed_columns:
                if re.search(
                    rf"(?:{_IDENTIFIER}\s*\.\s*)?"
                    rf"\[?{re.escape(column.strip())}\]?\b",
                    arguments,
                    re.IGNORECASE,
                ):
                    errors.append(
                        "Do not wrap indexed filter column "
                        f"{column.strip()} in {function_name}() in WHERE."
                    )


def _function_calls(sql_fragment: str) -> list[tuple[str, str]]:
    """Return simple and nested function calls from comment-free SQL."""

    calls: list[tuple[str, str]] = []
    opening_pattern = re.compile(
        rf"\b(?P<function>{_IDENTIFIER})\s*\(",
        re.IGNORECASE,
    )
    for match in opening_pattern.finditer(sql_fragment):
        opening_index = match.end() - 1
        depth = 0
        closing_index: int | None = None
        for index in range(opening_index, len(sql_fragment)):
            character = sql_fragment[index]
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    closing_index = index
                    break
        if closing_index is None:
            continue
        calls.append(
            (
                _normalize_identifier(match.group("function")),
                sql_fragment[opening_index + 1 : closing_index],
            )
        )
    return calls


def validate_query_contract(
    contract: str | Path,
    *,
    project_root: str | Path | None = None,
    guardrails: RuntimeGuardrails | None = None,
) -> QueryValidationReport:
    """Validate one project-owned contract and SQL file without executing it."""

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else PROJECT_ROOT.resolve()
    )
    contract_path = Path(contract).resolve()
    active_guardrails = guardrails or get_runtime_guardrails()
    errors: list[str] = []
    warnings: list[str] = []
    query_path: Path | None = None
    evidence_path: Path | None = None
    query_sha256: str | None = None
    evidence: Mapping[str, Any] = {}
    normalized_risk: str | None = None

    contracts_root = (root / "query_contracts").resolve()
    if not contract_path.is_relative_to(contracts_root):
        errors.append(
            "Contract must be stored under the project query_contracts/ "
            "directory."
        )

    try:
        raw_contract = json.loads(
            contract_path.read_text(encoding="utf-8-sig")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {contract_path}: {exc.msg}"
        ) from exc
    if not isinstance(raw_contract, Mapping):
        raise ValueError("Query contract must contain one JSON object")

    policy_version = _required_text(
        raw_contract.get("policy_version"),
        "policy_version",
        errors,
    )
    if policy_version is not None and policy_version != POLICY_VERSION:
        errors.append(
            f"policy_version must be {POLICY_VERSION}; found "
            f"{policy_version}."
        )

    program_name = _required_text(
        raw_contract.get("program_name"),
        "program_name",
        errors,
    )
    report_family = _required_text(
        raw_contract.get("report_family"),
        "report_family",
        errors,
    )
    query_version = _required_text(
        raw_contract.get("query_version"),
        "query_version",
        errors,
    )
    declared_query_sha256 = _required_text(
        raw_contract.get("candidate_query_sha256"),
        "candidate_query_sha256",
        errors,
    )
    if (
        declared_query_sha256 is not None
        and not re.fullmatch(r"[0-9A-Fa-f]{64}", declared_query_sha256)
    ):
        errors.append(
            "candidate_query_sha256 must contain exactly 64 hexadecimal "
            "characters."
        )

    database_name = _required_text(
        raw_contract.get("database_name"),
        "database_name",
        errors,
    )
    if (
        database_name is not None
        and database_name.casefold() != MES_DATABASE_NAME.casefold()
    ):
        errors.append(
            f"database_name must be {MES_DATABASE_NAME}, not "
            f"{database_name}."
        )

    connection_profile = _required_text(
        raw_contract.get("connection_profile"),
        "connection_profile",
        errors,
    )
    if (
        connection_profile is not None
        and connection_profile != active_guardrails.read_only_profile
    ):
        errors.append(
            "connection_profile must match the configured read-only MES "
            f"profile {active_guardrails.read_only_profile}."
        )

    risk_class = _required_text(
        raw_contract.get("risk_class"),
        "risk_class",
        errors,
    )
    if risk_class is not None:
        normalized_risk = risk_class.casefold()
        if normalized_risk not in {"a", "b", "c", "retired"}:
            errors.append("risk_class must be A, B, C, or Retired.")
        elif normalized_risk != "a":
            errors.append(
                f"Risk class {risk_class} is not app-wiring eligible; only "
                "Class A may pass this gate."
            )

    query_file = _required_text(
        raw_contract.get("query_file"),
        "query_file",
        errors,
    )
    if query_file is not None:
        configured_query_path = Path(query_file)
        if configured_query_path.is_absolute():
            errors.append("query_file must be relative to the contract file.")
        else:
            query_path = (
                contract_path.parent / configured_query_path
            ).resolve()
            governed_queries_root = (root / "queries").resolve()
            if not query_path.is_relative_to(governed_queries_root):
                errors.append(
                    "query_file must resolve under the new project's "
                    "queries/ directory."
                )
            if query_path.suffix.casefold() != ".sql":
                errors.append("query_file must reference a .sql file.")
            if not query_path.is_file():
                errors.append(f"Query file does not exist: {query_path}.")

    scope = _mapping(raw_contract.get("scope"), "scope", errors)
    parameter_defaults_value = scope.get("parameter_defaults", {})
    if isinstance(parameter_defaults_value, Mapping):
        parameter_defaults: Mapping[str, Any] = parameter_defaults_value
    else:
        errors.append("scope.parameter_defaults must be a JSON object.")
        parameter_defaults = {}
    scope_type = _required_text(scope.get("type"), "scope.type", errors)
    if (
        scope_type is not None
        and scope_type.casefold() not in ALLOWED_SCOPE_TYPES
    ):
        errors.append(
            "scope.type must be report, area, product, date, lot, "
            "candidate_list, resource, or planning."
        )

    parameters_value = scope.get("parameters")
    parameters: list[str] = []
    if not isinstance(parameters_value, list) or not parameters_value:
        errors.append("scope.parameters must be a non-empty list.")
    else:
        seen_parameters: set[str] = set()
        for parameter in parameters_value:
            if not isinstance(parameter, str) or not _PARAMETER_NAME.fullmatch(
                parameter
            ):
                errors.append(
                    "Every scope parameter must be an unprefixed SQL "
                    "parameter name."
                )
                continue
            normalized = parameter.casefold()
            if normalized in seen_parameters:
                errors.append(f"Duplicate scope parameter: {parameter}.")
                continue
            seen_parameters.add(normalized)
            parameters.append(parameter)

    bound_value = scope.get("bound_parameters")
    bound_parameters: list[str] = []
    if not isinstance(bound_value, list) or not bound_value:
        errors.append("scope.bound_parameters must be a non-empty list.")
    else:
        parameter_names = {name.casefold() for name in parameters}
        for parameter in bound_value:
            if not isinstance(parameter, str) or not _PARAMETER_NAME.fullmatch(
                parameter
            ):
                errors.append(
                    "Every bound parameter must be an unprefixed SQL "
                    "parameter name."
                )
                continue
            if parameter.casefold() not in parameter_names:
                errors.append(
                    f"Bound parameter {parameter} is not listed in "
                    "scope.parameters."
                )
            bound_parameters.append(parameter)

    detail_cap = scope.get("detail_cap_parameter")
    if (
        isinstance(detail_cap, str)
        and detail_cap.strip()
        and detail_cap.casefold()
        not in {name.casefold() for name in parameters}
    ):
        errors.append(
            "scope.detail_cap_parameter must also appear in "
            "scope.parameters."
        )

    validation = _mapping(
        raw_contract.get("validation"),
        "validation",
        errors,
    )
    if (
        _strict_bool(
            validation.get("tested_read_only"),
            "validation.tested_read_only",
            errors,
        )
        is not True
    ):
        errors.append(
            "The contract must confirm a read-only production MES test."
        )
    if (
        _strict_bool(
            validation.get("useful_rows_returned"),
            "validation.useful_rows_returned",
            errors,
        )
        is not True
    ):
        errors.append(
            "The contract must confirm useful rows for a known test case."
        )
    if (
        _strict_bool(
            validation.get("full_refresh_timed"),
            "validation.full_refresh_timed",
            errors,
        )
        is not True
    ):
        errors.append(
            "Elapsed validation time must include connection, execution, "
            "fetch, and raw local write."
        )
    _required_text(
        validation.get("known_test_case"),
        "validation.known_test_case",
        errors,
    )
    evidence_reference = _required_text(
        validation.get("evidence_reference"),
        "validation.evidence_reference",
        errors,
    )
    if evidence_reference is not None:
        configured_evidence_path = Path(evidence_reference)
        if configured_evidence_path.is_absolute():
            errors.append(
                "validation.evidence_reference must be project-relative."
            )
        else:
            evidence_path = (root / configured_evidence_path).resolve()
            evidence_root = (root / "query_contracts" / "evidence").resolve()
            if not evidence_path.is_relative_to(evidence_root):
                errors.append(
                    "validation.evidence_reference must resolve under "
                    "query_contracts/evidence/."
                )
            elif evidence_path.suffix.casefold() != ".json":
                errors.append(
                    "validation.evidence_reference must identify a JSON file."
                )
            elif not evidence_path.is_file():
                errors.append(
                    f"Validation evidence file does not exist: "
                    f"{evidence_path}."
                )
            else:
                try:
                    loaded_evidence = json.loads(
                        evidence_path.read_text(encoding="utf-8-sig")
                    )
                except json.JSONDecodeError as exc:
                    errors.append(
                        f"Invalid evidence JSON in {evidence_path}: "
                        f"{exc.msg}."
                    )
                else:
                    if isinstance(loaded_evidence, Mapping):
                        evidence = loaded_evidence
                    else:
                        errors.append(
                            "Validation evidence must contain one JSON "
                            "object."
                        )

    elapsed_seconds = _number(
        validation.get("elapsed_seconds"),
        "validation.elapsed_seconds",
        errors,
    )
    if elapsed_seconds is not None:
        if elapsed_seconds < 0:
            errors.append("validation.elapsed_seconds must not be negative.")
        elif elapsed_seconds >= HARD_FAILURE_THRESHOLD_SECONDS:
            errors.append(
                "Validated full-refresh time must be under 300 seconds."
            )
        elif elapsed_seconds >= active_guardrails.warning_threshold_seconds:
            warnings.append(
                "Validated full-refresh time is at or above the "
                f"{active_guardrails.warning_threshold_seconds}-second "
                "warning threshold."
            )

    known_rows = _integer(
        validation.get("known_test_case_row_count"),
        "validation.known_test_case_row_count",
        errors,
    )
    if known_rows is not None and known_rows <= 0:
        errors.append(
            "validation.known_test_case_row_count must be greater than zero."
        )

    expected_rows = _mapping(
        validation.get("expected_row_count"),
        "validation.expected_row_count",
        errors,
    )
    expected_min = _integer(
        expected_rows.get("min"),
        "validation.expected_row_count.min",
        errors,
    )
    expected_max = _integer(
        expected_rows.get("max"),
        "validation.expected_row_count.max",
        errors,
    )
    if expected_min is not None and expected_min < 0:
        errors.append("Expected minimum row count must not be negative.")
    if expected_max is not None and expected_max < 0:
        errors.append("Expected maximum row count must not be negative.")
    if (
        expected_min is not None
        and expected_max is not None
        and expected_min > expected_max
    ):
        errors.append("Expected row-count min must not exceed max.")
    if (
        known_rows is not None
        and expected_min is not None
        and expected_max is not None
        and not expected_min <= known_rows <= expected_max
    ):
        errors.append(
            "Known test-case row count is outside the documented expected "
            "range."
        )

    anomaly_policy = _required_text(
        validation.get("row_count_anomaly_policy"),
        "validation.row_count_anomaly_policy",
        errors,
    )
    if (
        anomaly_policy is not None
        and anomaly_policy.casefold() not in {"warn", "stop"}
    ):
        errors.append(
            "validation.row_count_anomaly_policy must be warn or stop."
        )

    consecutive_warning_runs = _integer(
        validation.get("consecutive_warning_runs"),
        "validation.consecutive_warning_runs",
        errors,
    )
    if consecutive_warning_runs is not None and consecutive_warning_runs < 0:
        errors.append(
            "validation.consecutive_warning_runs must not be negative."
        )

    outputs = _mapping(raw_contract.get("outputs"), "outputs", errors)
    _validate_output_target(
        outputs.get("raw_archive_target"),
        "outputs.raw_archive_target",
        ("data", "archive"),
        errors,
    )
    _validate_output_target(
        outputs.get("processed_artifact_target"),
        "outputs.processed_artifact_target",
        ("data", "processed"),
        errors,
    )
    _validate_output_target(
        outputs.get("published_artifact_target"),
        "outputs.published_artifact_target",
        ("data", "published"),
        errors,
    )
    if (
        _strict_bool(
            outputs.get("archive_raw_before_transform"),
            "outputs.archive_raw_before_transform",
            errors,
        )
        is not True
    ):
        errors.append(
            "Raw MES output must be archived before transformation."
        )
    if (
        _strict_bool(
            outputs.get("keep_previous_published_on_failure"),
            "outputs.keep_previous_published_on_failure",
            errors,
        )
        is not True
    ):
        errors.append(
            "Failed feeds must keep the previous published artifact active."
        )

    _required_text(raw_contract.get("audit_rule"), "audit_rule", errors)

    telemetry_fields = raw_contract.get("telemetry_fields")
    if not isinstance(telemetry_fields, list) or not all(
        isinstance(field, str) and field.strip()
        for field in telemetry_fields
    ):
        errors.append("telemetry_fields must be a list of field names.")
    else:
        normalized_fields = {
            field.strip().casefold() for field in telemetry_fields
        }
        missing_fields = sorted(
            REQUIRED_TELEMETRY_FIELDS - normalized_fields
        )
        if missing_fields:
            errors.append(
                "telemetry_fields is missing: " + ", ".join(missing_fields)
            )

    scheduling = _mapping(
        raw_contract.get("scheduling"),
        "scheduling",
        errors,
    )
    scheduled = _strict_bool(
        scheduling.get("enabled"),
        "scheduling.enabled",
        errors,
    )
    on_demand_only = _strict_bool(
        scheduling.get("on_demand_only"),
        "scheduling.on_demand_only",
        errors,
    )

    if scope_type is not None and scope_type.casefold() == "lot":
        if scheduled is True:
            errors.append("Lot drilldown queries must not be scheduled.")
        if on_demand_only is not True:
            errors.append(
                "Lot drilldown contracts must set on_demand_only to true."
            )

    if scheduled is True:
        _required_text(
            scheduling.get("business_cadence"),
            "scheduling.business_cadence",
            errors,
        )
        _required_text(
            scheduling.get("job_step"),
            "scheduling.job_step",
            errors,
        )
        if (
            _strict_bool(
                scheduling.get("one_report_family_per_job_step"),
                "scheduling.one_report_family_per_job_step",
                errors,
            )
            is not True
        ):
            errors.append(
                "Scheduled contracts must use one report family per job step."
            )
        if (
            consecutive_warning_runs is not None
            and consecutive_warning_runs >= 2
        ):
            errors.append(
                "Scheduling must be paused after two consecutive runs at or "
                "above the warning threshold."
            )

    if active_guardrails.per_query_retry == 1:
        retry_reviewed = _strict_bool(
            validation.get("retry_reviewed"),
            "validation.retry_reviewed",
            errors,
        )
        if retry_reviewed is not True:
            errors.append(
                "A retry count of 1 requires reviewed retry evidence in the "
                "contract."
            )

    if query_path is not None and query_path.is_file():
        query_bytes = query_path.read_bytes()
        query_sha256 = hashlib.sha256(query_bytes).hexdigest()
        try:
            sql_text = query_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            errors.append("Query file must be UTF-8 encoded.")
        else:
            _validate_sql(
                sql_text,
                parameters=parameters,
                bound_parameters=bound_parameters,
                scope=scope,
                errors=errors,
            )

    if (
        declared_query_sha256 is not None
        and re.fullmatch(r"[0-9A-Fa-f]{64}", declared_query_sha256)
        and query_sha256 is not None
        and declared_query_sha256.casefold() != query_sha256.casefold()
    ):
        errors.append(
            "candidate_query_sha256 does not match the current query file."
        )

    if normalized_risk == "a":
        _validate_class_a_evidence(
            evidence,
            evidence_path=evidence_path,
            root=root,
            program_name=program_name,
            report_family=report_family,
            query_version=query_version,
            query_path=query_path,
            query_sha256=query_sha256,
            database_name=database_name,
            connection_profile=connection_profile,
            parameter_defaults=parameter_defaults,
            declared_elapsed_seconds=elapsed_seconds,
            known_rows=known_rows,
            expected_min=expected_min,
            expected_max=expected_max,
            errors=errors,
        )

    if not active_guardrails.live_mes_enabled:
        warnings.append(
            "Live MES execution remains disabled by configuration; this "
            "validator did not connect to MES."
        )

    return QueryValidationReport(
        contract_path=contract_path,
        query_path=query_path,
        evidence_path=evidence_path,
        query_sha256=query_sha256,
        static_gate_passed=not errors,
        errors=tuple(dict.fromkeys(errors)),
        warnings=tuple(dict.fromkeys(warnings)),
        runtime_guardrails=active_guardrails,
    )
