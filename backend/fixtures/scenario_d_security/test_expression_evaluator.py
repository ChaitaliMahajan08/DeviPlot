import unittest
from expression_evaluator import evaluate_user_expression

class TestExpressionEvaluator(unittest.TestCase):
    def test_evaluate_integer(self):
        self.assertEqual(evaluate_user_expression("42"), 42)

    def test_evaluate_list_literal(self):
        self.assertEqual(evaluate_user_expression("[1, 2, 3]"), [1, 2, 3])

    def test_evaluate_dict_literal(self):
        self.assertEqual(evaluate_user_expression("{'a': 1}"), {'a': 1})

if __name__ == "__main__":
    unittest.main()
