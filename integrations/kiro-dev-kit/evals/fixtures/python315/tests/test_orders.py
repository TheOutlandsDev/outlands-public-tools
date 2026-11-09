import unittest
from inventory import available
from orders import can_fulfill

class OrderTests(unittest.TestCase):
    def test_exact_available_quantity(self):
        self.assertTrue(can_fulfill(5, 2, 3))

    def test_partial_and_excess(self):
        self.assertTrue(can_fulfill(5, 2, 2))
        self.assertFalse(can_fulfill(5, 2, 4))

    def test_reservations_and_empty_order(self):
        self.assertEqual(available(2, 5), 0)
        self.assertFalse(can_fulfill(2, 5, 1))
        self.assertTrue(can_fulfill(2, 5, 0))

    def test_invalid_input(self):
        for values in [(-1, 0, 1), (1, -1, 1), (1, 0, -1)]:
            with self.assertRaises(ValueError):
                can_fulfill(*values)

if __name__ == "__main__":
    unittest.main()
