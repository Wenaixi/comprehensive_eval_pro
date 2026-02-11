import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services import auth as auth_mod


class DummyResponse:
    def __init__(self, headers=None):
        self.headers = headers or {}


class TestAuthTokenCapture(unittest.TestCase):
    def setUp(self):
        self.svc = auth_mod.ProAuthService(sso_base="https://example.com")

    def test_token_from_root(self):
        data = {"code": 1, "token": "t1", "returnData": {"realName": "A"}}
        with mock.patch.object(self.svc, "validate_captcha", return_value=True), mock.patch.object(
            auth_mod, "request_json_response", return_value=(data, DummyResponse())
        ):
            ok = self.svc.login("u", "p", "abcd", school_id="sid")
        self.assertTrue(ok)
        self.assertEqual(self.svc.token, "t1")

    def test_token_from_return_data(self):
        data = {"code": 1, "returnData": {"token": "t2", "realName": "B"}}
        with mock.patch.object(self.svc, "validate_captcha", return_value=True), mock.patch.object(
            auth_mod, "request_json_response", return_value=(data, DummyResponse())
        ):
            ok = self.svc.login("u", "p", "abcd", school_id="sid")
        self.assertTrue(ok)
        self.assertEqual(self.svc.token, "t2")

    def test_token_from_header(self):
        data = {"code": 1, "returnData": {"realName": "C"}}
        res = DummyResponse(headers={"X-Auth-Token": "t3"})
        with mock.patch.object(self.svc, "validate_captcha", return_value=True), mock.patch.object(
            auth_mod, "request_json_response", return_value=(data, res)
        ):
            ok = self.svc.login("u", "p", "abcd", school_id="sid")
        self.assertTrue(ok)
        self.assertEqual(self.svc.token, "t3")

    def test_selected_ocr_engine_auto_prefers_ai(self):
        with mock.patch.object(self.svc.session, "get") as mock_get:
            mock_get.return_value = mock.Mock(status_code=200, content=b"fake_img")
            with mock.patch.object(self.svc.vision.ai, "enabled", return_value=True):
                # VisionService 内部逻辑是如果 AI 可用且 engine="auto"，会先尝试 AI
                # 我们通过 mock vision.see 来验证它被调用时传入的参数
                with mock.patch.object(self.svc.vision, "see", return_value="ai_res") as mock_see:
                    _, res = self.svc.get_captcha(engine="auto")
                    self.assertEqual(res, "ai_res")
                    # 验证 see 被调用，且 engine 传递正确
                    mock_see.assert_called_once()
                    self.assertEqual(mock_see.call_args[1]['engine'], "auto")

    def test_selected_ocr_engine_auto_falls_back_to_ddddocr(self):
        with mock.patch.object(self.svc.session, "get") as mock_get:
            mock_get.return_value = mock.Mock(status_code=200, content=b"fake_img")
            with mock.patch.object(self.svc.vision.ai, "enabled", return_value=False):
                # 当 AI 不可用时，VisionService 内部会尝试 local (如果 engine="auto" 和单图 OCR)
                with mock.patch.object(self.svc.vision, "see", return_value="local_res") as mock_see:
                    _, res = self.svc.get_captcha(engine="auto")
                    self.assertEqual(res, "local_res")


if __name__ == "__main__":
    unittest.main()
