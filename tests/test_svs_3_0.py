import unittest
from comprehensive_eval_pro.services.task_manager import ProTaskManager

class TestSVS30System(unittest.TestCase):
    def setUp(self):
        # 初始化一个基础的 TaskManager
        self.tm = ProTaskManager(token="test", user_info={})

    def test_reality_layer_similarity(self):
        """测试现实层：资源文件夹反向匹配"""
        task_name = "2025.9.29高一(8)班《百年薪火传，青春报国时》"
        # 模拟存在的文件夹（可能名字略有差异，比如少了日期或班级描述不同）
        existing = ["《百年薪火传，青春报国时》主题班会"]
        
        # 应该识别成功 (相似度 > 0.85)
        self.assertTrue(
            ProTaskManager._looks_like_class_meeting(task_name, existing_folders=existing),
            "Reality Layer should match similar folder names"
        )

    def test_semantic_layer_scoring(self):
        """测试语义层：权重评分逻辑"""
        # 场景 A: 思想品德维度 + 书名号 + 关键词 = 高分
        task_a = "《青春使命，报国志》"
        dim_a = "思想品德"
        self.assertTrue(ProTaskManager._looks_like_class_meeting(task_a, dimension_name=dim_a))

        # 场景 B: 非思想品德维度 + 书名号 + 关键词 = 可能及格
        task_b = "《网络安全教育》"
        dim_b = "其它"
        self.assertTrue(ProTaskManager._looks_like_class_meeting(task_b, dimension_name=dim_b))

        # 场景 C: 名字太短且无强特征 = 不及格
        task_c = "班级活动"
        dim_c = "思想品德"
        self.assertFalse(ProTaskManager._looks_like_class_meeting(task_c, dimension_name=dim_c))

    def test_structural_layer_regex_task_36(self):
        """测试结构层：修复 Task 36 的全角/空格排版事故"""
        # Task 36 原型：2025.9.29高一（ 8 ）班《百年薪火传，青春报国时》
        task_36 = "2025.9.29高一（ 8 ）班《百年薪火传，青春报国时》"
        dim_36 = "思想品德"
        
        self.assertTrue(
            ProTaskManager._looks_like_class_meeting(task_36, dimension_name=dim_36),
            "SVS 3.0 should recognize Task 36 with full-width brackets and spaces"
        )
        
        # 变种测试
        variants = [
            "高二(1)班班会",
            "高三  12  班主题活动",
            "高一（15）班安全教育"
        ]
        for v in variants:
            self.assertTrue(
                ProTaskManager._looks_like_class_meeting(v, dimension_name="思想品德"),
                f"Failed to recognize variant: {v}"
            )

    def test_negative_filtering_task_41(self):
        """测试黑名单：拦截非专项任务"""
        # Task 41 原型：2025-2026学年”我们不一’班‘，共赢’心‘高考“团体辅导志愿者
        task_41 = "2025-2026学年”我们不一’班‘，共赢’心‘高考“团体辅导志愿者"
        dim_41 = "思想品德"
        
        self.assertFalse(
            ProTaskManager._looks_like_class_meeting(task_41, dimension_name=dim_41),
            "SVS 3.0 should block volunteer tasks via blacklist"
        )
        
        # 其它黑名单测试
        self.assertFalse(ProTaskManager._looks_like_class_meeting("期末评价任务", "思想品德"))
        self.assertFalse(ProTaskManager._looks_like_class_meeting("学生素质考核", "思想品德"))

    def test_labor_task_recognition(self):
        """测试劳动任务识别"""
        # 场景 A: 明确的劳动动作
        self.assertTrue(ProTaskManager._is_labor_task("校园卫生大扫除", "劳动素养"))
        self.assertTrue(ProTaskManager._is_labor_task("教室保洁活动", "思想品德")) # 跨维度识别
        
        # 场景 B: 排除评价/考核
        self.assertFalse(ProTaskManager._is_labor_task("劳动素养自我评价", "劳动素养"))
        self.assertFalse(ProTaskManager._is_labor_task("志愿者服务", "劳动素养"))

if __name__ == "__main__":
    unittest.main()
