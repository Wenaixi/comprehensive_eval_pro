import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager
from comprehensive_eval_pro.utils.record_parser import extract_first_record_text

class TestFuzzyMatchingAdvanced(unittest.TestCase):
    def setUp(self):
        self.test_root = os.path.realpath(tempfile.mkdtemp(prefix="cep_fuzzy_"))
        self.assets_dir = Path(self.test_root) / "assets"
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.tm = ProTaskManager(token="mock_token")

    def tearDown(self):
        if os.path.exists(self.test_root):
            shutil.rmtree(self.test_root)

    def _create_file(self, path):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            if p.suffix.lower() in (".jpg", ".jpeg"):
                f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")
            elif p.suffix.lower() in (".xls", ".xlsx"):
                f.write(b"content: this is a test record for fuzzy matching")
            else:
                f.write(b"dummy content")

    def test_fuzzy_matching_logic_deep(self):
        base_dir = self.assets_dir / "主题班会" / "测试学校" / "高一" / "1班"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        self._create_file(base_dir / "无关文件夹" / "photo.jpg")
        self._create_file(base_dir / "2025.10.13 其他活动" / "photo.jpg")
        target_dir = base_dir / "2025.10.13 高一(1)班 “法制教育” 主题班会"
        self._create_file(target_dir / "photo1.jpg")
        self._create_file(target_dir / "记录.xlsx")
        
        task_name = "2025.10.13 开展“法制教育”主题班会活动"
        found_dir = self.tm._find_best_matching_folder(task_name, str(base_dir))
        
        self.assertIsNotNone(found_dir)
        self.assertEqual(os.path.realpath(found_dir), os.path.realpath(str(target_dir)))

    def test_nested_recursive_images(self):
        target_dir = self.assets_dir / "劳动" / "测试学校" / "深层目录"
        img_path = target_dir / "a" / "b" / "c" / "deep_photo.png"
        self._create_file(img_path)
        
        imgs = self.tm._list_images_recursive(str(target_dir))
        self.assertEqual(len(imgs), 1)
        self.assertIn("deep_photo.png", imgs[0])

    def test_multi_suffix_and_record_extraction(self):
        target_dir = self.assets_dir / "班会资源包"
        self._create_file(target_dir / "img1.JPG")
        self._create_file(target_dir / "img2.jpeg")
        self._create_file(target_dir / "record.xlsx")
        
        imgs = [f for f in os.listdir(target_dir) if f.lower().endswith(self.tm.IMAGE_EXTS)]
        self.assertEqual(len(imgs), 2)
        
        content, used_file = extract_first_record_text(str(target_dir))
        if used_file:
            self.assertIn("record.xlsx", used_file)

if __name__ == "__main__":
    unittest.main()
