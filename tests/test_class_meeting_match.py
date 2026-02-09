import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager
from comprehensive_eval_pro import main as app_main


class TestClassMeetingMatch(unittest.TestCase):
    def test_task_manager_match_explicit_banhui(self):
        self.assertTrue(ProTaskManager._looks_like_class_meeting("主题班会：消防安全", "数学"))

    def test_task_manager_match_ban_title_in_moral_dimension(self):
        self.assertTrue(ProTaskManager._looks_like_class_meeting("高一(1)班《消防安全》", "德育"))
        self.assertTrue(ProTaskManager._looks_like_class_meeting("高一(1)班“消防安全”", "思想品德"))

    def test_task_manager_not_match_ban_title_in_academic_dimension(self):
        self.assertFalse(ProTaskManager._looks_like_class_meeting("高一(1)班《数学作业》", "数学"))

    def test_main_y_special_includes_class_meeting(self):
        t = {"name": "高一(1)班《消防安全》", "dimensionName": "德育"}
        self.assertTrue(app_main._is_y_special_task(t))

    def test_main_not_class_meeting_for_generic_class_text(self):
        t = {"name": "班级卫生打扫", "dimensionName": "劳动"}
        self.assertFalse(app_main._looks_like_class_meeting(t))


if __name__ == "__main__":
    unittest.main()

