import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.flow_logic import (
    compute_base_entries,
    compute_target_entries,
    mark_task_generated,
    should_use_cache_for_task,
)
from comprehensive_eval_pro.policy import should_use_cache


class TestFlowLogic(unittest.TestCase):
    def test_compute_base_entries_y(self):
        tasks = [{"name": "劳动A"}, {"name": "其他"}, {"name": "军训B"}]

        def is_y(t):
            return "劳动" in t.get("name", "") or "军训" in t.get("name", "")

        base = compute_base_entries(
            tasks=tasks,
            selection="y",
            indices=[],
            looks_like_class_meeting=lambda t: False,
            is_y_special_task=is_y,
        )
        self.assertEqual([i for i, _ in base], [0, 2])

    def test_compute_target_entries_scope(self):
        base = [
            (0, {"circleTaskStatus": "待写实"}),
            (1, {"circleTaskStatus": "已提交"}),
        ]

        def get_status(t):
            return t.get("circleTaskStatus")

        def is_pending(s):
            return s == "待写实"

        target, pending_count, done_count = compute_target_entries(
            base_entries=base,
            scope="pending",
            get_task_status=get_status,
            is_pending_status=is_pending,
        )
        self.assertEqual([i for i, _ in target], [0])
        self.assertEqual(pending_count, 1)
        self.assertEqual(done_count, 1)

    def test_task_name_based_cache_counting(self):
        preset = {"diversity_every": 3}
        task_name = "劳动：校园清洁"

        self.assertTrue(
            should_use_cache_for_task(preset=preset, task_name=task_name, diversity_every=3, should_use_cache=should_use_cache)
        )
        mark_task_generated(preset=preset, task_name=task_name)

        self.assertTrue(
            should_use_cache_for_task(preset=preset, task_name=task_name, diversity_every=3, should_use_cache=should_use_cache)
        )
        mark_task_generated(preset=preset, task_name=task_name)

        self.assertFalse(
            should_use_cache_for_task(preset=preset, task_name=task_name, diversity_every=3, should_use_cache=should_use_cache)
        )


if __name__ == "__main__":
    unittest.main()

