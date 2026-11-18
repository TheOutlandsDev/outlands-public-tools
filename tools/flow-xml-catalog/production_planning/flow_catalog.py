"""Hash-gated, read-only catalog for development flow XML references."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .flow_xml import FlowXmlDocument, FlowXmlValidationError, parse_flow_xml


class FlowCatalogError(ValueError):
    """Raised when the catalog or an immutable source fails validation."""


class FlowCatalogEntry(BaseModel):
    filename: str = Field(min_length=1, max_length=255, pattern=r"^[^/\\]+\.xml$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    flow_name: str = Field(min_length=1, max_length=256)
    flow_version: str = Field(min_length=1, max_length=50)
    step_count: int = Field(gt=0, le=1000)
    rework_path_count: int = Field(ge=0, le=1000)
    classification: str = Field(min_length=1, max_length=100)
    catalog_status: str = Field(
        pattern=r"^(ACTIVE_DEVELOPMENT_REFERENCE|CANDIDATE_NOT_ACTIVE)$"
    )
    review_authority: str = Field(min_length=1, max_length=200)
    model_config = ConfigDict(frozen=True)

    @property
    def active(self) -> bool:
        return self.catalog_status == "ACTIVE_DEVELOPMENT_REFERENCE"


class MissingFlowXml(BaseModel):
    flow_name: str
    flow_version: str
    expected_step_count: int = Field(gt=0)
    model_config = ConfigDict(frozen=True)


class FlowCatalogManifest(BaseModel):
    manifest_id: str
    manifest_version: str
    status: str
    sources: tuple[FlowCatalogEntry, ...] = Field(min_length=1, max_length=100)
    missing_fw32_xml: MissingFlowXml
    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_uniqueness_and_activation(self):
        identities = [(x.flow_name, x.flow_version) for x in self.sources]
        hashes = [x.sha256 for x in self.sources]
        filenames = [x.filename.casefold() for x in self.sources]
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate flow name and version")
        if len(hashes) != len(set(hashes)):
            raise ValueError("duplicate source checksum")
        if len(filenames) != len(set(filenames)):
            raise ValueError("duplicate source filename")
        active_names = [x.flow_name for x in self.sources if x.active]
        if len(active_names) != len(set(active_names)):
            raise ValueError("more than one active development version for a flow")
        return self


class VerifiedFlowCatalog(BaseModel):
    manifest: FlowCatalogManifest
    documents: dict[str, FlowXmlDocument]
    model_config = ConfigDict(frozen=True)


def load_verified_catalog(
    manifest_path: Path,
    source_directory: Path,
) -> VerifiedFlowCatalog:
    """Load the tracked catalog and prove every external source matches it."""

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = FlowCatalogManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise FlowCatalogError("flow catalog manifest is invalid") from exc

    documents: dict[str, FlowXmlDocument] = {}
    for entry in manifest.sources:
        try:
            document = parse_flow_xml((source_directory / entry.filename).read_bytes())
        except (OSError, FlowXmlValidationError) as exc:
            raise FlowCatalogError("catalog source is missing or invalid") from exc
        actual = (
            document.source_sha256,
            document.flow_name,
            document.flow_version,
            len(document.steps),
            len(document.rework_paths),
        )
        expected = (
            entry.sha256,
            entry.flow_name,
            entry.flow_version,
            entry.step_count,
            entry.rework_path_count,
        )
        if actual != expected:
            raise FlowCatalogError("catalog source does not match its manifest")
        documents[entry.sha256] = document
    return VerifiedFlowCatalog(manifest=manifest, documents=documents)


def compare_flows(left: FlowXmlDocument, right: FlowXmlDocument) -> dict:
    """Return a deterministic, bounded position-by-position comparison."""

    left_by_position = {step.position: step for step in left.steps}
    right_by_position = {step.position: step for step in right.steps}
    positions = sorted(set(left_by_position) | set(right_by_position))
    changes = []
    for position in positions:
        left_step = left_by_position.get(position)
        right_step = right_by_position.get(position)
        if left_step == right_step:
            continue
        fields = (
            "step_name",
            "step_ref_id",
            "flow_step_object_id",
            "correlation_id",
            "is_optional",
            "is_skippable",
            "is_source",
            "is_line",
        )
        changed_fields = [
            field
            for field in fields
            if (None if left_step is None else getattr(left_step, field))
            != (None if right_step is None else getattr(right_step, field))
        ]
        changes.append(
            {
                "position": position,
                "left_step": None if left_step is None else left_step.step_name,
                "right_step": None if right_step is None else right_step.step_name,
                "left_ref_id": None if left_step is None else left_step.step_ref_id,
                "right_ref_id": None if right_step is None else right_step.step_ref_id,
                "changed_fields": changed_fields,
            }
        )
    return {
        "left": {"flow_name": left.flow_name, "flow_version": left.flow_version},
        "right": {"flow_name": right.flow_name, "flow_version": right.flow_version},
        "step_count_delta": len(right.steps) - len(left.steps),
        "rework_path_count_delta": len(right.rework_paths) - len(left.rework_paths),
        "changed_position_count": len(changes),
        "changed_positions": changes,
    }
