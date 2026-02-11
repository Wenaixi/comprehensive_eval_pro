import unittest
import os
import sys

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comprehensive_eval_pro.flows import _get_selected_accounts_display_name

class TestAccountSelectionDisplay(unittest.TestCase):
    def test_display_name_with_real_name(self):
        prepared_accounts = [
            {"username": "user1", "real_name": "张三"},
            {"username": "user2", "real_name": "李四"}
        ]
        selected = {0, 1}
        result = _get_selected_accounts_display_name(selected, prepared_accounts)
        self.assertEqual(result, "：(张三, 李四)")

    def test_display_name_with_username_fallback(self):
        prepared_accounts = [
            {"username": "user1", "real_name": ""},
            {"username": "user2", "real_name": None}
        ]
        selected = {0, 1}
        result = _get_selected_accounts_display_name(selected, prepared_accounts)
        self.assertEqual(result, "：(user1, user2)")

    def test_display_name_mixed(self):
        prepared_accounts = [
            {"username": "user1", "real_name": "张三"},
            {"username": "user2", "real_name": ""}
        ]
        selected = {0, 1}
        result = _get_selected_accounts_display_name(selected, prepared_accounts)
        self.assertEqual(result, "：(张三, user2)")

    def test_display_name_empty_selection(self):
        prepared_accounts = [
            {"username": "user1", "real_name": "张三"}
        ]
        selected = set()
        result = _get_selected_accounts_display_name(selected, prepared_accounts)
        self.assertEqual(result, "")

    def test_display_name_invalid_index(self):
        prepared_accounts = [
            {"username": "user1", "real_name": "张三"}
        ]
        selected = {0, 5} # 5 is invalid
        result = _get_selected_accounts_display_name(selected, prepared_accounts)
        self.assertEqual(result, "：(张三)")

if __name__ == "__main__":
    unittest.main()
