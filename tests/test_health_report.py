import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# 允许从根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.flows import generate_resource_health_report

class TestHealthReport(unittest.TestCase):
    def setUp(self):
        self.test_root = tempfile.mkdtemp(prefix="cep_test_health_")
        self.assets_dir = os.path.join(self.test_root, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    @patch("comprehensive_eval_pro.flows.os.path.dirname")
    @patch("comprehensive_eval_pro.flows.ProTaskManager")
    def test_generate_report_with_missing_resources(self, mock_tm_class, mock_dirname):
        """
        验证资源体检报告能正确识别缺失的资源。
        """
        # 模拟 flows.py 所在的目录，使其指向我们的测试目录
        mock_dirname.return_value = self.test_root
        
        # 模拟两个账号，属于不同的班级
        mock_tm1 = MagicMock()
        mock_tm1._school_name.return_value = "测试学校"
        mock_tm1._grade_name.return_value = "高一"
        mock_tm1._pure_class_name.return_value = "一班"
        # 模拟一班资源状况
        mock_tm1.check_resource_health.return_value = {
            "labor": True,
            "military": False,
            "class_meeting_img": False,
            "class_meeting_record": False
        }
        
        mock_tm2 = MagicMock()
        mock_tm2._school_name.return_value = "测试学校"
        mock_tm2._grade_name.return_value = "高一"
        mock_tm2._pure_class_name.return_value = "二班"
        # 模拟二班资源状况
        mock_tm2.check_resource_health.return_value = {
            "labor": False,
            "military": False,
            "class_meeting_img": False,
            "class_meeting_record": False
        }
        
        prepared_accounts = [
            {"username": "user1", "status": "已就绪", "task_mgr": mock_tm1},
            {"username": "user2", "status": "已就绪", "task_mgr": mock_tm2},
            {"username": "user3", "status": "登录失败", "task_mgr": None}
        ]
        
        # 准备资源：给一班准备劳动图片，二班什么都不准备
        # 模拟 ProTaskManager._sanitize_path_component
        def mock_sanitize(text):
            return text
        mock_tm_class._sanitize_path_component.side_effect = mock_sanitize
        mock_tm_class.IMAGE_EXTS = ('.jpg', '.png')

        ld_dir_1 = os.path.join(self.assets_dir, "劳动", "测试学校", "高一", "一班")
        os.makedirs(ld_dir_1, exist_ok=True)
        with open(os.path.join(ld_dir_1, "test.jpg"), "w") as f:
            f.write("image data")
            
        # 捕获标准输出以验证报告内容
        from io import StringIO
        saved_stdout = sys.stdout
        try:
            out = StringIO()
            sys.stdout = out
            generate_resource_health_report(prepared_accounts)
            report_text = out.getvalue()
        finally:
            sys.stdout = saved_stdout

        # 验证报告中包含预期的信息
        self.assertIn("资源体检报告", report_text)
        self.assertIn("测试学校", report_text)
        self.assertIn("高一", report_text)
        self.assertIn("一班", report_text)
        self.assertIn("二班", report_text)
        
        # 检查 ✅ 和 ❌
        # 一班劳动应该是 ✅，二班劳动应该是 ❌
        # 注意：由于对齐原因，匹配逻辑可能需要更精确
        lines = report_text.splitlines()
        line_1 = [l for l in lines if "一班" in l][0]
        line_2 = [l for l in lines if "二班" in l][0]
        
        self.assertIn("✅", line_1) # 劳动
        self.assertIn("❌", line_2) # 劳动均缺失

if __name__ == "__main__":
    unittest.main()
