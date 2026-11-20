"""Preserved planning authority tests with a fictional source bundle."""

from pathlib import Path
import sys

import pytest

from planning_bundle import ARTIFACT_RELATIVE_PATHS, PlanningAuthorityError, load_planning_authority, load_planning_authority_paths

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from make_bundle import make_bundle


@pytest.fixture
def root(tmp_path: Path) -> Path:
    root = (tmp_path / "fictional").resolve()
    make_bundle(root)
    return root


def test_complete_planning_authority_source_set_is_bounded_and_stable(root: Path) -> None:
    paths = load_planning_authority_paths(root)

    assert set(paths.artifacts) == set(ARTIFACT_RELATIVE_PATHS)
    assert len(paths.artifacts) == 11
    assert all(path.is_relative_to(root) for path in paths.artifacts.values())
    assert all(len(digest) == 64 for digest in paths.artifact_sha256.values())
    assert len(paths.source_fingerprint) == 64


def test_authoritative_bundle_exposes_one_semantic_runtime(root: Path) -> None:
    first = load_planning_authority("authoritative_gate_a", project_root=root)
    second = load_planning_authority("authoritative_gate_a", project_root=root)

    assert first.settings.runtime.active is True
    assert first.settings.runtime.recommendation_factor == "1.00"
    assert first.settings.runtime.legacy_comparison_factor == "1.10"
    assert len(first.settings.planning_configuration["products"]) == 4
    assert sum(
        len(operations)
        for operations in first.settings.kanban_assignment["direct_kanbans"].values()
    ) == 66
    assert first.semantic_fingerprint == second.semantic_fingerprint


def test_source_fingerprint_changes_when_an_artifact_changes(root: Path, tmp_path: Path) -> None:
    copied_root = tmp_path / "candidate"
    for artifact, relative_path in ARTIFACT_RELATIVE_PATHS.items():
        target = copied_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / relative_path).read_bytes())

    baseline = load_planning_authority_paths(copied_root)
    changed = copied_root / ARTIFACT_RELATIVE_PATHS["gate_b_business_input"]
    changed.write_bytes(changed.read_bytes() + b"\n")
    candidate = load_planning_authority_paths(copied_root)

    assert baseline.source_fingerprint != candidate.source_fingerprint


def test_missing_authority_artifact_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(PlanningAuthorityError, match="unavailable"):
        load_planning_authority_paths(tmp_path)
