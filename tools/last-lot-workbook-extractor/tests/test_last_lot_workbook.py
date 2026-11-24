from zipfile import ZipFile

import pytest

from examples.make_workbook import make_workbook
from last_lot_workbook import LastLotWorkbookError, load_last_lot_contract


def save(workbook, path):
    try:
        workbook.save(path)
    finally:
        workbook.close()
    return path


def test_fictional_rows_preserve_order_and_normalize_text(tmp_path):
    path = save(make_workbook(), tmp_path / "fictional.xlsx")
    original = path.read_bytes()
    rows = load_last_lot_contract(path)
    assert len(rows) == 21
    assert [row.prefix for row in rows] == [f"DEMO-{number:02d}-" for number in range(1, 22)]
    assert rows[0].model_dump() == {
        "product": "DEMO-ITEM-01",
        "material_template": "Fictional Template 01",
        "prefix": "DEMO-01-",
        "last_lot_started": "DEMO-01-AAAZ",
        "next_lot_to_start": "DEMO-01-AABA",
    }
    assert rows[1].product is None and rows[1].material_template is None
    assert path.read_bytes() == original


def test_one_sheet_and_an_explicit_custom_name(tmp_path):
    path = save(make_workbook("Fictional Ledger"), tmp_path / "custom.xlsx")
    with pytest.raises(LastLotWorkbookError, match="only the selected"):
        load_last_lot_contract(path)
    assert len(load_last_lot_contract(path, sheet_name="Fictional Ledger")) == 21

    workbook = make_workbook()
    workbook.create_sheet("Extra")
    extra = save(workbook, tmp_path / "extra.xlsx")
    with pytest.raises(LastLotWorkbookError, match="only the selected"):
        load_last_lot_contract(extra)


def test_headers_keep_the_original_normalization_case_and_blank_column(tmp_path):
    workbook = make_workbook()
    workbook.active["A2"] = "  Product    Group  "
    assert len(load_last_lot_contract(save(workbook, tmp_path / "spaces.xlsx"))) == 21

    for cell, value in (("A2", "product group"), ("E2", "Extra header")):
        workbook = make_workbook()
        workbook.active[cell] = value
        path = save(workbook, tmp_path / f"{cell}.xlsx")
        with pytest.raises(LastLotWorkbookError, match="headers changed"):
            load_last_lot_contract(path)


def test_row_count_and_fixed_table_boundary(tmp_path):
    workbook = make_workbook()
    workbook.active["C24"] = "OUTSIDE-TABLE-"
    path = save(workbook, tmp_path / "with-footer.xlsx")
    assert len(load_last_lot_contract(path)) == 21

    workbook = make_workbook()
    workbook.active["C23"] = "  "
    workbook.active["C24"] = "OUTSIDE-TABLE-"
    incomplete = save(workbook, tmp_path / "incomplete.xlsx")
    with pytest.raises(LastLotWorkbookError, match="record count changed"):
        load_last_lot_contract(incomplete)


def test_duplicate_prefix_is_rejected_after_normalization(tmp_path):
    workbook = make_workbook()
    workbook.active["C4"] = "   DEMO-01- "
    path = save(workbook, tmp_path / "duplicate-prefix.xlsx")
    with pytest.raises(LastLotWorkbookError, match="prefix is not unique"):
        load_last_lot_contract(path)


def test_duplicate_last_and_next_lot_values_are_rejected(tmp_path):
    for column, field in (("D", "last_lot_started"), ("F", "next_lot_to_start")):
        workbook = make_workbook()
        workbook.active[f"{column}4"] = workbook.active[f"{column}3"].value
        path = save(workbook, tmp_path / f"duplicate-{column}.xlsx")
        with pytest.raises(LastLotWorkbookError, match=f"{field} is not unique"):
            load_last_lot_contract(path)


def test_invalid_xlsx_and_macro_package_are_rejected(tmp_path):
    unreadable = tmp_path / "unreadable.xlsx"
    unreadable.write_bytes(b"not an XLSX")
    with pytest.raises(LastLotWorkbookError, match="not a readable XLSX"):
        load_last_lot_contract(unreadable)
    path = save(make_workbook(), tmp_path / "macro.xlsx")
    with ZipFile(path, "a") as workbook:
        workbook.writestr("xl/vbaProject.bin", b"fictional macro part")
    with pytest.raises(LastLotWorkbookError, match="Macro-enabled"):
        load_last_lot_contract(path)
