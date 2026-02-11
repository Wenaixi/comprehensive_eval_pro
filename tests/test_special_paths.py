import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# 确保可以导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager

class TestSpecialPaths(unittest.TestCase):
    def setUp(self):
        self.test_root = os.path.realpath(tempfile.mkdtemp(prefix="cep_special_"))
        self.assets_dir = Path(self.test_root) / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 TaskManager 并 Mock 关键信息
        self.tm = ProTaskManager(token="mock_token")
        self.tm._school_name = MagicMock(return_value="福清一中")
        self.tm._grade_name = MagicMock(return_value="高一")
        self.tm._pure_class_name = MagicMock(return_value="八班")

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def _create_img(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
        return str(p)

    def test_speech_path_shared(self):
        """验证国旗下讲话强制全校共享路径，不使用年级/班级层级"""
        # 1. 即使存在年级/班级目录，也不应被匹配
        wrong_path = self.assets_dir / "国旗下讲话" / "福清一中" / "高一" / "八班" / "wrong.jpg"
        self._create_img(wrong_path)
        
        # 2. 只有 学校/默认 目录下的图片才应该被匹配
        correct_path = self.assets_dir / "国旗下讲话" / "福清一中" / "默认" / "correct.jpg"
        self._create_img(correct_path)
        
        # 执行匹配
        picked = self.tm._pick_image_path("国旗下讲话", base_assets_dir=str(self.assets_dir))
        
        self.assertIsNotNone(picked)
        self.assertEqual(os.path.realpath(picked), os.path.realpath(str(correct_path)))

    def test_labor_path_hierarchy_with_fallback(self):
        """验证劳动任务保留层级，并支持学校默认兜底"""
        school_default = self.assets_dir / "劳动" / "福清一中" / "默认" / "fallback.jpg"
        class_specific = self.assets_dir / "劳动" / "福清一中" / "高一" / "八班" / "specific.jpg"
        
        # 情况 A: 只有学校默认
        self._create_img(school_default)
        picked_a = self.tm._pick_image_path("劳动", base_assets_dir=str(self.assets_dir))
        self.assertEqual(os.path.realpath(picked_a), os.path.realpath(str(school_default)))
        
        # 情况 B: 存在班级专属，应优先使用
        self._create_img(class_specific)
        picked_b = self.tm._pick_image_path("劳动", base_assets_dir=str(self.assets_dir))
        self.assertEqual(os.path.realpath(picked_b), os.path.realpath(str(class_specific)))

if __name__ == "__main__":
    unittest.main()
