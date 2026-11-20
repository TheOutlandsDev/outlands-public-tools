from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_authority import make_authority
from program_authority import (
    INDEX_RELATIVE_PATH,
    ProgramAuthorityError,
    SAFE_STATUS,
    SOURCE_PATHS,
    load_program_authority,
    validate_program_authority_expectations,
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    directory = tmp_path / "fictional"
    make_authority(directory)
    return directory


def test_program_authority_consolidates_current_state_without_runtime_work(root: Path) -> None:
    authority = load_program_authority(project_root=root)

    assert authority.status == SAFE_STATUS
    assert set(authority.source_sha256) == set(SOURCE_PATHS)
    assert len(authority.source_fingerprint) == 64
    assert len(authority.authority_fingerprint) == 64
    assert authority.observed_state["gate_b"] == {
        "integrity_status": "PASS",
        "gate_status": "BLOCKED",
        "retained_products": 9,
        "configured_products": 5,
        "detailed_products": 2,
        "timing_review_pending_products": 3,
        "fail_closed_products": 4,
    }
    assert authority.observed_state["gate_c"]["gate_status"] == "BLOCKED"
    assert authority.observed_state["functional_parity"]["capability_count"] == 10
    assert authority.observed_state["platform"] == {
        "current_routes": 7,
        "planned_routes": 2,
    }
    assert authority.observed_state["migrations"] == {
        "total": 6,
        "postgresql": 4,
        "clickhouse": 2,
        "live_execution_authorized": False,
    }


def test_program_authority_is_deterministic(root: Path) -> None:
    first = load_program_authority(project_root=root)
    second = load_program_authority(project_root=root)

    assert first.source_fingerprint == second.source_fingerprint
    assert first.authority_fingerprint == second.authority_fingerprint


def test_index_has_no_execution_or_production_authority(root: Path) -> None:
    payload = json.loads(
        (root / INDEX_RELATIVE_PATH).read_text(
            encoding="utf-8"
        )
    )

    assert payload["production_authority"] is False
    assert payload["activation_authorized"] is False
    assert payload["database_reads"] is False
    assert payload["database_writes"] is False
    assert payload["calculations_executed"] == 0
    assert payload["plans_generated"] == 0
    assert len(payload["blockers"]) == 3


def test_expected_state_tamper_fails_closed(root: Path) -> None:
    payload = json.loads(
        (root / INDEX_RELATIVE_PATH).read_text(
            encoding="utf-8"
        )
    )
    observed = deepcopy(payload["expected_state"])
    payload["expected_state"]["gate_b"]["configured_products"] = 9

    with pytest.raises(ProgramAuthorityError, match="state drifted"):
        validate_program_authority_expectations(payload, observed)


def test_runtime_authorization_tamper_fails_closed(root: Path) -> None:
    payload = json.loads(
        (root / INDEX_RELATIVE_PATH).read_text(
            encoding="utf-8"
        )
    )
    payload["activation_authorized"] = True

    with pytest.raises(ProgramAuthorityError, match="runtime work"):
        validate_program_authority_expectations(payload, payload["expected_state"])
