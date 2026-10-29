import unittest
from age_validator import is_valid_age

class TestAgeValidator(unittest.TestCase):
    def test_minor_rejected(self):
        self.assertFalse(is_valid_age(17))
        self.assertFalse(is_valid_age(10))

    def test_exact_eighteen_boundary(self):
        # 18 is of legal age and MUST return True
        self.assertTrue(is_valid_age(18))

    def test_adult_accepted(self):
        self.assertTrue(is_valid_age(25))

    def test_invalid_negative(self):
        self.assertFalse(is_valid_age(-5))

if __name__ == "__main__":
    unittest.main()
