import json
from pathlib import Path

import pytest

from production_planning.flow_catalog import (
    FlowCatalogError,
    compare_flows,
    load_verified_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "flow_xml_manifest.json"
INPUTS = ROOT / "data" / "flow_xml_inputs"


def test_catalog_verifies_all_sources_and_activation_boundaries() -> None:
    catalog = load_verified_catalog(MANIFEST, INPUTS)
    assert len(catalog.manifest.sources) == 5
    assert len(catalog.documents) == 5
    assert sum(entry.active for entry in catalog.manifest.sources) == 4
    candidate = next(
        entry
        for entry in catalog.manifest.sources
        if entry.flow_name == "Demo Panel Route" and entry.flow_version == "9"
    )
    assert candidate.catalog_status == "CANDIDATE_NOT_ACTIVE"
    assert catalog.manifest.missing_fw32_xml.flow_name == "Demo Pending Route"


def test_changed_or_missing_source_fails_entire_catalog_closed(tmp_path: Path) -> None:
    source_copy = tmp_path / "sources"
    source_copy.mkdir()
    for entry in json.loads(MANIFEST.read_text())["sources"]:
        (source_copy / entry["filename"]).write_bytes(
            (INPUTS / entry["filename"]).read_bytes()
        )
    changed = source_copy / "demo-circuit-6.xml"
    changed.write_bytes(changed.read_bytes() + b" ")
    with pytest.raises(FlowCatalogError, match="does not match"):
        load_verified_catalog(MANIFEST, source_copy)
    changed.unlink()
    with pytest.raises(FlowCatalogError, match="missing or invalid"):
        load_verified_catalog(MANIFEST, source_copy)


def test_duplicate_active_version_for_same_flow_fails_closed(tmp_path: Path) -> None:
    payload = json.loads(MANIFEST.read_text())
    duplicate = dict(payload["sources"][0])
    duplicate["filename"] = "new.xml"
    duplicate["sha256"] = "0" * 64
    duplicate["flow_version"] = "8"
    payload["sources"].append(duplicate)
    candidate = tmp_path / "manifest.json"
    candidate.write_text(json.dumps(payload))
    with pytest.raises(FlowCatalogError, match="manifest is invalid"):
        load_verified_catalog(candidate, INPUTS)


def test_comparison_is_deterministic_and_bounded() -> None:
    catalog = load_verified_catalog(MANIFEST, INPUTS)
    left = catalog.documents[
        "e833e1d667cf876b095c1e68efeb7aa6650542c189b35e508ad6a3f8ffb39086"
    ]
    right = catalog.documents[
        "0994899f03db5393b94c32dec2a6853d9845ce69fa8697515759f8c82ab8885c"
    ]
    comparison = compare_flows(left, right)
    assert comparison["step_count_delta"] == 4
    assert comparison["rework_path_count_delta"] == 3
    assert comparison["changed_position_count"] <= 42
    assert all(row["changed_fields"] for row in comparison["changed_positions"])
    assert [row["position"] for row in comparison["changed_positions"]] == sorted(
        row["position"] for row in comparison["changed_positions"]
    )
