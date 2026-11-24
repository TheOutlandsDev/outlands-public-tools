from pathlib import Path

from policy_product_parity import PolicySnapshot, _validate_configured_products, _verify_fail_closed


def example_policies():
    examples = Path(__file__).resolve().parents[1] / "examples"
    return tuple(
        PolicySnapshot.model_validate_json((examples / filename).read_bytes())
        for filename in ("baseline.json", "candidate.json")
    )


def test_all_twelve_configured_products_are_semantically_equivalent():
    legacy, candidate = example_policies()
    _validate_configured_products(legacy, candidate)
    assert len(legacy.configured_products) == len(candidate.configured_products) == 12


def test_all_eleven_unapproved_products_remain_fail_closed():
    legacy, candidate = example_policies()
    assert _verify_fail_closed(legacy, candidate) == 11
