import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import flows


class TestLoginFallback(unittest.TestCase):
    def test_manual_captcha_fallback_when_no_ocr(self):
        auth = mock.Mock()
        auth.ocr = None
        auth.get_captcha.return_value = ("X:\\tmp\\captcha.jpg", "")
        auth.login.return_value = True

        with mock.patch("builtins.input", return_value="abcd"):
            ok = flows.ocr_login_with_retries(auth, "u", "p", "sid", max_retries=3)

        self.assertTrue(ok)
        auth.get_captcha.assert_called()
        auth.get_captcha.assert_called_with(auto_open=True)
        auth.login.assert_called_with("u", "p", "abcd", school_id="sid")

    def test_ocr_fail_then_manual_fallback(self):
        auth = mock.Mock()
        auth.ocr = object()

        auth.get_captcha.side_effect = [("X:\\tmp\\captcha.jpg", "bad")] * 10 + [("X:\\tmp\\captcha.jpg", "")]
        auth.login.side_effect = [False] * 10 + [True]

        with mock.patch("builtins.input", return_value="good"):
            ok = flows.ocr_login_with_retries(auth, "u", "p", "sid", max_retries=10)

        self.assertTrue(ok)
        self.assertEqual(auth.get_captcha.call_count, 11)
        auth.get_captcha.assert_any_call(auto_open=False)
        auth.get_captcha.assert_any_call(auto_open=True)


if __name__ == "__main__":
    unittest.main()
