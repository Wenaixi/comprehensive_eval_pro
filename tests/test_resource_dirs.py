import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager


class TestResourceDirs(unittest.TestCase):
    def test_pick_image_prefers_school_default_for_flag_speech(self):
        mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info={"studentSchoolInfo": {"schoolName": "福清一中", "gradeName": "高一", "className": "八班"}},
        )
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "assets")
            os.makedirs(os.path.join(base, "国旗下讲话", "福清一中", "默认"), exist_ok=True)
            os.makedirs(os.path.join(base, "国旗下讲话"), exist_ok=True)
            with open(os.path.join(base, "国旗下讲话", "福清一中", "默认", "a.jpg"), "wb") as f:
                f.write(b"0")
            with open(os.path.join(base, "国旗下讲话", "b.jpg"), "wb") as f:
                f.write(b"0")
            picked = mgr._pick_image_path("国旗下讲话", base_assets_dir=base)
            self.assertTrue((picked or "").endswith(os.path.join("福清一中", "默认", "a.jpg")))

    def test_pick_image_prefers_school_class_for_labor(self):
        mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info={"studentSchoolInfo": {"schoolName": "福清一中", "gradeName": "高一", "className": "高一八班"}},
        )
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "assets")
            # 嵌套路径：劳动/福清一中/高一/八班/
            os.makedirs(os.path.join(base, "劳动", "福清一中", "高一", "八班"), exist_ok=True)
            os.makedirs(os.path.join(base, "劳动"), exist_ok=True)
            with open(os.path.join(base, "劳动", "福清一中", "高一", "八班", "a.jpg"), "wb") as f:
                f.write(b"0")
            with open(os.path.join(base, "劳动", "b.jpg"), "wb") as f:
                f.write(b"0")
            picked = mgr._pick_image_path("劳动", base_assets_dir=base)
            self.assertTrue((picked or "").endswith(os.path.join("福清一中", "高一", "八班", "a.jpg")))

    def test_pick_image_supports_fuzzy_subfolder(self):
        mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info={"studentSchoolInfo": {"schoolName": "福清一中", "gradeName": "高一", "className": "八班"}},
        )
        with tempfile.TemporaryDirectory() as d:
            base = os.path.join(d, "assets")
            # 嵌套路径：劳动/福清一中/高一/八班/校园清洁/
            target_dir = os.path.join(base, "劳动", "福清一中", "高一", "八班", "校园清洁")
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, "special.jpg"), "wb") as f:
                f.write(b"0")
            
            # 匹配任务名
            picked = mgr._pick_image_path("劳动", task_name="关于【校园清洁】的任务", base_assets_dir=base)
            self.assertIn("special.jpg", picked)
            self.assertIn("校园清洁", picked)


if __name__ == "__main__":
    unittest.main()
