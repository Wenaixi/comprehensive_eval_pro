import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.content_gen import AIContentGenerator
from comprehensive_eval_pro.services.task_manager import ProTaskManager


class TestTaskPayload(unittest.TestCase):
    def setUp(self):
        self.ai = AIContentGenerator(api_key=None)
        self.mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info={"studentSchoolInfo": {"gradeName": "高一", "className": "八班"}},
            upload_url="http://example.com/upload",
        )

    def test_payload_class_meeting(self):
        task = {"name": "主题班会：消防安全", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "德育"}
        preview = self.mgr.submit_task(task, self.ai, dry_run=True, use_cache=True)
        p = preview["payload"]
        self.assertEqual(p["name"], "班会")
        self.assertEqual(p["hours"], 1.0)
        self.assertEqual(p["address"], "高一八班")
        self.assertEqual(p["playRole"], "3")

    def test_payload_labor(self):
        task = {"name": "劳动：校园清洁", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "劳动"}
        preview = self.mgr.submit_task(task, self.ai, dry_run=True, use_cache=True)
        p = preview["payload"]
        self.assertEqual(p["name"], "劳动：校园清洁")
        self.assertEqual(p["level"], "5")
        self.assertEqual(p["orgName"], "福清一中")
        self.assertEqual(p["address"], "福清一中")
        self.assertEqual(p["playRole"], "")

    def test_payload_military(self):
        task = {"name": "军训：队列训练", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "军训"}
        preview = self.mgr.submit_task(task, self.ai, dry_run=True, use_cache=True)
        p = preview["payload"]
        self.assertEqual(p["name"], "")
        self.assertEqual(p["hours"], 32.0)
        self.assertEqual(p["checkResult"], "1")
        self.assertEqual(p["orgName"], "福清一中")
        self.assertEqual(p["address"], "福清一中")
        self.assertEqual(p["playRole"], "")

    def test_payload_generic(self):
        task = {"name": "社团活动", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "其他"}
        preview = self.mgr.submit_task(task, self.ai, dry_run=True, use_cache=True)
        p = preview["payload"]
        self.assertEqual(p["name"], "社团活动")
        self.assertEqual(p["playRole"], "3")


if __name__ == "__main__":
    unittest.main()

