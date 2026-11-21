from pathlib import Path

import pytest

from transfer_history_filters import FilterValidationError, load_products, validate_history_filters

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_history_filters_are_bounded_to_controlled_modalities() -> None:
    approved = load_products(EXAMPLES / "products.json")
    year, products, page, page_size = validate_history_filters(
        2026, ("LUMEN01", "ORBIT02"), 1, 100, products=approved
    )
    assert year == 2026
    assert [item.display_modality for item in products] == ["LUMEN01", "ORBIT02"]
    assert (page, page_size) == (1, 100)
    with pytest.raises(FilterValidationError, match="year"):
        validate_history_filters(2019, (), 1, 50, products=approved)
    with pytest.raises(FilterValidationError, match="Unsupported"):
        validate_history_filters(2026, ("UNLISTED",), 1, 50, products=approved)
