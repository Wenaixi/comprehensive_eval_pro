import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import flows


class TestLoginFallback(unittest.TestCase):
    def test_manual_captcha_fallback_on_auto_failure(self):
        auth = mock.Mock()
        # 模拟自动识别总是返回错误验证码
        auth.get_captcha.return_value = ("X:\\tmp\\captcha.jpg", "wrong")
        auth.login.return_value = False
        
        # 模拟手动登录成功
        def login_side_effect(u, p, code, school_id=None):
            return code == "manual_code"
        auth.login.side_effect = login_side_effect

        with mock.patch("comprehensive_eval_pro.flows.get_ocr_max_retries", return_value=1):
            with mock.patch("comprehensive_eval_pro.flows.get_manual_ocr_max_retries", return_value=1):
                # 第一次 get_captcha 是自动
                # 第二次 get_captcha 是手动
                auth.get_captcha.side_effect = [
                    ("X:\\tmp\\captcha.jpg", "wrong"),
                    ("X:\\tmp\\captcha.jpg", "")
                ]
                with mock.patch("builtins.input", return_value="manual_code"):
                    ok = flows.ocr_login_with_retries(auth, "u", "p", "sid")

        self.assertTrue(ok)
        self.assertEqual(auth.get_captcha.call_count, 2)
        # 验证第一次是 auto，第二次是 manual
        calls = auth.get_captcha.call_args_list
        self.assertEqual(calls[0].kwargs.get('engine'), "auto")
        self.assertEqual(calls[1].kwargs.get('engine'), "manual")


if __name__ == "__main__":
    unittest.main()
