import unittest
from discount_service import calculate_discount

class TestDiscountService(unittest.TestCase):
    def test_regular_tier_no_discount(self):
        self.assertEqual(calculate_discount(100.0, "REGULAR"), 100.0)

    def test_gold_tier_ten_percent(self):
        self.assertAlmostEqual(calculate_discount(100.0, "GOLD"), 90.0)

    def test_vip_tier_twenty_percent(self):
        # 20% of 100 is 20 -> expected 80.0
        self.assertAlmostEqual(calculate_discount(100.0, "VIP"), 80.0)

    def test_vip_tier_cap_at_fifty(self):
        # 20% of 500 is 100, capped at 50 -> expected 450.0
        self.assertAlmostEqual(calculate_discount(500.0, "VIP"), 450.0)

if __name__ == "__main__":
    unittest.main()
