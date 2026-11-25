"""Validate a saved planning gap register and report the products awaiting review."""

import argparse
import csv
import io
import json
from pathlib import Path
import sys

EXPECTED_COLUMNS = [
    "record_id",
    "artifact_role",
    "import_eligibility",
    "current_gate_b_state",
    "observed_in_active_os",
    "demand_authority",
    "modality",
    "canonical_part_number",
    "approved_product_name",
    "accepted_part_aliases",
    "approved_lot_prefix",
    "approved_standard_lot_quantity_circuits",
    "legacy_reference_quantity",
    "lot_quantity_authority",
    "current_lead_time_candidate_days",
    "lead_time_authority",
    "route_and_operation_map_status",
    "timing_status",
    "business_review_status",
    "business_reviewer_name_sso",
    "business_reviewed_on",
    "business_approval_evidence_reference",
    "technical_validation_status",
    "technical_validator_name_sso",
    "technical_validated_on",
    "technical_validation_evidence_reference",
    "bounded_comment",
]

MAX_BYTES = 1024 * 1024
MAX_ROWS = 2_000
TIMING_PENDING = "TIMING_REVIEW_PENDING"
BUSINESS_INPUT_REQUIRED = "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
REGISTER_ONLY = {
    "artifact_role": "PRODUCT_GAP_REGISTER_ONLY",
    "import_eligibility": "NOT_IMPORTABLE_MODEL_EVOLUTION_REQUIRED",
    "route_and_operation_map_status": "NOT_PROVIDED",
    "business_review_status": "NOT_PROVIDED",
    "technical_validation_status": "NOT_VALIDATED",
    "business_reviewer_name_sso": "",
    "business_reviewed_on": "",
    "business_approval_evidence_reference": "",
    "technical_validator_name_sso": "",
    "technical_validated_on": "",
    "technical_validation_evidence_reference": "",
}


class RegisterError(ValueError):
    """The CSV does not satisfy the gap-register contract."""


def read_register(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RegisterError("Expected a local CSV file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise RegisterError("CSV exceeds the 1 MiB input limit")

    text = raw.decode("utf-8-sig")
    if "\x00" in text:
        raise RegisterError("NUL bytes are invalid in the CSV")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    if next(reader, None) != EXPECTED_COLUMNS:
        raise RegisterError("CSV header differs from the gap-register schema")
    rows = []
    for number, fields in enumerate(reader, start=2):
        if len(fields) != len(EXPECTED_COLUMNS):
            raise RegisterError(f"CSV record {number}: unexpected field count")
        if len(rows) == MAX_ROWS:
            raise RegisterError("CSV exceeds the 2,000-row limit")
        rows.append(dict(zip(EXPECTED_COLUMNS, fields, strict=True)))
    if not rows:
        raise RegisterError("CSV contains no product rows")
    return rows


def positive_decimal(value: str) -> bool:
    return value.isascii() and value.isdecimal() and bool(value.lstrip("0"))


def validate_row(row: dict[str, str], number: int) -> None:
    for field, expected in REGISTER_ONLY.items():
        if row[field] != expected:
            raise RegisterError(f"CSV record {number}: invalid register-only value for {field}")

    state = row["current_gate_b_state"]
    lot = row["approved_standard_lot_quantity_circuits"]
    legacy = row["legacy_reference_quantity"]
    lot_authority = row["lot_quantity_authority"]
    lead_time = row["current_lead_time_candidate_days"]
    lead_authority = row["lead_time_authority"]
    if legacy and not positive_decimal(legacy):
        raise RegisterError(f"CSV record {number}: invalid legacy lot quantity")
    if state == TIMING_PENDING:
        if lot_authority != "USER_CONFIRMED" or not positive_decimal(lot):
            raise RegisterError(f"CSV record {number}: timing review requires a confirmed lot quantity")
        if (lead_authority != "LEGACY_REFERENCE_ONLY" or not positive_decimal(lead_time)
                or row["timing_status"] != "LEGACY_DEFAULT_PENDING_PRODUCT_REVIEW"):
            raise RegisterError(f"CSV record {number}: timing candidate must remain reference-only")
    elif state == BUSINESS_INPUT_REQUIRED:
        legacy_authority = "LEGACY_REFERENCE_ONLY" if legacy else "NOT_PROVIDED"
        if lot or lot_authority != legacy_authority:
            raise RegisterError(f"CSV record {number}: unapproved lot quantity or authority")
        if lead_time or lead_authority != "NOT_PROVIDED" or row["timing_status"] != "NOT_PROVIDED":
            raise RegisterError(f"CSV record {number}: incomplete business inputs cannot carry timing")
    else:
        raise RegisterError(f"CSV record {number}: unsupported gap state")


def validate_register(rows: list[dict[str, str]]) -> dict:
    parts_by_state = {TIMING_PENDING: [], BUSINESS_INPUT_REQUIRED: []}
    identities = {"record_id": set(), "canonical_part_number": set()}
    for number, row in enumerate(rows, start=2):
        validate_row(row, number)
        for field, seen in identities.items():
            value = row[field]
            if not value or value != value.strip() or len(value) > 120 or not value.isprintable():
                raise RegisterError(f"CSV record {number}: invalid {field}")
            normalized = value.casefold()
            if normalized in seen:
                raise RegisterError(f"CSV record {number}: duplicate {field}")
            seen.add(normalized)
        parts_by_state[row["current_gate_b_state"]].append(row["canonical_part_number"])
    return {
        "status": "PASS",
        "total_products": len(rows),
        "importable": False,
        "counts_by_state": {state: len(parts) for state, parts in parts_by_state.items()},
        "part_numbers_by_state": {state: sorted(parts, key=str.casefold)
                                  for state, parts in parts_by_state.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    args = parser.parse_args()
    try:
        report = validate_register(read_register(args.register))
    except RegisterError as exc:
        print(f"Gap register: {exc}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, csv.Error):
        print("Gap register: cannot read valid UTF-8 CSV", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
