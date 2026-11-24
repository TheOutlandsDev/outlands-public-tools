"""Validate and normalize a saved work-in-progress filter request."""

import argparse
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import json
from math import isfinite
from pathlib import Path
import re
import sys


MAX_REQUEST_BYTES = 1024 * 1024
MAX_WIP_PAGE = 1000
MAX_WIP_PAGE_SIZE = 100
MAX_WIP_SEARCH_LENGTH = 80


class WIPFilterError(ValueError):
    """The saved WIP request does not meet the filter contract."""


@dataclass(frozen=True)
class ProductAlias:
    canonical_modality: str
    display_modality: str


def normalize_wip_modalities(
    values: Iterable[str] | None, *, products: tuple[ProductAlias, ...],
) -> tuple[ProductAlias, ...]:
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

    if any(value not in aliases for value in requested):
        raise WIPFilterError("Unsupported WIP modality.")
    selected = {aliases[value].display_modality for value in requested}
    return tuple(
        product for product in products if product.display_modality in selected
    )


def normalize_wip_search(value: str | None) -> str | None:
    """Normalize a bounded literal search without treating it as SQL syntax."""

    normalized = (value or "").strip()
    if not normalized:
        return None
    if len(normalized) > MAX_WIP_SEARCH_LENGTH:
        raise WIPFilterError(
            "WIP search must be 80 characters or fewer."
        )
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise WIPFilterError(
            "WIP search contains a control character."
        )
    return normalized


def validate_wip_pagination(page: int, page_size: int) -> tuple[int, int]:
    if page < 1 or page > MAX_WIP_PAGE:
        raise WIPFilterError(
            "WIP page must be between 1 and 1000."
        )
    if page_size < 1 or page_size > MAX_WIP_PAGE_SIZE:
        raise WIPFilterError(
            "WIP page_size must be between 1 and 100."
        )
    return page, page_size


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WIPFilterError("The request contains a duplicate JSON field.")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise WIPFilterError("The request contains a nonfinite JSON value.")


def _finite_float(value):
    number = float(value)
    if not isfinite(number):
        _invalid_constant(value)
    return number


def _load_request(path: Path) -> object:
    try:
        if not path.is_file():
            raise WIPFilterError("The request must be a readable file.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_REQUEST_BYTES + 1)
    except OSError as exc:
        raise WIPFilterError("The request could not be read.") from exc
    if len(raw) > MAX_REQUEST_BYTES:
        raise WIPFilterError("The request exceeds the 1 MiB input limit.")
    try:
        return json.loads(raw.decode("utf-8-sig"),
                          object_pairs_hook=_unique_fields, parse_constant=_invalid_constant,
                          parse_float=_finite_float)
    except WIPFilterError:
        raise
    except (ValueError, RecursionError) as exc:
        raise WIPFilterError("The request is not valid JSON.") from exc


def _validate_products(rows: object) -> tuple[ProductAlias, ...]:
    if not isinstance(rows, list) or not rows:
        raise WIPFilterError("The request requires a nonempty products array.")
    products = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.keys() != {"canonical_modality", "display_modality"}:
            raise WIPFilterError("Each product requires a canonical and a display modality.")
        names = (row["canonical_modality"], row["display_modality"])
        if any(not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", value) for value in names):
            raise WIPFilterError("Product aliases must use uppercase letters, digits, underscores, or hyphens.")
        if seen.intersection(names):
            raise WIPFilterError("A product alias is shared by multiple products.")
        seen.update(names)
        products.append(ProductAlias(*names))
    return tuple(products)


def validate_filter(request: object) -> dict[str, object]:
    if (not isinstance(request, dict) or "products" not in request
            or not request.keys() <= {"products", "modalities", "search", "page", "page_size"}):
        raise WIPFilterError("The request has an invalid filter schema.")
    products = _validate_products(request["products"])
    modalities = request.get("modalities")
    search = request.get("search")
    page = request.get("page", 1)
    page_size = request.get("page_size", 50)
    if modalities is not None and (
        not isinstance(modalities, list) or any(not isinstance(value, str) for value in modalities)
    ):
        raise WIPFilterError("Modalities must be an array of strings or null.")
    if search is not None and not isinstance(search, str):
        raise WIPFilterError("Search must be text or null.")
    if type(page) is not int or type(page_size) is not int:
        raise WIPFilterError("Page and page_size must be integers.")

    selected = normalize_wip_modalities(modalities, products=products)
    normalized_search = normalize_wip_search(search)
    page, page_size = validate_wip_pagination(page, page_size)
    return {
        "selected_products": [asdict(product) for product in selected],
        "search": normalized_search,
        "page": page,
        "page_size": page_size,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("request", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_filter(_load_request(args.request))
    except WIPFilterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
