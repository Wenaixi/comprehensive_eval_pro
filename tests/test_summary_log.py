import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.summary_log import append_summary


class TestSummaryLog(unittest.TestCase):
    def test_append_summary_writes_file(self):
        with tempfile.TemporaryDirectory() as d:
            append_summary(
                username="u1",
                user_info={
                    "studentSchoolInfo": {
                        "schoolName": "测试中学",
                        "gradeName": "高一",
                        "className": "八班"
                    }
                },
                task_name="劳动：校园清洁",
                ok=True,
                log_dir=d,
            )
            # 新路径逻辑：{log_dir}/{school}/{grade}/{class}/{username}.log
            path = os.path.join(d, "测试中学", "高一", "八班", "u1.log")
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("八班", content)
            self.assertIn("劳动：校园清洁", content)
            # 验证颜色代码存在 (例如 \033[)
            self.assertIn("\033[", content)


if __name__ == "__main__":
    unittest.main()

