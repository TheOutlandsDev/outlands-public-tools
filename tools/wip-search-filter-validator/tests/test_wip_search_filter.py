import json
from pathlib import Path

import pytest

from wip_search_filter import ProductAlias, WIPFilterError, normalize_wip_modalities, normalize_wip_search


FIXTURE = Path(__file__).resolve().parents[1] / "examples/fictional-filter.json"
PRODUCTS = tuple(ProductAlias(**row) for row in json.loads(FIXTURE.read_bytes())["products"])


def test_wip_scope_accepts_only_five_contract_products() -> None:
    selected = normalize_wip_modalities(
        ["DEMO-A", "VIEW-B, DEMO-C", "DEMO-D", "VIEW-E", "DEMO-A"], products=PRODUCTS
    )

    assert [item.display_modality for item in selected] == [
        "VIEW-A",
        "VIEW-B",
        "VIEW-C",
        "VIEW-D",
        "VIEW-E",
    ]
    with pytest.raises(WIPFilterError, match="Unsupported"):
        normalize_wip_modalities(["UNKNOWN"], products=PRODUCTS)


def test_wip_search_is_bounded_and_treats_empty_as_unset() -> None:
    assert normalize_wip_search("  DEMO-LOT-001  ") == "DEMO-LOT-001"
    assert normalize_wip_search("  ") is None
    with pytest.raises(WIPFilterError, match="80"):
        normalize_wip_search("x" * 81)
    with pytest.raises(WIPFilterError, match="control"):
        normalize_wip_search("bad\nsearch")
