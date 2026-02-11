import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import main as app_main


class TestMainConfig(unittest.TestCase):
    def test_load_config_returns_state(self):
        cfg = app_main.load_config()
        self.assertIsInstance(cfg, dict)
        # 应该包含 accounts 键
        self.assertIn("accounts", cfg)

    def test_save_config_calls_manager(self):
        with mock.patch.object(app_main.config, "save_state") as mock_save:
            app_main.save_config(app_main.config.state)
            mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
