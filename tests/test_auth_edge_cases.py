import unittest
from unittest.mock import MagicMock, patch
from comprehensive_eval_pro.services.auth import ProAuthService

class TestAuthEdgeCases(unittest.TestCase):
    def setUp(self):
        self.auth = ProAuthService()
        self.auth.session = MagicMock()

    def test_get_school_meta_malformed_json(self):
        """测试后端返回非 JSON 或格式错误时的情况"""
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.side_effect = Exception("Not JSON")
        mock_res.text = "Invalid JSON"
        self.auth.session.request.return_value = mock_res
        
        meta = self.auth.get_school_meta("u1")
        self.assertEqual(meta, {})

    def test_get_school_meta_empty_data_list(self):
        """测试 dataList 为空时的情况"""
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"code": 1, "dataList": []}
        self.auth.session.request.return_value = mock_res
        
        meta = self.auth.get_school_meta("u1")
        self.assertEqual(meta, {})

    def test_login_integer_school_id(self):
        """测试传入整数类型的 school_id 是否能正确处理"""
        # 模拟 validate_captcha 成功
        with patch.object(self.auth, 'validate_captcha', return_value=True):
            # 模拟 login 响应
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_res.json.return_value = {"code": 1, "token": "test-token"}
            mock_res.headers = {}
            # 必须让 session.request 返回这个 mock_res
            self.auth.session.request.return_value = mock_res
            
            # 传入整数 school_id
            success = self.auth.login("u1", "p1", "1234", school_id=12345)
            
            self.assertTrue(success)
            self.assertEqual(self.auth.token, "test-token")
            # 验证最终发送给后端的 payload 中 schoolId 是否被转为字符串
            args, kwargs = self.auth.session.request.call_args
            self.assertEqual(kwargs['json']['schoolId'], "12345")

if __name__ == '__main__':
    unittest.main()
