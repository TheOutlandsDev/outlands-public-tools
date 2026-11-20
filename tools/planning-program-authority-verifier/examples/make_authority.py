"""Write a fictional program authority index and evidence in a fresh directory."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from program_authority import INDEX_RELATIVE_PATH, SAFE_STATUS, SOURCE_PATHS


def make_authority(root: Path) -> None:
    root.mkdir()
    (root / "reports").mkdir()
    planning = {
        "artifact_count": 3, "recommendation_factor": "1.05",
        "legacy_comparison_factor": "1.20", "active": False,
    }
    coverage = {
        "integrity_status": "PASS", "gate_status": "BLOCKED",
        "retained_products": 9, "configured_products": 5, "detailed_products": 2,
        "timing_review_pending_products": 3, "fail_closed_products": 4,
    }
    fixtures = {
        "integrity_status": "PASS", "gate_status": "BLOCKED",
        "authoritative_expected_value_fixtures": 1, "legacy_comparison_fixtures": 4,
        "required_scenarios": 7, "reusable_scenarios": 2, "partial_scenarios": 1,
    }
    platform = {"current_routes": 7, "planned_routes": 2}
    migrations = {"total": 6, "postgresql": 4, "clickhouse": 2, "live_execution_authorized": False}
    parity = {
        "capability_count": 10,
        "categories": dict(IN=2, CALC=2, VIEW=2, AUTO=2, CTRL=2),
        "classifications": {"Ready": 5, "Pending": 5},
    }
    table = "".join(
        f"| {category}-{number} | Fictional capability | Evidence | Review | "
        f"{'Ready' if number == 1 else '**Pending**'} | Notes |\n"
        for category in ("IN", "CALC", "VIEW", "AUTO", "CTRL") for number in (1, 2)
    )
    evidence = {
        "functional-parity-matrix": table,
        "business-input-register": "reference,label\nDEMO-1,Fictional material\n",
        "system-logic": '{"scenario":"Fictional workshop"}\n',
    }
    for source_id, report in (
        ("planning-authority", planning), ("configuration-coverage", coverage),
        ("fixture-coverage", fixtures), ("database-migration-registry", migrations),
    ):
        semantic_bytes = json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
        evidence[source_id] = json.dumps({**report, "fingerprint": sha256(semantic_bytes).hexdigest()}, indent=2)
    evidence["platform-module-registry"] = json.dumps(platform, indent=2)
    sources = []
    for source_id, relative_path in SOURCE_PATHS.items():
        data = evidence[source_id].encode("utf-8")
        (root / relative_path).write_bytes(data)
        sources.append(dict(source_id=source_id, path=relative_path.as_posix(),
                            role="Fictional review evidence", sha256=sha256(data).hexdigest()))

    payload = {
        "contract_id": "DEMO-WORKSHOP", "contract_version": "1", "status": SAFE_STATUS,
        "technical_owner": "Fictional Workshop Team", "scope": "DEVELOPMENT_ONLY_SOURCE_AUTHORITY",
        "production_authority": False, "activation_authorized": False, "database_reads": False,
        "database_writes": False, "calculations_executed": 0, "plans_generated": 0,
        "sources": sources,
        "expected_state": {"planning_authority": planning, "gate_b": coverage, "gate_c": fixtures,
                           "functional_parity": parity, "platform": platform, "migrations": migrations},
        "blockers": ["Review trial timings", "Extend fictional test coverage", "Review sample inputs"],
        "allowed_next_action": "REVIEWED_INCREMENTAL_BUSINESS_AUTHORITY_ONLY",
    }
    (root / INDEX_RELATIVE_PATH).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    make_authority(parser.parse_args().directory)
