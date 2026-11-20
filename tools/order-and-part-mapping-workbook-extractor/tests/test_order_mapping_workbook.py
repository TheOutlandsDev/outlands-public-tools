"""Adapted order, mapping, type, and hash checks from the original workbook tests."""

from datetime import date
from hashlib import sha256

import pytest

from examples.make_orders import make_orders
import order_mapping_workbook as extractor


def test_fictional_workbook_produces_typed_orders_and_mappings_without_mutation(tmp_path):
    path = tmp_path / "orders.xlsx"
    make_orders(path)
    before = sha256(path.read_bytes()).hexdigest()
    customer, panel, mappings = extractor.extract(path, before)
    assert sha256(path.read_bytes()).hexdigest() == before
    assert (len(customer), len(panel), len(mappings)) == (118, 2, 9)
    assert isinstance(customer[0], extractor.PTLAOrderRecord)
    assert isinstance(panel[0], extractor.PTLAOrderRecord)
    assert isinstance(mappings[0], extractor.PTLAMappingRecord)
    assert (customer[0].source_sheet, panel[0].source_sheet, mappings[0].source_sheet) == ("C", "P", "Mapping")
    assert customer[0].source_row == panel[0].source_row == mappings[0].source_row == 4
    assert customer[0].lead_time_calculation == date(2030, 9, 13)
    assert any(order.lead_time_calculation == "#REF!" for order in customer)


def test_checksum_mismatch_fails_before_workbook_parsing(tmp_path, monkeypatch):
    path = tmp_path / "orders.xlsx"
    make_orders(path)
    expected = sha256(path.read_bytes()).hexdigest()
    with path.open("ab") as stream:
        stream.write(b"fictional change")

    def unexpected(_content):
        pytest.fail("Workbook parsing must not run before the checksum passes")

    monkeypatch.setattr(extractor, "inspect_workbook", unexpected)
    with pytest.raises(extractor.PTLAInputHashMismatch, match="checksum gate"):
        extractor.extract(path, expected)
