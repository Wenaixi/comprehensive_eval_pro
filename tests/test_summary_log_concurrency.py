import os
import sys
import threading
import shutil
import tempfile
import unittest

# 允许从根目录导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.summary_log import append_summary

class TestSummaryLogConcurrency(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="cep_test_log_")
        self.username = "test_user_concurrency"
        self.user_info = {
            "studentSchoolInfo": {
                "schoolName": "并发测试学校",
                "gradeName": "高一",
                "className": "八班"
            }
        }

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_concurrent_writes(self):
        """
        压力测试：多线程并发写入同一个日志文件，验证完整性。
        """
        num_threads = 20
        writes_per_thread = 50
        total_expected = num_threads * writes_per_thread

        def worker(thread_id):
            for i in range(writes_per_thread):
                task_name = f"Thread-{thread_id}-Task-{i}"
                append_summary(
                    username=self.username,
                    user_info=self.user_info,
                    task_name=task_name,
                    ok=True,
                    msg="Success",
                    log_dir=self.test_dir
                )

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 验证结果
        log_path = os.path.join(self.test_dir, "并发测试学校", "高一", "八班", f"{self.username}.log")
        self.assertTrue(os.path.exists(log_path), "日志文件未生成")

        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.assertEqual(len(lines), total_expected, f"预期 {total_expected} 行，实际 {len(lines)} 行。并发写入可能存在丢失。")
        
        # 检查是否有损坏的行（简单检查每行是否以时间戳开头，且包含 OK）
        for line in lines:
            self.assertIn("OK", line)
            self.assertIn("Thread-", line)

if __name__ == "__main__":
    unittest.main()
