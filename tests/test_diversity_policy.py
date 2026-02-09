import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import main as app_main


class TestDiversityPolicy(unittest.TestCase):
    def test_should_use_cache_every_5(self):
        every = 5
        flags = [app_main._should_use_cache(i, every) for i in range(10)]
        self.assertEqual(flags, [True, True, True, True, False, True, True, True, True, False])

    def test_should_use_cache_disabled(self):
        self.assertTrue(app_main._should_use_cache(0, 0))
        self.assertTrue(app_main._should_use_cache(4, -1))

    def test_get_diversity_every_default(self):
        old = os.environ.get("CEP_DIVERSITY_EVERY")
        try:
            if "CEP_DIVERSITY_EVERY" in os.environ:
                del os.environ["CEP_DIVERSITY_EVERY"]
            self.assertEqual(app_main._get_diversity_every(), 3)
        finally:
            if old is None:
                if "CEP_DIVERSITY_EVERY" in os.environ:
                    del os.environ["CEP_DIVERSITY_EVERY"]
            else:
                os.environ["CEP_DIVERSITY_EVERY"] = old


if __name__ == "__main__":
    unittest.main()
