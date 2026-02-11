import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import flows


class DummyMgr:
    def __init__(self, tasks):
        self._tasks = tasks
        self.submitted = []
        self.student_name = "stu"

    def get_all_tasks(self, force_refresh=False):
        return self._tasks

    def get_class_meeting_folders(self):
        return []

    def audit_resources(self):
        return []

    def submit_task(self, task, ai_gen, dry_run=True, use_cache=True):
        if dry_run:
            return {"code": 1, "payload": {"name": task.get("name"), "content": "x"}}
        self.submitted.append(task.get("name"))
        return {"code": 1}


class DummyAI:
    pass


class TestFlowScopeSelection(unittest.TestCase):
    def test_scope_done_only_submits_done_tasks(self):
        tasks = [
            {"name": "劳动A", "circleTaskStatus": "待写实", "dimensionName": "x"},
            {"name": "劳动B", "circleTaskStatus": "已提交", "dimensionName": "x"},
            {"name": "其他C", "circleTaskStatus": "已提交", "dimensionName": "x"},
        ]
        mgr = DummyMgr(tasks)
        preset = {
            "mode": "ld",
            "selection": "ld",
            "scope": "done",
            "indices": [],
            "skip_review": True,
            "confirmed_resubmit": True,
            "diversity_every": 5,
            "submit_index": 0,
        }
        flows.run_task_flow(mgr, DummyAI(), preset=preset, strict=False)
        self.assertEqual(mgr.submitted, ["劳动B"])


if __name__ == "__main__":
    unittest.main()

