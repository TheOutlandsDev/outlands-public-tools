"""Create a fictional planning configuration and its pinned evidence."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


APPROVED = "APPROVED_DEVELOPMENT_BASELINE"
ABSENT = "NOT_PROVIDED"


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def identity(number: int) -> dict:
    return {"part_number": f"DEMO-{number:02}", "modality": f"TYPE-{number:02}"}


def make_configuration(root: Path) -> None:
    root.mkdir()
    (root / "evidence").mkdir()
    note = b"Fictional development review notes.\n"
    (root / "evidence/review.txt").write_bytes(note)
    parts = [identity(number) for number in range(1, 24)]
    policy = dict(policy_id="DEMO-POLICY", policy_revision="1.0.0",
                  configured_products=parts[:12], fail_closed_products=parts[12:])
    mapping = {"part_to_modality": {row["part_number"]: row["modality"] for row in parts}}
    matrix_products = []
    detail_products = []

    for number, part in enumerate(parts, start=1):
        row = dict(
            canonical_part_number=part["part_number"], modality=part["modality"],
            product_name=f"Fictional product {number}", demand_authority="Fictional order ledger",
            lot_size_authority=ABSENT, route_authority=ABSENT,
            operation_to_kanban_authority=ABSENT, timing_authority=ABSENT,
            business_review={"status": ABSENT},
            technical_validation={"status": "NOT_VALIDATED"},
        )
        if number <= 4:
            days = {str(stage): 8 - stage for stage in range(1, 8)}
            row.update(
                coverage_state="DETAILED_CONFIGURATION", coverage_reason="Reviewed fictional input.",
                lot_prefix=f"D{number:02}", lot_size_circuits=10 + number,
                lot_size_authority=APPROVED, flow_name=f"Fictional route {number}", route_version=1,
                route_authority=APPROVED, operation_to_kanban_count=2,
                operation_to_kanban_authority=APPROVED, kanban_days_remaining=days,
                lead_time_days=8, timing_authority=APPROVED, timing_exception_count=0,
                business_review=dict(status=APPROVED, reviewer="Fictional reviewer",
                                     reviewed_on="2030-04-01", evidence_reference="evidence/review.txt"),
                technical_validation=dict(status="PASS", validator="Fictional validator",
                                          validated_on="2030-04-01", evidence_reference="evidence/review.txt"),
            )
            detail_products.append({
                **part, "expected_lot_start_quantity": 10 + number, "flow_name": row["flow_name"],
                "route_version": 1, "operation_to_kanban": {"Prepare": 1, "Inspect": 7},
                "kanban_days_remaining": days, "timing_exceptions": [],
                "uncovered_demand_start_factor": "1.10",
            })
        elif number <= 12:
            row.update(coverage_state="TIMING_REVIEW_PENDING", coverage_reason="Fictional timing review pending.",
                       lot_prefix=f"D{number:02}", lot_size_circuits=10 + number, lot_size_authority=APPROVED)
        else:
            row.update(coverage_state="FAIL_CLOSED_BUSINESS_INPUT_REQUIRED",
                       coverage_reason="Fictional development values are unavailable.")
        matrix_products.append(row)

    matrix = dict(
        matrix_id="DEMO-AUTHORITY", matrix_revision="2.0.0",
        status="DEVELOPMENT_AUTHORITY_MATRIX_PARTIAL", prepared_on="2030-04-01",
        technical_owner="Fictional workshop", production_authority=False,
        recommendation_factor="1.00", legacy_comparison_factor="1.10",
        legacy_comparison_factor_status="COMPARISON_ONLY_NOT_EXECUTABLE",
        early_wip_loss_rate="0.20", early_wip_loss_authority="LEGACY_REFERENCE_ONLY_GATE_C_PENDING",
        products=matrix_products,
        sources=[{"path": "evidence/review.txt", "sha256": sha256(note).hexdigest(),
                  "role": "Fictional review evidence"}],
    )
    for name, payload in (("policy.json", policy), ("detail.json", {"products": detail_products}),
                          ("part-map.json", mapping), ("product-matrix.json", matrix)):
        write_json(root / name, payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_configuration(parser.parse_args().directory)
