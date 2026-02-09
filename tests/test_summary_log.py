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
                user_info={"studentSchoolInfo": {"gradeName": "高一", "className": "八班"}},
                task_name="劳动：校园清洁",
                ok=True,
                log_dir=d,
            )
            path = os.path.join(d, "u1.log")
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("高一八班", content)
            self.assertIn("劳动：校园清洁", content)


if __name__ == "__main__":
    unittest.main()

