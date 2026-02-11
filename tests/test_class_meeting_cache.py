import unittest
import os
import shutil
from comprehensive_eval_pro.services.task_manager import ProTaskManager

class MockAIGen:
    def __init__(self):
        self.enabled = lambda: True
    def generate_class_meeting_content(self, text, name, use_cache=True, school_name=""):
        return f"AI Generated: {text[:20]}"
    def generate_content_from_images(self, paths, name, school_name=""):
        return "OCR Result from images"
    def generate_speech_content(self, name, use_cache=True, school_name=""):
        return "Speech Content"

class TestClassMeetingGlobalCache(unittest.TestCase):
    def setUp(self):
        # 准备测试资源目录
        self.base_dir = os.path.abspath(os.path.join(os.getcwd(), "test_assets_cache"))
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)
        os.makedirs(self.base_dir)
        
        # 模拟两个班级的资源包
        # 8班有正确的文本文件
        self.class8_dir = os.path.join(self.base_dir, "SchoolA", "Grade1", "Class8")
        self.pkg8_dir = os.path.join(self.class8_dir, "Meeting1")
        os.makedirs(self.pkg8_dir)
        with open(os.path.join(self.pkg8_dir, "record.txt"), "w", encoding="utf-8") as f:
            f.write("This is Class 8 Correct Record Content")
            
        # 9班啥也没有，只有几张图
        self.class9_dir = os.path.join(self.base_dir, "SchoolA", "Grade1", "Class9")
        self.pkg9_dir = os.path.join(self.class9_dir, "Meeting1")
        os.makedirs(self.pkg9_dir)
        with open(os.path.join(self.pkg9_dir, "photo1.jpg"), "w") as f: f.write("dummy")

        # 重置全局缓存
        ProTaskManager._GLOBAL_RECORD_CACHE = {}

    def tearDown(self):
        if os.path.exists(self.base_dir):
            shutil.rmtree(self.base_dir)

    def test_global_cache_dominance(self):
        ai = MockAIGen()
        task = {"name": "2026.1.12高一（8）班《测试班会》", "id": 1}
        
        # 1. 模拟8班运行 (第一个运行的)
        mgr8 = ProTaskManager("token8", user_info={
            "studentSchoolInfo": {"schoolName": "SchoolA", "gradeName": "Grade1", "className": "Class8"}
        })
        # 核心：把 assets_dir 指向我们的测试目录
        mgr8.assets_dir = self.base_dir
        
        # 强制指定匹配路径逻辑
        def mock_find_folder(self_mgr, t_name, b_dir):
            # b_dir 已经是 assets_dir 拼接后的路径
            # 简化匹配逻辑，直接返回对应的 Meeting1 文件夹
            if "Class8" in b_dir: return self.pkg8_dir
            if "Class9" in b_dir: return self.pkg9_dir
            return None
        
        # 将 mock 方法绑定到实例上
        import types
        mgr8._find_best_matching_folder = types.MethodType(mock_find_folder, mgr8)
        
        # 为了让 os.path.isdir(cand_root) 返回 True，我们需要在 mgr8 运行前，
        # 确保 cand_root 对应的物理目录存在
        # ProTaskManager 内部拼接路径是 os.path.join(current_dir, "assets", "主题班会", ...)
        # 看来我得更暴力一点，直接 mock os.path.isdir
        
        import unittest.mock as mock
        with mock.patch("os.path.isdir", return_value=True):
            # 执行提交
            mgr8.submit_task(task, ai, dry_run=True)
            
            # 缓存键目前是 "{school_name}_{normalized_task_name}"
            # 归一化逻辑会去掉括号等符号
            norm_name = ProTaskManager._normalize_match_text(task["name"])
            cache_key = f"SchoolA_{norm_name}"
            print(f"[DEBUG] Generated Cache Key: {cache_key}")
            self.assertIn(cache_key, ProTaskManager._GLOBAL_RECORD_CACHE)
            self.assertEqual(ProTaskManager._GLOBAL_RECORD_CACHE[cache_key], "This is Class 8 Correct Record Content")
            
            # 2. 模拟9班运行 (应该命中8班的缓存)
            mgr9 = ProTaskManager("token9", user_info={
                "studentSchoolInfo": {"schoolName": "SchoolA", "gradeName": "Grade1", "className": "Class9"}
            })
            mgr9.assets_dir = self.base_dir
            mgr9._find_best_matching_folder = types.MethodType(mock_find_folder, mgr9)
            
            # 即使 mgr9 的目录下没有文本文件，它也应该从缓存里拿到 8 班的内容
            preview = mgr9.submit_task(task, ai, dry_run=True)
            content = preview["payload"]["content"]
            
            self.assertIn("Class 8", content)
            print("✅ 霸道缓存验证成功：9班成功复用了8班的解析结果")

if __name__ == "__main__":
    unittest.main()
