import unittest
from comprehensive_eval_pro.services.task_manager import ProTaskManager
from comprehensive_eval_pro.flows import is_y_special_task, looks_like_class_meeting

class TestTripleCheck(unittest.TestCase):
    def setUp(self):
        # 建立一个模拟环境
        self.tm = ProTaskManager(token="test_token", user_info={})

    def test_homophone_pun_exclusion(self):
        """测试：排除 Task 41 这种谐音梗志愿者任务"""
        # 模拟 Task 41 的情况
        task_41 = {
            "name": "2025-2026学年”我们不一’班‘，共赢’心‘高考“团体辅导志愿者",
            "dimensionName": "身心健康"
        }
        # 1. 验证 looks_like_class_meeting
        self.assertFalse(looks_like_class_meeting(task_41), "不应该被识别为班会")
        # 2. 验证 is_y_special_task
        self.assertFalse(is_y_special_task(task_41), "不应该被识别为四大专项")

    def test_dimension_validation(self):
        """测试：验证维度的影响力"""
        # 正确维度下的班级格式
        task_right_dim = {
            "name": "高一(8)班主题活动",
            "dimensionName": "思想品德"
        }
        self.assertTrue(looks_like_class_meeting(task_right_dim), "思想品德维度的班级活动应该是班会")

        # 错误维度下的班级格式 (非明确班会)
        task_wrong_dim = {
            "name": "高一(8)班志愿者服务",
            "dimensionName": "社会实践"
        }
        self.assertFalse(looks_like_class_meeting(task_wrong_dim), "非思想品德维度的志愿者服务不应是班会")

    def test_blacklist_filtering(self):
        """测试：黑名单关键词一票否决"""
        tasks = [
            {"name": "班会评价", "dimensionName": "思想品德"},
            {"name": "劳动考核", "dimensionName": "劳动素养"},
            {"name": "班级打卡记录", "dimensionName": "思想品德"},
            {"name": "志愿者班级服务", "dimensionName": "思想品德"},
        ]
        for t in tasks:
            with self.subTest(task_name=t["name"]):
                self.assertFalse(is_y_special_task(t), f"{t['name']} 命中黑名单，不应通过")

    def test_strict_regex(self):
        """测试：精准正则匹配，防止误伤"""
        # 真正的班会
        task_ok = {"name": "2025.1.26高一（8 ）班 学习与实践主题班会", "dimensionName": "思想品德"}
        self.assertTrue(looks_like_class_meeting(task_ok))

        # 只有“班”字且无明确班会语义的 (非思想品德维度)
        task_bad = {"name": "这个班不一般", "dimensionName": "身心健康"}
        self.assertFalse(looks_like_class_meeting(task_bad))

    def test_labor_refinement(self):
        """测试：劳动任务精细化"""
        # 真正的劳动动作
        task_real = {"name": "校园保洁活动", "dimensionName": "劳动素养"}
        self.assertTrue(is_y_special_task(task_real))

        # 劳动素养评价
        task_eval = {"name": "2025劳动素养评价", "dimensionName": "劳动素养"}
        self.assertFalse(is_y_special_task(task_eval))

if __name__ == "__main__":
    unittest.main()
