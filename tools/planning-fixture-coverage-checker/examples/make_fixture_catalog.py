"""Generate a fictional coverage catalog, fixtures, and inert scenario sources."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixture_coverage import REQUIRED_SCENARIOS, _result_sha256


def write_json(path: Path, data: dict) -> None:
    path.write_bytes(json.dumps(data, indent=2).encode("utf-8") + b"\n")


def make_fixture_catalog(root: Path) -> None:
    root.mkdir()
    (root / "tests").mkdir()
    (root / "fixtures").mkdir()
    product_evidence = []
    products = []
    for number in range(1, 24):
        part, modality = f"DEMO-{number:02}", f"TYPE-{number:02}"
        if number <= 4:
            state = "DETAILED_CONFIGURATION"
        elif number <= 12:
            state = "TIMING_REVIEW_PENDING"
        else:
            state = "FAIL_CLOSED_BUSINESS_INPUT_REQUIRED"
        products.append(dict(part_number=part, modality=modality, coverage_state=state))
        if number > 4:
            continue
        dedicated = number <= 3
        relative = f"fixtures/{part.lower()}.json"
        status = "FICTIONAL_REVIEW_ONLY"
        write_json(root / relative, dict(part_number=part, modality=modality, status=status))
        product_evidence.append(dict(
            part_number=part, modality=modality,
            evidence_kind="DEDICATED_REVIEWED_FIXTURE" if dedicated else "CONTROLLED_SNAPSHOT_COMPARISON",
            source_path=relative, source_sha256=sha256((root / relative).read_bytes()).hexdigest(),
            dedicated_fixture=dedicated, authority_status=status,
            recommendation_expectation_authority=("LEGACY_1_10_COMPARISON_ONLY" if dedicated
                                                   else "AGGREGATE_SNAPSHOT_ONLY"),
        ))

    test_sources = []
    node_ids = []
    for group in range(3):
        relative = f"tests/test_scenario_{group}.py"
        nodes = [f"test_scenario_{number:02}" for number in range(group * 5, group * 5 + 5)]
        node_ids.extend(f"{relative}::{node}" for node in nodes)
        text = 'raise RuntimeError("Scenario sources must never be imported")\n\n'
        text += "\n\n".join(f"def {node}():\n    pass" for node in nodes) + "\n"
        data = text.encode("utf-8")
        (root / relative).write_bytes(data)
        test_sources.append(dict(source_path=relative, source_sha256=sha256(data).hexdigest()))

    reusable = {"EDITED", "EXACT_BOUNDARY", "SHIPPED", "WIP_SHORTAGE"}
    scenario_evidence = []
    for index, scenario in enumerate(REQUIRED_SCENARIOS):
        more_nodes = [node_ids[index + 11]] if index < 4 else []
        if index == 4:
            more_nodes = [node_ids[0]]
        scenario_evidence.append(dict(
            scenario=scenario, coverage_status="REUSABLE" if scenario in reusable else "PARTIAL",
            gap=None if scenario in reusable else f"Fictional {scenario.lower()} expected result pending.",
            test_nodes=[node_ids[index], *more_nodes],
        ))
    catalog = dict(
        catalog_id="planning-fixture-catalog-v1", status="DEVELOPMENT_SCAFFOLD_NOT_PARITY_COMPLETE",
        prepared_on="2030-05-01", technical_owner="Fictional team",
        business_values_created=False, calculations_executed=0, expected_values_generated=0,
        plans_generated=0, test_nodes_executed=0, database_reads=False, database_writes=False,
        silent_fallback_count=0, production_authority=False,
        required_scenarios=REQUIRED_SCENARIOS, test_sources=test_sources,
        product_evidence=product_evidence, scenario_evidence=scenario_evidence,
    )
    write_json(root / "fixture-catalog.json", catalog)
    report = dict(integrity_status="PASS", gate_b_status="BLOCKED", products=products,
                  detailed_product_count=4, timing_review_pending_count=8,
                  fail_closed_product_count=11, comparison_factor_products=4)
    report["result_sha256"] = _result_sha256(report)
    write_json(root / "configuration-report.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_fixture_catalog(parser.parse_args().directory)
