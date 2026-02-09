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


if __name__ == "__main__":
    unittest.main()

