import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.flows import parse_account_selection


class TestAccountSelection(unittest.TestCase):
    def test_replace_by_indices_and_commas(self):
        selected, _ = parse_account_selection("1,3,5", 6, set(range(6)))
        self.assertEqual(selected, {0, 2, 4})

    def test_range_support(self):
        selected, _ = parse_account_selection("2-4", 6, set())
        self.assertEqual(selected, {1, 2, 3})

    def test_all_and_invert(self):
        selected, _ = parse_account_selection("a", 4, {1})
        self.assertEqual(selected, {0, 1, 2, 3})
        selected, _ = parse_account_selection("i", 4, {0, 1})
        self.assertEqual(selected, {2, 3})

    def test_add_and_remove(self):
        selected, _ = parse_account_selection("+2 +4", 5, {0})
        self.assertEqual(selected, {0, 1, 3})
        selected, _ = parse_account_selection("-1,3", 5, {0, 1, 2, 3})
        self.assertEqual(selected, {1, 3})

    def test_cancel(self):
        selected, action = parse_account_selection("q", 3, {0, 1, 2})
        self.assertIsNone(selected)
        self.assertEqual(action, "cancel")


if __name__ == "__main__":
    unittest.main()

