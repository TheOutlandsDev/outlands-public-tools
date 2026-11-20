"""Write a fictional source bundle and normalized policy snapshot."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from planning_bundle import ARTIFACT_RELATIVE_PATHS, SEMANTIC_INPUTS, load_planning_authority_paths


def make_bundle(root: Path, mode: str = "authoritative_gate_a") -> None:
    root.mkdir()
    (root / "artifacts").mkdir()
    for key, path in ARTIFACT_RELATIVE_PATHS.items():
        content = ("part,review\nDEMO-A,Fictional pending review\n" if path.suffix == ".csv"
                   else json.dumps({"artifact": key, "example": "Fictional authority evidence"}))
        (root / path).write_bytes(content.encode("utf-8"))
    paths = load_planning_authority_paths(root)
    active = mode == "authoritative_gate_a"
    runtime = dict(
        mode=mode, active=active, policy_id="DEMO-POLICY", policy_revision="demo-1",
        policy_sha256=paths.artifact_sha256["authoritative_policy"] if active else None,
        policy_document_status=("FICTIONAL_DEVELOPMENT_APPROVED" if active
                                else "CANDIDATE_NOT_LOADED_BY_LEGACY_READER"),
        recommendation_factor="1.00", legacy_comparison_factor="1.10",
        legacy_comparison_factor_status="COMPARISON_ONLY_NOT_EXECUTABLE",
        configured_products=12, fail_closed_products=11,
        event_identity_primary="candidate_policy_revision" if active else "legacy_contract_version",
        candidate_identities_for_new_events_only=active, dual_alias_lookup=True,
        historical_events_rewritten=False, status_endpoint_database_writes=False, production_included=False,
    )
    products = [f"DEMO-{number:02}" for number in range(1, 5)]
    payload = dict(
        source_fingerprint=paths.source_fingerprint, runtime=runtime,
        planning_configuration={"products": [{"part_number": product} for product in products]},
        part_modality={"part_to_modality": {product: f"TYPE-{index}" for index, product in enumerate(products)}},
        wip_normalization={"profile": "fictional"},
        kanban_assignment={
            "direct_kanbans": {
                product: {f"Fictional step {step:02}": (step % 6) + 1 for step in range(count)}
                for product, count in zip(products, (15, 16, 17, 18), strict=True)
            }
        },
    )
    (root / SEMANTIC_INPUTS).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--mode", choices=("authoritative_gate_a", "legacy"), default="authoritative_gate_a")
    args = parser.parse_args()
    make_bundle(args.directory, args.mode)
