import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.task_manager import ProTaskManager


class _BombAI:
    def generate_labor_content(self, *args, **kwargs):
        raise AssertionError("should not call generate_labor_content when content_override is set")

    def generate_military_content(self, *args, **kwargs):
        raise AssertionError("should not call generate_military_content when content_override is set")

    def generate_class_meeting_content(self, *args, **kwargs):
        raise AssertionError("should not call generate_class_meeting_content when content_override is set")

    def generate_speech_content(self, *args, **kwargs):
        raise AssertionError("should not call generate_speech_content when content_override is set")


class TestTaskSubmitOverrides(unittest.TestCase):
    def setUp(self):
        self.mgr = ProTaskManager(
            token="dummy",
            base_url="http://example.com",
            user_info={"studentSchoolInfo": {"gradeName": "高一", "className": "八班", "schoolName": "福清一中"}},
            upload_url="http://example.com/upload",
        )

    def test_content_override_bypasses_ai_generation(self):
        task = {"name": "劳动：校园清洁", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "劳动"}
        preview = self.mgr.submit_task(task, _BombAI(), dry_run=True, use_cache=True, content_override="X")
        self.assertEqual(preview["payload"]["content"], "X")

    def test_attachment_ids_override_bypasses_image_pick(self):
        task = {"name": "国旗下讲话：主题", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "德育"}
        with mock.patch.object(self.mgr, "_pick_image_path", side_effect=AssertionError("should not pick image")):
            preview = self.mgr.submit_task(
                task,
                _BombAI(),
                dry_run=True,
                use_cache=True,
                content_override="X",
                attachment_ids_override=[123],
            )
        self.assertEqual(preview["payload"]["pictureList"], [123])
        self.assertEqual(preview.get("upload_paths") or [], [])

    def test_dry_run_returns_upload_paths_when_image_selected(self):
        task = {"name": "劳动：校园清洁", "id": 1, "dimensionId": 2, "circleTypeId": 3, "dimensionName": "劳动"}
        with mock.patch.object(self.mgr, "_pick_image_path", return_value="X:\\a.jpg"):
            preview = self.mgr.submit_task(task, _BombAI(), dry_run=True, use_cache=True, content_override="X")
        self.assertEqual(preview["upload_paths"], ["X:\\a.jpg"])
        self.assertEqual(preview["payload"]["pictureList"], [999999])


if __name__ == "__main__":
    unittest.main()

