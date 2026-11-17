from __future__ import annotations

from decimal import Decimal
from unittest import TestCase

from agent_seed_examples.money import InvoiceLine, invoice_total


class MoneyTests(TestCase):
    def test_invoice_total_uses_decimal_rounding(self) -> None:
        lines = [
            InvoiceLine("sensor", 1, Decimal("19.995")),
            InvoiceLine("cable", 1, Decimal("5.00")),
        ]
        self.assertEqual(invoice_total(lines), Decimal("25.00"))

    def test_rejects_negative_quantity(self) -> None:
        with self.assertRaises(ValueError):
            InvoiceLine("bad", -1, Decimal("1.00")).subtotal()
