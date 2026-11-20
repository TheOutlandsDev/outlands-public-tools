"""Verify saved planning authority artifacts and a normalized policy snapshot."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import stat
import sys
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool


AuthorityArtifact = Literal[
    "authoritative_policy",
    "automatic_lot_starts",
    "lot_start_policy",
    "detailed_planning",
    "approved_case_planning",
    "part_modality",
    "kanban_assignment",
    "wip_normalization",
    "active_fulfillment",
    "product_authority_matrix",
    "gate_b_business_input",
]

ARTIFACT_RELATIVE_PATHS: dict[AuthorityArtifact, Path] = {
    "authoritative_policy": Path("artifacts/authoritative-policy.json"),
    "automatic_lot_starts": Path("artifacts/automatic-lot-starts.json"),
    "lot_start_policy": Path("artifacts/lot-start-policy.json"),
    "detailed_planning": Path("artifacts/detailed-planning.json"),
    "approved_case_planning": Path("artifacts/approved-case-planning.json"),
    "part_modality": Path("artifacts/part-modality.json"),
    "kanban_assignment": Path("artifacts/kanban-assignment.json"),
    "wip_normalization": Path("artifacts/wip-normalization.json"),
    "active_fulfillment": Path("artifacts/active-fulfillment.json"),
    "product_authority_matrix": Path("artifacts/product-authority-matrix.json"),
    "gate_b_business_input": Path("artifacts/gate-b-business-input.csv"),
}

MAX_ARTIFACT_BYTES = 2_000_000
SEMANTIC_INPUTS = Path("semantic-inputs.json")
PolicyMode = Literal["legacy", "authoritative_gate_a"]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class PlanningAuthorityError(ValueError):
    """The saved authority bundle could not be verified."""


class SavedRuntimeStatus(BaseModel):
    """Policy status attached to the saved normalized settings."""

    mode: PolicyMode
    active: StrictBool
    policy_id: str = Field(min_length=1, max_length=160)
    policy_revision: str = Field(min_length=1, max_length=80)
    policy_sha256: Digest | None
    policy_document_status: str = Field(min_length=1, max_length=160)
    recommendation_factor: Literal["1.00"]
    legacy_comparison_factor: Literal["1.10"]
    legacy_comparison_factor_status: Literal["COMPARISON_ONLY_NOT_EXECUTABLE"]
    configured_products: int = Field(strict=True, ge=0, le=500)
    fail_closed_products: int = Field(strict=True, ge=0, le=500)
    event_identity_primary: Literal["legacy_contract_version", "candidate_policy_revision"]
    candidate_identities_for_new_events_only: StrictBool
    dual_alias_lookup: StrictBool
    historical_events_rewritten: StrictBool
    status_endpoint_database_writes: StrictBool
    production_included: StrictBool

    model_config = ConfigDict(extra="forbid", frozen=True)


class SavedSettings(BaseModel):
    """The JSON-mode model dumps used by the original semantic fingerprint."""

    source_fingerprint: Digest
    runtime: SavedRuntimeStatus
    planning_configuration: dict[str, Any]
    part_modality: dict[str, Any]
    wip_normalization: dict[str, Any]
    kanban_assignment: dict[str, Any]

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True)
class PlanningAuthorityPaths:
    project_root: Path
    artifacts: dict[AuthorityArtifact, Path]
    artifact_sha256: dict[AuthorityArtifact, str]
    source_fingerprint: str

    def path(self, artifact: AuthorityArtifact) -> Path:
        try:
            return self.artifacts[artifact]
        except KeyError as exc:
            raise PlanningAuthorityError("Unknown planning authority artifact.") from exc


@dataclass(frozen=True)
class PlanningAuthorityBundle:
    paths: PlanningAuthorityPaths
    settings: SavedSettings
    semantic_fingerprint: str


def _read_bounded(root: Path, relative: Path) -> bytes:
    candidate = root / relative
    if not candidate.resolve().is_relative_to(root):
        raise PlanningAuthorityError("A planning authority artifact escapes the project root.")
    try:
        parent = root
        for part in relative.parts[:-1]:
            parent /= part
            info = parent.lstat()
            if (not stat.S_ISDIR(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
                raise PlanningAuthorityError("An authority artifact parent must be an ordinary directory.")
        info = candidate.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise PlanningAuthorityError("A planning authority artifact must be an ordinary file.")
        with candidate.open("rb") as stream:
            content = stream.read(MAX_ARTIFACT_BYTES + 1)
    except OSError as exc:
        raise PlanningAuthorityError("A planning authority artifact is unavailable.") from exc
    if not 0 < len(content) <= MAX_ARTIFACT_BYTES:
        raise PlanningAuthorityError("A planning authority artifact is empty or exceeds its size limit.")
    return content


def load_planning_authority_paths(project_root: Path) -> PlanningAuthorityPaths:
    """Resolve and fingerprint the complete source set beneath one root."""
    root = project_root.resolve()
    artifacts = {}
    digests = {}
    for artifact, relative in ARTIFACT_RELATIVE_PATHS.items():
        digests[artifact] = sha256(_read_bounded(root, relative)).hexdigest()
        artifacts[artifact] = root / relative
    fingerprint_payload = json.dumps(
        {name: digests[name] for name in sorted(digests)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return PlanningAuthorityPaths(root, artifacts, digests, sha256(fingerprint_payload).hexdigest())


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise PlanningAuthorityError("The normalized settings contain duplicate JSON fields.")
    return fields


def _invalid_constant(_value: str) -> None:
    raise PlanningAuthorityError("The normalized settings contain a non-finite number.")


def _load_settings(paths: PlanningAuthorityPaths) -> SavedSettings:
    content = _read_bounded(paths.project_root, SEMANTIC_INPUTS)
    try:
        payload = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_fields,
                             parse_constant=_invalid_constant)
        return SavedSettings.model_validate(payload)
    except (ValueError, RecursionError) as exc:
        raise PlanningAuthorityError("The saved normalized settings are invalid.") from exc


def load_planning_authority(mode: PolicyMode, *, project_root: Path) -> PlanningAuthorityBundle:
    """Bind the saved normalized settings to the complete observed source set."""
    paths = load_planning_authority_paths(project_root)
    settings = _load_settings(paths)
    status = settings.runtime
    if settings.source_fingerprint != paths.source_fingerprint:
        raise PlanningAuthorityError("The normalized settings do not match the source fingerprint.")
    if status.mode != mode:
        raise PlanningAuthorityError("The saved policy mode does not match the requested mode.")
    active = mode == "authoritative_gate_a"
    if (
        status.active != active or status.candidate_identities_for_new_events_only != active
        or not status.dual_alias_lookup or status.historical_events_rewritten
        or status.status_endpoint_database_writes or status.production_included
        or status.event_identity_primary != ("candidate_policy_revision" if active else "legacy_contract_version")
    ):
        raise PlanningAuthorityError("The saved runtime status is incompatible with a development bundle.")
    expected_policy = paths.artifact_sha256["authoritative_policy"] if active else None
    if status.policy_sha256 != expected_policy:
        raise PlanningAuthorityError("The saved policy hash does not match the selected policy mode.")
    products = settings.planning_configuration.get("products")
    direct = settings.kanban_assignment.get("direct_kanbans")
    if (not isinstance(products, list) or not all(isinstance(item, dict) for item in products)
            or not isinstance(settings.part_modality.get("part_to_modality"), dict)
            or not settings.wip_normalization
            or not isinstance(direct, dict) or not all(isinstance(item, dict) for item in direct.values())):
        raise PlanningAuthorityError("A normalized component is missing its required structure.")

    semantic_payload = settings.model_dump(mode="json")
    try:
        semantic_fingerprint = sha256(json.dumps(
            semantic_payload, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
    except (ValueError, RecursionError) as exc:
        raise PlanningAuthorityError("The saved normalized settings could not be fingerprinted.") from exc
    return PlanningAuthorityBundle(paths, settings, semantic_fingerprint)


def authority_summary(bundle: PlanningAuthorityBundle) -> dict[str, str | int | bool]:
    status = bundle.settings.runtime
    return {
        "artifact_count": len(bundle.paths.artifacts),
        "recommendation_factor": status.recommendation_factor,
        "legacy_comparison_factor": status.legacy_comparison_factor,
        "active": status.active,
        "fingerprint": bundle.semantic_fingerprint,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Directory with the artifact set and semantic-inputs.json")
    parser.add_argument("--mode", choices=("authoritative_gate_a", "legacy"), default="authoritative_gate_a")
    parser.add_argument("--authority-summary", action="store_true", help="Emit the Program Authority Verifier summary")
    args = parser.parse_args()
    try:
        bundle = load_planning_authority(args.mode, project_root=args.root)
    except PlanningAuthorityError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError):
        print("The saved authority bundle is unavailable or invalid.", file=sys.stderr)
        return 2
    report = authority_summary(bundle) if args.authority_summary else {
        "status": "PASS",
        "artifact_sha256": bundle.paths.artifact_sha256,
        "source_fingerprint": bundle.paths.source_fingerprint,
        "semantic_fingerprint": bundle.semantic_fingerprint,
        "runtime": bundle.settings.runtime.model_dump(mode="json"),
    }
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
