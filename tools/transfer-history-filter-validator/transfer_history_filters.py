"""Validate saved transfer history filters against a supplied product list."""

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
import json
from pathlib import Path
import sys

MIN_HISTORY_YEAR = 2020
MAX_HISTORY_YEAR = 2100
MAX_HISTORY_PAGE = 1000
MAX_HISTORY_PAGE_SIZE = 100


class FilterValidationError(ValueError):
    """Raised when a saved filter is outside the transfer history contract."""


@dataclass(frozen=True)
class Product:
    canonical_modality: str
    display_modality: str


def normalize_product_aliases(
    values: Iterable[str] | None,
    products: tuple[Product, ...],
) -> tuple[Product, ...]:
    """Accept canonical or display names and return a unique controlled scope."""

    aliases = {
        alias: product
        for product in products
        for alias in (product.canonical_modality, product.display_modality)
    }
    requested: list[str] = []
    for raw_value in values or ():
        requested.extend(part.strip().upper() for part in raw_value.split(","))
    requested = [value for value in requested if value]
    if not requested:
        return products

    unknown = sorted({value for value in requested if value not in aliases})
    if unknown:
        raise FilterValidationError(
            "Unsupported product alias: " + ", ".join(unknown)
        )
    selected = {aliases[value].display_modality for value in requested}
    return tuple(
        product for product in products if product.display_modality in selected
    )


def validate_history_filters(
    year: int,
    modalities: Iterable[str] | None,
    page: int,
    page_size: int,
    *,
    products: tuple[Product, ...],
) -> tuple[int, tuple[Product, ...], int, int]:
    if year < MIN_HISTORY_YEAR or year > MAX_HISTORY_YEAR:
        raise FilterValidationError(
            f"Transfer history year must be between {MIN_HISTORY_YEAR} and {MAX_HISTORY_YEAR}."
        )
    if page < 1 or page > MAX_HISTORY_PAGE:
        raise FilterValidationError(
            "Transfer history page must be between 1 and 1000."
        )
    if page_size < 1 or page_size > MAX_HISTORY_PAGE_SIZE:
        raise FilterValidationError(
            "Transfer history page_size must be between 1 and 100."
        )
    return year, normalize_product_aliases(modalities, products), page, page_size


def load_products(path: Path) -> tuple[Product, ...]:
    rows = json.loads(path.read_bytes())
    if not isinstance(rows, list) or not rows:
        raise FilterValidationError("The product list must be a non-empty JSON array.")
    products = []
    aliases = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"canonical_modality", "display_modality"}:
            raise FilterValidationError("Each product must declare a canonical and display alias.")
        keys = tuple(row[name] for name in ("canonical_modality", "display_modality"))
        if any(
            not isinstance(key, str) or not key or key != key.strip().upper() or "," in key
            for key in keys
        ):
            raise FilterValidationError("Product aliases must be uppercase, non-empty and comma-free.")
        if aliases.intersection(keys):
            raise FilterValidationError("Product aliases must be unique across products.")
        aliases.update(keys)
        products.append(Product(*keys))
    return tuple(products)


def load_request(path: Path) -> dict:
    payload = json.loads(path.read_bytes())
    required = {"year", "page", "page_size"}
    if not isinstance(payload, dict) or not required <= payload.keys() <= required | {"modalities"}:
        raise FilterValidationError("A filter request must declare year, page and page_size.")
    if any(type(payload[key]) is not int for key in required):
        raise FilterValidationError("Year, page and page_size must be integers.")
    modalities = payload.get("modalities")
    if modalities is not None and (
        not isinstance(modalities, list) or any(not isinstance(value, str) for value in modalities)
    ):
        raise FilterValidationError("Modalities must be a list of strings or null.")
    return {**payload, "modalities": modalities}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filters", type=Path, help="Saved filter request in JSON")
    parser.add_argument("--products", type=Path, required=True, help="Approved product aliases in JSON")
    args = parser.parse_args()
    try:
        year, selected, page, page_size = validate_history_filters(
            **load_request(args.filters), products=load_products(args.products)
        )
    except FilterValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print("Could not read a valid JSON input.", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "PASS",
        "year": year,
        "page": page,
        "page_size": page_size,
        "modalities": [product.display_modality for product in selected],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
