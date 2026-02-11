import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import flows


class _DummyAI:
    def enabled(self):
        return True


class _DummyAuth:
    def __init__(self):
        self.calls = []
        self.login_attempts = 0

    def get_captcha(self, auto_open=False, engine=None, ai_model=None):
        self.calls.append((engine, ai_model))
        return "x.jpg", "1111"

    def login(self, username, password, captcha_code, school_id=None):
        self.login_attempts += 1
        # 模拟前 3 次登录失败（比如验证码识别错），第 4 次成功
        if self.login_attempts <= 3:
            return False
        return True


class TestOCRFallbackPriority(unittest.TestCase):
    def test_auto_engine_is_used(self):
        auth = _DummyAuth()
        # 模拟 policy 中的配置
        with mock.patch("comprehensive_eval_pro.flows.get_ocr_max_retries", return_value=5):
            with mock.patch("comprehensive_eval_pro.flows.get_manual_ocr_max_retries", return_value=1):
                ok = flows.ocr_login_with_retries(auth, "u", "p", "sid")
                self.assertTrue(ok)
                # 应该调用了 4 次 get_captcha，且 engine 都是 "auto"
                self.assertEqual(len(auth.calls), 4)
                for call in auth.calls:
                    self.assertEqual(call[0], "auto")


if __name__ == "__main__":
    unittest.main()
