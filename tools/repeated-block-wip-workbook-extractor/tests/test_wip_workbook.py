"""Original WIP type, count, source integrity, and checksum-first assertions."""

from hashlib import sha256

import pytest

from examples.make_inventory import make_inventory
from wip_supply import FPCWIPRecord
import wip_workbook


def test_fictional_workbook_produces_typed_wip_without_mutation(tmp_path):
    path = tmp_path / "inventory.xlsx"
    make_inventory(path)
    before = sha256(path.read_bytes()).hexdigest()
    records = wip_workbook.extract(path, before, expected_count=131)
    assert sha256(path.read_bytes()).hexdigest() == before
    assert len(records) == 131
    assert isinstance(records[0], FPCWIPRecord)
    assert records[0].source_row == 5
    assert records[0].material_name == "DEMO-LOT-001"
    assert records[-1].material_name == "DEMO-LOT-131"


def test_checksum_mismatch_fails_before_workbook_parsing(tmp_path, monkeypatch):
    path = tmp_path / "inventory.xlsx"
    make_inventory(path)
    expected = sha256(path.read_bytes()).hexdigest()
    with path.open("ab") as stream:
        stream.write(b"fictional change")

    def unexpected(_content):
        pytest.fail("Workbook parsing must not run before the checksum passes")

    monkeypatch.setattr(wip_workbook, "inspect_workbook", unexpected)
    with pytest.raises(wip_workbook.PTLAInputHashMismatch, match="checksum gate"):
        wip_workbook.extract(path, expected)
