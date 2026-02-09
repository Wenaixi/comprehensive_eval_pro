import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager


class TestMeetingFolderMatch(unittest.TestCase):
    def _make_folder_with_res(self, base, name):
        path = os.path.join(base, name)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "a.jpg"), "wb") as f:
            f.write(b"0")
        return path

    def test_match_by_quoted_title_best_similarity(self):
        mgr = ProTaskManager(token="dummy", base_url="http://example.com")
        with tempfile.TemporaryDirectory() as d:
            base_dir = os.path.join(d, "主题班会")
            os.makedirs(base_dir, exist_ok=True)
            f1 = "2025.9.29高一（8）班《百年薪火传，青春报国时》"
            f2 = "2025.9.29高一（8）班《百年薪火传青春报国时》"
            f3 = "2025.9.29高一（8）班《法制教育》"
            self._make_folder_with_res(base_dir, f2)
            self._make_folder_with_res(base_dir, f3)
            self._make_folder_with_res(base_dir, f1)

            task_name = "主题班会：2025.9.29高一（8）班《百年薪火传，青春报国时》"
            matched = mgr._find_best_matching_folder(task_name, base_dir)
            self.assertTrue(matched.endswith(f1))

    def test_match_by_double_quotes(self):
        mgr = ProTaskManager(token="dummy", base_url="http://example.com")
        with tempfile.TemporaryDirectory() as d:
            base_dir = os.path.join(d, "主题班会")
            os.makedirs(base_dir, exist_ok=True)
            f1 = "2025.9.8高一(1)班《消防安全》"
            f2 = "2025.9.8高一(1)班《法制教育》"
            self._make_folder_with_res(base_dir, f1)
            self._make_folder_with_res(base_dir, f2)

            task_name = '高一(1)班"消防安全"'
            matched = mgr._find_best_matching_folder(task_name, base_dir)
            self.assertTrue(matched.endswith(f1))


if __name__ == "__main__":
    unittest.main()

