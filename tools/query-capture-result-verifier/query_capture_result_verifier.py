"""Check a saved query comparison manifest against a separate report contract."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import re
from stat import S_ISREG
import sys

MAX_DETAIL_ROWS = 10_000
MAX_INPUT_BYTES = 1_048_576
TIMESTAMP_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")
WINDOW_GUIDANCE = (
    "Use two YYYY-MM-DDTHH:MM:SS endpoints without timezone offsets, "
    "in the SQL datetime range and up to 24 hours apart."
)
ERROR_GUIDANCE = {
    "authentication": "The recorded capture failed authentication.",
    "previous_evidence": "The prior capture evidence could not be verified.",
    "source_changed": "The reviewed report or adapter source changed.",
    "result_shape": "The result columns or types could not be verified.",
    "unsupported_precision": "The comparison did not support the recorded timestamp precision.",
    "hard_timeout": "The recorded capture exceeded its deadline.",
    "supervision_failure": "The capture worker did not complete normally.",
    "parent_interrupted": "The recorded comparison was interrupted.",
    "worker_failure": "The capture worker did not return a complete manifest.",
    "connection_identity": "The recorded server or database identity differed from the approved identity.",
    "connection_cleanup": "The capture recorded a connection cleanup failure.",
    "detail_row_cap": "The recorded capture exceeded the 10,000-row limit.",
    "tls_validation": "The recorded capture failed certificate validation.",
    "connectivity": "The recorded capture failed to connect or timed out.",
    "driver": "The recorded capture encountered a database driver error.",
    "database_error": "The recorded database could not complete the query.",
    "invalid_window": WINDOW_GUIDANCE,
}
SAFE_SQLSTATES = frozenset((
    "28000", "08001", "08004", "08006", "08S01", "HYT00", "HYT01", "IM002",
    "IM003", "42000", "42S02", "42S22", "HY000", "HYC00",
))
EVIDENCE_STAGES = frozenset((
    "manifest_read", "manifest_schema", "source_hashes", "parameters", "identity",
    "fixture", "raw_path", "raw_read", "raw_hash", "csv", "nulls", "typed_rows", "fixture_digest",
))
COUNT_FIELDS = (
    "columns_compared", "expected_rows", "actual_rows", "matched_rows",
    "expected_only_rows", "actual_only_rows",
)
FLAG_FIELDS = ("all_values_match", "ordered_group_keys_match", "order_check_applicable", "sql_metadata_match")


@dataclass(frozen=True)
class CaptureContract:
    report: str
    start: str
    end: str
    expected_columns: int
    ordered: bool

    def __post_init__(self):
        if type(self.report) is not str or not self.report.strip() or len(self.report) > 120:
            raise ValueError("Contract report must be nonblank text of at most 120 characters")
        if type(self.expected_columns) is not int or self.expected_columns < 1:
            raise ValueError("Contract expected_columns must be a positive integer")
        if type(self.ordered) is not bool:
            raise ValueError("Contract ordered must be a JSON boolean")
        validate_window(self.start, self.end)


def validate_window(start: str, end: str) -> None:
    stamps = []
    for value in (start, end):
        if type(value) is not str or TIMESTAMP_PATTERN.fullmatch(value) is None:
            raise ValueError(WINDOW_GUIDANCE)
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(WINDOW_GUIDANCE) from None
        if timestamp.year < 1753:
            raise ValueError(WINDOW_GUIDANCE)
        stamps.append(timestamp)
    if not timedelta(0) < stamps[1] - stamps[0] <= timedelta(days=1):
        raise ValueError(WINDOW_GUIDANCE)


def error_summary(error: object) -> dict:
    if not isinstance(error, dict):
        error = {}
    category = error.get("category")
    state = error.get("sqlstate")
    category = category if isinstance(category, str) else None
    state = state if isinstance(state, str) else None
    if category == "invalid_window":
        return {"error_category": "invalid_window", "error_sqlstate": "N/A", "guidance": WINDOW_GUIDANCE}
    result = {
        "error_category": category if category in ERROR_GUIDANCE else "capture_failed",
        "error_sqlstate": state if state in SAFE_SQLSTATES else "N/A",
        "guidance": ERROR_GUIDANCE.get(category, "Comparison failed. Review the sanitized local manifest."),
    }
    stage = error.get("evidence_stage")
    failure = error.get("evidence_failure")
    if isinstance(stage, str) and stage in EVIDENCE_STAGES:
        result["evidence_stage"] = stage
    if failure in ("access_denied", "missing", "invalid"):
        result["evidence_failure"] = failure
    return result


def summary(contract: CaptureContract, manifest: dict) -> dict:
    """Verify evidence for one saved comparison case."""
    result = {
        "report": contract.report,
        "parameters": {"StartDate": contract.start, "EndDate": contract.end},
        "parity_status": "not_established",
    }
    if manifest.get("status") != "compared_not_validated":
        return {**result, "status": "failed", **error_summary(manifest.get("error", {}))}
    if manifest.get("parameters") != result["parameters"]:
        return {**result, "status": "failed", **error_summary({"category": "invalid_window"})}
    values = manifest.get("comparison")
    if not isinstance(values, dict):
        values = {}
    for field in COUNT_FIELDS:
        value = values.get(field)
        result[field] = value if type(value) is int and value >= 0 else None
    for field in FLAG_FIELDS:
        value = values.get(field)
        result[field] = value if type(value) is bool else None
    elapsed = manifest.get("elapsed_seconds")
    finite_elapsed = type(elapsed) is int or (type(elapsed) is float and math.isfinite(elapsed))
    result["elapsed_seconds"] = elapsed if finite_elapsed and elapsed >= 0 else None

    count = result["expected_rows"]
    if contract.ordered:
        order_pass = result["ordered_group_keys_match"] is True and result["order_check_applicable"] is True
    else:
        order_pass = (
            "ordered_group_keys_match" in values
            and values["ordered_group_keys_match"] is None
            and result["order_check_applicable"] is False
        )
    passed = (
        values.get("status") == "match"
        and result["columns_compared"] == contract.expected_columns
        and type(count) is int and count <= MAX_DETAIL_ROWS
        and count == result["actual_rows"] == result["matched_rows"]
        and result["expected_only_rows"] == result["actual_only_rows"] == 0
        and result["all_values_match"] is True
        and result["sql_metadata_match"] is True
        and order_pass
    )
    if passed and count == 0:
        result.update(
            status="empty_not_validated",
            guidance="Both captures were empty. A nonempty case is needed for data validation.",
        )
    elif passed:
        result.update(
            status="matched",
            guidance=f"All {contract.expected_columns} fields and row multiplicities matched for this case. Full report parity remains pending.",
        )
    else:
        result.update(
            status="mismatch",
            guidance="A required value, metadata, count or ordering comparison did not pass. Review local evidence.",
        )
    return result


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("Invalid JSON number")


def _read_object(path: Path, label: str) -> dict:
    try:
        if not S_ISREG(path.stat().st_mode):
            raise OSError
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        raise ValueError(f"{label} must be a readable regular file") from None
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError(f"{label} exceeds 1,048,576 bytes")
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ValueError(f"{label} must be valid UTF-8 JSON with unique keys") from None
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    try:
        contract_data = _read_object(args.contract, "Contract")
        fields = {"report", "start", "end", "expected_columns", "ordered"}
        if contract_data.keys() != fields:
            raise ValueError("Contract must provide report, start, end, expected_columns, and ordered")
        contract = CaptureContract(**contract_data)
        manifest = _read_object(args.manifest, "Manifest")
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 2

    print(json.dumps(summary(contract, manifest), indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
