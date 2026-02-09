import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.logging_setup import setup_logging


class TestLoggingSetup(unittest.TestCase):
    def test_file_logging_creates_output(self):
        with tempfile.TemporaryDirectory() as d:
            log_path = os.path.join(d, "app.log")
            setup_logging(level="INFO", log_file=log_path, console=False, max_bytes=1024 * 1024, backup_count=1)

            import logging

            logger = logging.getLogger("TestLogger")
            logger.info("hello")
            for h in logging.getLogger().handlers:
                try:
                    h.flush()
                except Exception:
                    pass
            for h in list(logging.getLogger().handlers):
                try:
                    h.close()
                except Exception:
                    pass
                logging.getLogger().removeHandler(h)

            self.assertTrue(os.path.exists(log_path))
            with open(log_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("hello", content)


if __name__ == "__main__":
    unittest.main()
