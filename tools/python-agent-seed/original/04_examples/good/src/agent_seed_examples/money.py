"""Small Decimal example for exact invoice arithmetic."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


_CENTS = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class InvoiceLine:
    """One line item in an invoice."""

    description: str
    quantity: int
    unit_price: Decimal

    def subtotal(self) -> Decimal:
        """Return the rounded line subtotal."""
        if self.quantity < 0:
            raise ValueError("quantity must not be negative")
        if self.unit_price < 0:
            raise ValueError("unit_price must not be negative")
        return (self.unit_price * self.quantity).quantize(_CENTS, rounding=ROUND_HALF_UP)


def invoice_total(lines: list[InvoiceLine]) -> Decimal:
    """Return the rounded total for invoice lines."""
    return sum((line.subtotal() for line in lines), Decimal("0.00")).quantize(_CENTS, rounding=ROUND_HALF_UP)
