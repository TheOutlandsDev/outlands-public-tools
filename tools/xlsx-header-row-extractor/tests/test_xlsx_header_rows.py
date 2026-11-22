import inspect

import xlsx_header_rows as analytical_seed


def test_sheet_reader_handles_streaming_workbooks_without_cached_dimensions() -> None:
    source = inspect.getsource(analytical_seed._sheet_rows)
    assert "calculate_dimension(force=True)" in source
