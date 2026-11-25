from pathlib import Path

from planning_gap_register import read_register, validate_register


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "examples" / "gap-register.csv"
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


def _rows() -> list[dict[str, str]]:
    rows = read_register(WORKBOOK)
    assert list(rows[0]) == EXPECTED_COLUMNS
    validate_register(rows)
    return rows



def test_gate_b_business_input_workbook_contains_the_exact_19_product_gap() -> None:
    rows = _rows()

    assert len(rows) == 19
    assert all(row["artifact_role"] == "PRODUCT_GAP_REGISTER_ONLY" for row in rows)
    assert all(
        row["import_eligibility"] == "NOT_IMPORTABLE_MODEL_EVOLUTION_REQUIRED"
        for row in rows
    )
    assert sum(row["current_gate_b_state"] == "TIMING_REVIEW_PENDING" for row in rows) == 8
    assert sum(
        row["current_gate_b_state"] == "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
        for row in rows
    ) == 11
    assert len({row["record_id"] for row in rows}) == 19
    assert len({row["canonical_part_number"] for row in rows}) == 19
    assert all(row["business_review_status"] == "NOT_PROVIDED" for row in rows)
    assert all(row["technical_validation_status"] == "NOT_VALIDATED" for row in rows)
    assert all(row["business_approval_evidence_reference"] == "" for row in rows)
    assert all(row["technical_validation_evidence_reference"] == "" for row in rows)


def test_gate_b_legacy_values_remain_non_executable_and_user_values_are_preserved() -> None:
    rows = {row["modality"]: row for row in _rows()}

    assert rows["DEMO08"]["approved_standard_lot_quantity_circuits"] == "72"
    assert rows["DEMO08"]["lot_quantity_authority"] == "USER_CONFIRMED"
    assert rows["DEMO09"]["approved_standard_lot_quantity_circuits"] == ""
    assert rows["DEMO09"]["legacy_reference_quantity"] == "104"
    assert rows["DEMO09"]["lot_quantity_authority"] == "LEGACY_REFERENCE_ONLY"
    assert rows["DEMO10"]["legacy_reference_quantity"] == "44"
    assert rows["DEMO11"]["accepted_part_aliases"] == "DEMO-ALIAS-11"
    assert rows["DEMO11"]["approved_product_name"] == "Fictional Sensor Mount"
    assert rows["DEMO12"]["approved_product_name"] == "Fictional Panel Connector"
    assert all(
        row["approved_standard_lot_quantity_circuits"] == ""
        for row in rows.values()
        if row["current_gate_b_state"]
        == "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
    )


def test_gate_b_lot_quantity_and_lead_time_authorities_are_separate() -> None:
    rows = _rows()
    timing_pending = [
        row for row in rows if row["current_gate_b_state"] == "TIMING_REVIEW_PENDING"
    ]
    fail_closed = [
        row
        for row in rows
        if row["current_gate_b_state"]
        == "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
    ]

    assert len(timing_pending) == 8
    assert all(row["lot_quantity_authority"] == "USER_CONFIRMED" for row in timing_pending)
    assert all(row["current_lead_time_candidate_days"] == "21" for row in timing_pending)
    assert all(row["lead_time_authority"] == "LEGACY_REFERENCE_ONLY" for row in timing_pending)
    assert all(row["lead_time_authority"] == "NOT_PROVIDED" for row in fail_closed)
    assert all(row["current_lead_time_candidate_days"] == "" for row in fail_closed)


def test_gate_b_gap_register_has_no_importable_or_approved_rows() -> None:
    rows = _rows()

    assert all(row["route_and_operation_map_status"] == "NOT_PROVIDED" for row in rows)
    assert all(row["business_reviewer_name_sso"] == "" for row in rows)
    assert all(row["business_reviewed_on"] == "" for row in rows)
    assert all(row["technical_validator_name_sso"] == "" for row in rows)
    assert all(row["technical_validated_on"] == "" for row in rows)
