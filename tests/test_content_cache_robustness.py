import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.content_gen import AIContentGenerator


class TestContentCacheRobustness(unittest.TestCase):
    def test_invalid_json_cache_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            cache_path = os.path.join(d, "content_cache.json")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write("{not-json")

            old = os.environ.get("CEP_CACHE_FILE")
            os.environ["CEP_CACHE_FILE"] = cache_path
            try:
                gen = AIContentGenerator(api_key=None)
                self.assertIsInstance(gen.cache, dict)
            finally:
                if old is None:
                    os.environ.pop("CEP_CACHE_FILE", None)
                else:
                    os.environ["CEP_CACHE_FILE"] = old


if __name__ == "__main__":
    unittest.main()

