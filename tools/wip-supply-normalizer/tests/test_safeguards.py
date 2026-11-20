"""Focused regressions for exact rounding, duplicate rows, and saved input."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from wip_supply import (
    FPCWIPRecord,
    WIPNormalizationConfiguration,
    WIPPreparationError,
    prepare_wip_supply,
)


CLI = Path(__file__).resolve().parents[1] / "wip_supply.py"
CONFIGURATION = {
    "early_stage_steps": ["Fictional_Cut"],
    "early_stage_loss_rate": "0.25",
}


def _record() -> dict[str, str | int]:
    return {
        "source_row": 5,
        "material_name": "Fictional-Lot-01",
        "step_name": "Fictional_Cut",
        "product_name": "Fictional-Part-01",
        "wip_quantity": 2,
        "packaging_quantity": 2,
        "qa_far_quantity": 3,
        "pack_and_ship_quantity": 4,
    }


def test_exact_half_tie_rounds_up() -> None:
    record = FPCWIPRecord.model_validate(_record())
    configuration = WIPNormalizationConfiguration.model_validate(CONFIGURATION)

    result = prepare_wip_supply((record,), configuration)

    assert result.records[0].yield_loss_quantity == 1
    assert result.records[0].quantity_in_process == 1
    assert result.yield_loss_total == 1


def test_duplicate_source_row_fails_closed() -> None:
    first = FPCWIPRecord.model_validate(_record())
    second = FPCWIPRecord.model_validate(
        {**_record(), "material_name": "Fictional-Lot-02"}
    )
    configuration = WIPNormalizationConfiguration.model_validate(CONFIGURATION)

    with pytest.raises(WIPPreparationError, match="duplicate WIP source row"):
        prepare_wip_supply((first, second), configuration)


def _sha256(value: object) -> str:
    canonical_json = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(canonical_json.encode("utf-8")).hexdigest()


def test_repeated_cli_runs_preserve_totals_hashes_and_input(tmp_path: Path) -> None:
    second = {
        "source_row": 6,
        "material_name": "Fictional-Lot-02",
        "step_name": "Fictional_Inspection",
        "product_name": "Fictional-Part-02",
        "wip_quantity": 8,
    }
    payload = {"configuration": CONFIGURATION, "records": [_record(), second]}
    original = (json.dumps(payload, indent=2) + "\n").encode("utf-8")
    input_file = tmp_path / "fictional-wip.json"
    input_file.write_bytes(original)
    command = [sys.executable, "-I", "-B", str(CLI), "--input", str(input_file)]

    first = subprocess.run(command, check=False, capture_output=True, timeout=30)
    repeated = subprocess.run(command, check=False, capture_output=True, timeout=30)

    assert first.returncode == repeated.returncode == 0
    assert first.stderr == repeated.stderr == b""
    assert first.stdout == repeated.stdout
    assert input_file.read_bytes() == original
    assert list(tmp_path.iterdir()) == [input_file]
    report = json.loads(first.stdout)
    assert report["status"] == "normalized"
    assert report["input_record_count"] == 2
    assert report["affected_record_count"] == 1
    assert report["zero_or_blank_wip_count"] == 0
    assert report["raw_wip_total"] == 10
    assert report["normalized_wip_total"] == 9
    assert report["yield_loss_total"] == 1
    assert report["completed_total"] == 9
    assert [row["source_row"] for row in report["records"]] == [5, 6]
    assert report["row_set_sha256"] == _sha256(report["records"])
    assert report["configuration_sha256"] == _sha256(CONFIGURATION)
