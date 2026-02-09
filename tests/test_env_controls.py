import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import main as app_main


class TestEnvControls(unittest.TestCase):
    def test_env_bool_parsing(self):
        old = os.environ.get("X_TEST_BOOL")
        try:
            os.environ["X_TEST_BOOL"] = "y"
            self.assertTrue(app_main._env_bool("X_TEST_BOOL", False))
            os.environ["X_TEST_BOOL"] = "0"
            self.assertFalse(app_main._env_bool("X_TEST_BOOL", True))
        finally:
            if old is None:
                if "X_TEST_BOOL" in os.environ:
                    del os.environ["X_TEST_BOOL"]
            else:
                os.environ["X_TEST_BOOL"] = old

    def test_get_ocr_max_retries_default(self):
        old = os.environ.get("CEP_OCR_MAX_RETRIES")
        try:
            if "CEP_OCR_MAX_RETRIES" in os.environ:
                del os.environ["CEP_OCR_MAX_RETRIES"]
            self.assertEqual(app_main._get_ocr_max_retries(), 10)
        finally:
            if old is None:
                if "CEP_OCR_MAX_RETRIES" in os.environ:
                    del os.environ["CEP_OCR_MAX_RETRIES"]
            else:
                os.environ["CEP_OCR_MAX_RETRIES"] = old


if __name__ == "__main__":
    unittest.main()

