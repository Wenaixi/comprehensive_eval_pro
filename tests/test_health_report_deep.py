import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from io import StringIO
from pathlib import Path

# 允许从根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.flows import generate_resource_health_report
from comprehensive_eval_pro.services.task_manager import ProTaskManager

class TestHealthReportDeep(unittest.TestCase):
    """
    深度测试资源体检报告，模拟多学校、多路径、资源自愈等复杂场景。
    """
    def setUp(self):
        # 使用 realpath 避免 Windows 短路径名 (8.3) 导致的潜在问题
        self.test_root = os.path.realpath(tempfile.mkdtemp(prefix="cep_deep_test_"))
        self.assets_dir = Path(self.test_root) / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def _create_mock_tm(self, school, grade, clazz, health_dict):
        mock_tm = MagicMock()
        mock_tm._school_name.return_value = school
        mock_tm._grade_name.return_value = grade
        mock_tm._pure_class_name.return_value = clazz
        mock_tm.check_resource_health.return_value = health_dict
        return mock_tm

    def _create_dummy_image(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF") # 伪造 JPEG 头

    def _create_dummy_excel(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"PK\x03\x04") # 伪造 XLSX 头

    def _get_clean_path(self, *parts):
        """使用业务逻辑相同的清理函数构造路径"""
        clean_parts = [ProTaskManager._sanitize_path_component(p) for p in parts]
        return str(self.assets_dir.joinpath(*clean_parts))

    @patch("comprehensive_eval_pro.flows.os.path.dirname")
    def test_multi_school_resource_isolation(self, mock_dirname):
        """
        场景 1：验证多学校之间的资源隔离。
        """
        mock_dirname.return_value = self.test_root
        
        # 学校 A：福清一中 - 高一八班 (全绿)
        tm_fq = self._create_mock_tm("福清一中", "高一", "八班", {
            "labor": True, "military": True, "class_meeting_img": True, "class_meeting_record": True
        })
        
        # 学校 B：厦门一中 - 高二三班 (全红)
        tm_xm = self._create_mock_tm("厦门一中", "高二", "三班", {
            "labor": False, "military": False, "class_meeting_img": False, "class_meeting_record": False
        })

        prepared_accounts = [
            {"username": "student_fq", "status": "已就绪", "task_mgr": tm_fq},
            {"username": "student_xm", "status": "已就绪", "task_mgr": tm_xm}
        ]

        # 仅为福清一中准备资源 (使用清理后的路径)
        self._create_dummy_image(self._get_clean_path("劳动", "福清一中", "高一", "八班", "1.jpg"))
        self._create_dummy_image(self._get_clean_path("军训", "福清一中", "高一", "八班", "2.jpg"))
        self._create_dummy_image(self._get_clean_path("主题班会", "福清一中", "高一", "八班", "3.jpg"))
        self._create_dummy_excel(self._get_clean_path("主题班会", "福清一中", "高一", "八班", "record.xls"))

        # 执行报告生成
        saved_stdout = sys.stdout
        out = StringIO()
        try:
            sys.stdout = out
            generate_resource_health_report(prepared_accounts)
            report_text = out.getvalue()
        finally:
            sys.stdout = saved_stdout

        lines = report_text.splitlines()
        fq_line = [l for l in lines if "福清一中" in l][0]
        xm_line = [l for l in lines if "厦门一中" in l][0]

        self.assertIn("✅", fq_line)
        self.assertIn("❌", xm_line)

    @patch("comprehensive_eval_pro.flows.os.path.dirname")
    def test_fuzzy_matching_logic_in_report(self, mock_dirname):
        """
        场景 2：验证模糊匹配在报告中的表现。
        """
        mock_dirname.return_value = self.test_root
        
        tm = self._create_mock_tm("测试学校", "初一", "五班", {
            "labor": True, "military": False, "class_meeting_img": True, "class_meeting_record": True
        })

        # 模拟：劳动文件夹使用了非标准命名
        labor_path = self._get_clean_path("劳动", "测试学校", "初一", "五班", "校园大扫除专项", "clean.jpg")
        self._create_dummy_image(labor_path)
        
        # 模拟：主题班会包含子目录
        meeting_dir = self._get_clean_path("主题班会", "测试学校", "初一", "五班", "2025防火安全")
        self._create_dummy_image(os.path.join(meeting_dir, "p.jpg"))
        self._create_dummy_excel(os.path.join(meeting_dir, "data.xlsx"))

        prepared_accounts = [{"username": "test_user", "status": "已就绪", "task_mgr": tm}]

        saved_stdout = sys.stdout
        out = StringIO()
        try:
            sys.stdout = out
            generate_resource_health_report(prepared_accounts)
            report_text = out.getvalue()
        finally:
            sys.stdout = saved_stdout

        report_lines = report_text.splitlines()
        line = [l for l in report_lines if "初一" in l][0]
        self.assertIn("✅", line) 

    @patch("comprehensive_eval_pro.flows.os.path.dirname")
    def test_empty_account_list(self, mock_dirname):
        """
        场景 4：验证无就绪账号时的鲁棒性。
        """
        mock_dirname.return_value = self.test_root
        prepared_accounts = [{"username": "fail_user", "status": "登录失败", "task_mgr": None}]
        
        saved_stdout = sys.stdout
        out = StringIO()
        try:
            sys.stdout = out
            generate_resource_health_report(prepared_accounts)
            report_text = out.getvalue()
        finally:
            sys.stdout = saved_stdout
            
        self.assertEqual(report_text.strip(), "")

if __name__ == "__main__":
    unittest.main()
