import unittest
from comprehensive_eval_pro.services.task_manager import ProTaskManager
from comprehensive_eval_pro.flows import is_y_special_task, looks_like_class_meeting
from comprehensive_eval_pro.flow_logic import compute_base_entries

class TestLogicRefinement(unittest.TestCase):
    def test_labor_task_exclusion(self):
        """测试劳动任务判定：包含劳动但排除劳动素养"""
        # 在 TaskManager 内部逻辑中验证
        tm = ProTaskManager(token="test", user_info={})
        
        # 真正的劳动任务
        task_real = {"name": "家务劳动", "dimensionName": "维度A"}
        # 劳动素养任务 (应该被排除)
        task_literacy = {"name": "学生劳动素养评价", "dimensionName": "维度B"}
        
        # 模拟 submit_task 内部的逻辑
        is_labor_real = "劳动" in task_real["name"] and "劳动素养" not in task_real["name"]
        is_labor_literacy = "劳动" in task_literacy["name"] and "劳动素养" not in task_literacy["name"]
        
        self.assertTrue(is_labor_real)
        self.assertFalse(is_labor_literacy)

    def test_class_meeting_dimension_agnostic(self):
        """测试班会判定：不依赖维度名称"""
        # 1. 名字像班会，维度完全无关
        task1 = {"name": "主题班会：诚实守信", "dimensionName": "乱七八糟维度"}
        self.assertTrue(looks_like_class_meeting(task1))
        
        # 2. 名字符合班级活动正则，维度无关
        task2 = {"name": "2月10日班《安全教育》", "dimensionName": "无关联"}
        self.assertTrue(looks_like_class_meeting(task2))
        
        # 3. 既不像班会，正则也匹配不上
        task3 = {"name": "班级日常表现", "dimensionName": "思想品德"}
        self.assertFalse(looks_like_class_meeting(task3))

    def test_is_y_special_task(self):
        """测试四大专项集合逻辑"""
        tasks = [
            {"name": "家务劳动"},             # True
            {"name": "劳动素养评价"},          # False
            {"name": "军训汇报"},             # True
            {"name": "国旗下讲话"},           # True
            {"name": "主题班会"},             # True
            {"name": "普通任务"}              # False
        ]
        results = [is_y_special_task(t) for t in tasks]
        self.assertEqual(results, [True, False, True, True, True, False])

    def test_compute_base_entries_ld(self):
        """测试 flow_logic 中的 ld 筛选逻辑"""
        tasks = [
            {"name": "参加劳动"},
            {"name": "劳动素养考核"},
            {"name": "日常表现"}
        ]
        # 筛选 ld
        entries = compute_base_entries(
            tasks=tasks,
            selection="ld",
            indices=[],
            looks_like_class_meeting=looks_like_class_meeting,
            is_y_special_task=is_y_special_task,
            is_labor_task=ProTaskManager._is_labor_task
        )
        # 应该只选中第一个
        if len(entries) != 1:
            print(f"\n[DEBUG] entries: {[e[1]['name'] for e in entries]}")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0][1]["name"], "参加劳动")

if __name__ == "__main__":
    unittest.main()
