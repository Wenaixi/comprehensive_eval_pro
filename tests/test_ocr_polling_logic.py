import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.flows import ocr_login_with_retries

class TestOCRPollingLogic(unittest.TestCase):
    def setUp(self):
        self.mock_auth = MagicMock()
        
    def test_auto_engine_calls(self):
        """
        验证 flows 现在统一调用 engine="auto"
        """
        self.mock_auth.get_captcha.return_value = ("path", "code")
        self.mock_auth.login.return_value = False
        
        with patch("comprehensive_eval_pro.flows.get_ocr_max_retries", return_value=3):
            with patch("comprehensive_eval_pro.flows.get_manual_ocr_max_retries", return_value=1):
                # 模拟手动输入以防止 OSError
                with patch("builtins.input", return_value="q"):
                    result = ocr_login_with_retries(self.mock_auth, "user", "pass", "sid")
                
        self.assertFalse(result)
        # 应该调用了 3 次自动 get_captcha + 1 次手动 get_captcha，且前 3 次 engine 都是 "auto"
        # 注意：ocr_login_with_retries 在自动失败后会尝试手动
        self.assertEqual(self.mock_auth.get_captcha.call_count, 4)
        calls = self.mock_auth.get_captcha.call_args_list
        for i in range(3):
            self.assertEqual(calls[i].kwargs.get('engine'), "auto")
        self.assertEqual(calls[3].kwargs.get('engine'), "manual")

    def test_success_stops_polling(self):
        """
        验证成功时立即停止
        """
        self.mock_auth.get_captcha.return_value = ("path", "correct_code")
        self.mock_auth.login.return_value = True
        
        result = ocr_login_with_retries(self.mock_auth, "user", "pass", "sid")
        
        self.assertTrue(result)
        self.assertEqual(self.mock_auth.get_captcha.call_count, 1)

if __name__ == "__main__":
    unittest.main()
