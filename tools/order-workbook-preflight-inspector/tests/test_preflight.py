"""Original unreadable-workbook rejection and fictional safeguards."""

import pytest

import workbook_preflight as preflight
from examples.make_workbook import fictional_workbook


def test_non_xlsx_content_fails_closed():
    with pytest.raises(preflight.WorkbookError, match="readable XLSX"):
        preflight.inspect_workbook(b"not a workbook")


def test_external_references_and_error_tokens_are_counted():
    report = preflight.inspect_workbook(fictional_workbook())
    assert report == preflight.WorkbookInspection(external_link_count=2, formula_error_count=2)


def test_macro_and_unsafe_path_are_refused():
    with pytest.raises(preflight.WorkbookError, match="Macro-enabled"):
        preflight.inspect_workbook(fictional_workbook({"xl/VBAProject.bin": ""}))
    with pytest.raises(preflight.WorkbookError, match="unsafe member path"):
        preflight.inspect_workbook(fictional_workbook({"../fictional.txt": ""}))


def test_declared_uncompressed_size_is_checked(monkeypatch):
    monkeypatch.setattr(preflight, "MAX_ZIP_UNCOMPRESSED_BYTES", 32)
    with pytest.raises(preflight.WorkbookError, match="expands beyond the size limit"):
        preflight.inspect_workbook(fictional_workbook())
