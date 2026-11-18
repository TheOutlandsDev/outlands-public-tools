"""Build bound parameters for the fictional report detail query.

This module only prepares SQL text and positional parameters. It does not open
a database connection or execute the query.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import date, datetime
from pathlib import Path


_TEMPLATE_PATH = Path(__file__).with_name("detail_pyodbc.sql")
_PRODUCT_MARKER = "/*PRODUCT_PARAMETERS*/"
_MAX_SQL_SERVER_PARAMETERS = 2_100
_DATE_PARAMETER_COUNT = 2


def _calendar_date(value: date | datetime, name: str) -> date:
    if not isinstance(value, date):
        raise TypeError(f"{name} must be a Python date or datetime")
    return value.date() if isinstance(value, datetime) else value


def _product_placeholders(template: str, count: int) -> str:
    if template.count(_PRODUCT_MARKER) != 1:
        raise ValueError("Product parameter marker must appear exactly once")
    return template.replace(_PRODUCT_MARKER, ", ".join("?" for _ in range(count)))


def build_detail_query(
    *,
    start_date: date | datetime,
    end_date: date | datetime,
    selected_products: Sequence[str],
    product_options: Collection[str],
) -> tuple[str, tuple[date | datetime | str, ...]]:
    """Return the fictional detail SQL and ordered pyodbc parameters.

    ``product_options`` must come from a saved, validated DataSet2 options
    artifact. The bundled SQL uses fictional tables.
    """

    start_day = _calendar_date(start_date, "start_date")
    end_day = _calendar_date(end_date, "end_date")
    if end_day < start_day:
        raise ValueError("end_date must be on or after start_date")

    if isinstance(selected_products, (str, bytes)) or not isinstance(selected_products, Sequence):
        raise TypeError("selected_products must be a sequence of product names")
    products = tuple(selected_products)
    if not products:
        raise ValueError("Select at least one product")
    if len(products) + _DATE_PARAMETER_COUNT > _MAX_SQL_SERVER_PARAMETERS:
        raise ValueError("At most 2098 products fit with two date parameters")
    if any(not isinstance(product, str) or not product.strip() for product in products):
        raise ValueError("Each selected product must be a nonempty string")
    if len(set(products)) != len(products):
        raise ValueError("Selected products must be unique")

    if isinstance(product_options, (str, bytes)) or not isinstance(product_options, Collection):
        raise TypeError("product_options must be a collection of DataSet2 product names")
    options = set(product_options)
    if any(not isinstance(option, str) for option in options):
        raise ValueError("DataSet2 product options must be strings")
    unknown = [product for product in products if product not in options]
    if unknown:
        raise ValueError("Selected product is absent from DataSet2 options")

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    sql = _product_placeholders(template, len(products))
    return sql, (start_date, end_date, *products)
