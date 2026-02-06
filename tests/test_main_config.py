import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import main as app_main


class TestMainConfig(unittest.TestCase):
    def test_load_config_creates_from_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "config.json")
            example_path = os.path.join(tmp, "config.example.json")

            with open(example_path, "w", encoding="utf-8") as f:
                json.dump({"model": "x", "token": ""}, f, ensure_ascii=False, indent=2)

            old_config = app_main.CONFIG_FILE
            old_example = app_main.CONFIG_EXAMPLE_FILE
            try:
                app_main.CONFIG_FILE = config_path
                app_main.CONFIG_EXAMPLE_FILE = example_path
                cfg = app_main.load_config()
            finally:
                app_main.CONFIG_FILE = old_config
                app_main.CONFIG_EXAMPLE_FILE = old_example

            self.assertTrue(os.path.exists(config_path))
            self.assertIn("model", cfg)
            self.assertIn("base_url", cfg)
            self.assertIn("upload_url", cfg)
            self.assertIn("sso_base", cfg)


if __name__ == "__main__":
    unittest.main()
