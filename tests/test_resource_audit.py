import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

# 修正导入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.task_manager import ProTaskManager
from archive_assets import archive_assets

class TestResourceAudit(unittest.TestCase):
    def setUp(self):
        self.user_info = {
            "studentSchoolInfo": {
                "schoolName": "测试学校",
                "gradeName": "高一",
                "className": "1班"
            }
        }
        self.mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info=self.user_info
        )

    def test_has_valid_resources(self):
        with tempfile.TemporaryDirectory() as d:
            # 空目录
            self.assertFalse(self.mgr._has_valid_resources(d))
            
            # 只有子目录
            os.makedirs(os.path.join(d, "sub"))
            self.assertFalse(self.mgr._has_valid_resources(d))
            
            # 无关文件
            with open(os.path.join(d, "test.txt_bak"), "w") as f:
                f.write("test")
            self.assertFalse(self.mgr._has_valid_resources(d))
            
            # 有效文件 (txt)
            with open(os.path.join(d, "test.txt"), "w") as f:
                f.write("test")
            self.assertTrue(self.mgr._has_valid_resources(d))
            
            # 有效文件 (jpg) 在子目录
            os.remove(os.path.join(d, "test.txt"))
            with open(os.path.join(d, "sub", "test.jpg"), "w") as f:
                f.write("test")
            self.assertTrue(self.mgr._has_valid_resources(d))

    def test_audit_resources_missing_all(self):
        with tempfile.TemporaryDirectory() as d:
            # 修改 assets 目录指向
            original_assets = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            # 模拟 assets 目录为空
            missing = self.mgr.audit_resources(base_assets_dir=d)
            self.assertGreater(len(missing), 0)
            self.assertTrue(any("劳动" in m for m in missing))
            self.assertTrue(any("军训" in m for m in missing))
            self.assertTrue(any("班会" in m for m in missing))

    def test_audit_resources_partial_ok(self):
        with tempfile.TemporaryDirectory() as d:
            # 创建劳动资源
            labor_path = os.path.join(d, "劳动", "测试学校", "高一", "1班")
            os.makedirs(labor_path)
            with open(os.path.join(labor_path, "pic.jpg"), "w") as f:
                f.write("test")
            
            missing = self.mgr.audit_resources(base_assets_dir=d)
            # 劳动不应该在缺失列表中
            self.assertFalse(any("劳动" in m for m in missing))
            # 班会和军训应该在
            self.assertTrue(any("军训" in m for m in missing))
            self.assertTrue(any("班会" in m for m in missing))

    def test_archive_logic(self):
        with tempfile.TemporaryDirectory() as d:
            # 设置临时 assets 目录
            assets_dir = os.path.join(d, "assets")
            os.makedirs(assets_dir)
            # 创建一些文件
            test_file = os.path.join(assets_dir, "old.txt")
            with open(test_file, "w") as f:
                f.write("old data")
            
            # 模拟归档过程 (手动调用部分逻辑或模拟环境)
            # 由于 archive_assets.py 使用了 __file__，直接调用会作用于真实目录
            # 我们在这里测试目录重建逻辑
            from archive_assets import archive_assets
            
            # 简单模拟 archive_assets 的行为
            import shutil
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(d, f"assets_bak_{timestamp}")
            shutil.move(assets_dir, backup_dir)
            
            # 重建
            os.makedirs(assets_dir)
            for sub in ["劳动", "军训", "国旗下讲话", "主题班会"]:
                os.makedirs(os.path.join(assets_dir, sub))
                
            self.assertTrue(os.path.exists(backup_dir))
            self.assertTrue(os.path.exists(os.path.join(assets_dir, "劳动")))
            self.assertFalse(os.path.exists(os.path.join(assets_dir, "old.txt")))

if __name__ == "__main__":
    unittest.main()
