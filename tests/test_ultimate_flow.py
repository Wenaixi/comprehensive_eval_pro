import unittest
import os
import shutil
import tempfile
import time
from unittest.mock import MagicMock, patch
from concurrent.futures import ThreadPoolExecutor
from comprehensive_eval_pro.services.task_manager import ProTaskManager

class TestUltimateFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import logging
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    def setUp(self):
        # 创建临时测试环境
        self.test_dir = tempfile.mkdtemp()
        self.assets_dir = os.path.join(self.test_dir, "assets")
        self.runtime_dir = os.path.join(self.test_dir, "runtime")
        os.makedirs(self.assets_dir)
        os.makedirs(os.path.join(self.runtime_dir, "temp"))
        
        self.school = "测试中学"
        self.grade = "高一"
        self.task_name = "2026.02.11防欺凌主题班会"

        # 预先创建资源目录
        for class_name in ["8班", "9班", "10班"]:
            path = os.path.join(self.assets_dir, "主题班会", self.school, self.grade, class_name, self.task_name)
            os.makedirs(path)
            if class_name == "8班":
                with open(os.path.join(path, "记录.pdf"), "w") as f: f.write("fake pdf")
            # 只有 8 班和 9 班有照片
            if class_name != "10班":
                with open(os.path.join(path, "photo.jpg"), "w") as f: f.write("fake img")

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        ProTaskManager._GLOBAL_RECORD_CACHE.clear()

    def _setup_tm_mocks(self, tm, class_name):
        """统一配置 TM 的 Mock 环境"""
        # 直接 Mock 掉 _school_name 等，避免触发复杂的业务逻辑
        tm._school_name = MagicMock(return_value=self.school)
        tm._grade_name = MagicMock(return_value=self.grade)
        tm._pure_class_name = MagicMock(return_value=class_name)
        # 确保它能识别到班会任务
        tm._looks_like_class_meeting = MagicMock(return_value=True)

    @patch("comprehensive_eval_pro.services.task_manager.os.path.abspath")
    @patch("comprehensive_eval_pro.services.task_manager.ProTaskManager._get_content_from_pdf_via_ocr")
    def test_concurrency_and_cache(self, mock_ocr, mock_abspath):
        # 核心：让 abspath 始终指向我们 mock 的路径，从而让 current_dir 指向 test_dir
        mock_abspath.return_value = os.path.join(self.test_dir, "services", "task_manager.py")
        mock_ocr.side_effect = lambda *a, **k: "并发测试解析内容"
        
        session = MagicMock()
        task = {"id": 101, "name": self.task_name, "dimensionName": "思想品德"}
        ai_gen = MagicMock()
        ai_gen.generate_class_meeting_content.return_value = "AI: 并发测试解析内容"
        ai_gen.generate_speech_content.return_value = "AI: 并发测试解析内容"

        def run_task(class_name):
            tm = ProTaskManager(session)
            self._setup_tm_mocks(tm, class_name)
            return tm.submit_task(task, ai_gen, dry_run=True)

        classes = ["8班", "9班", "10班"]
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(run_task, classes))

        # 8班和9班应该成功（有照片）
        self.assertEqual(results[0]["payload"]["content"], "AI: 并发测试解析内容")
        self.assertEqual(results[1]["payload"]["content"], "AI: 并发测试解析内容")
        # 10班应该失败（无照片）
        self.assertIsNone(results[2])
        
        # OCR 只执行一次
        self.assertEqual(mock_ocr.call_count, 1)

    @patch("comprehensive_eval_pro.services.task_manager.os.path.abspath")
    @patch("comprehensive_eval_pro.services.task_manager.fitz.open")
    def test_pdf_corruption_cleanup(self, mock_fitz_open, mock_abspath):
        mock_abspath.return_value = os.path.join(self.test_dir, "services", "task_manager.py")
        mock_fitz_open.side_effect = Exception("PDF Corrupted")
        
        tm = ProTaskManager(MagicMock())
        self._setup_tm_mocks(tm, "8班")
        
        task = {"id": 101, "name": self.task_name, "dimensionName": "思想品德"}
        ai_gen = MagicMock()
        
        tm.submit_task(task, ai_gen, dry_run=True)
        
        temp_dir = os.path.join(self.runtime_dir, "temp")
        self.assertEqual(len(os.listdir(temp_dir)), 0)

    def test_labor_exclusion_edge_cases(self):
        self.assertTrue(ProTaskManager._is_labor_task("校园卫生劳动"))
        self.assertFalse(ProTaskManager._is_labor_task("劳动素养自我评价"))

if __name__ == "__main__":
    unittest.main()
