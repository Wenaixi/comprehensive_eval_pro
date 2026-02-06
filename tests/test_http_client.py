import os
import sys
import unittest
from unittest.mock import MagicMock

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.utils.http_client import create_session, request_json, request_json_response


class TestHttpClient(unittest.TestCase):
    def test_create_session_returns_session(self):
        session = create_session(retries=0)
        self.assertIsInstance(session, requests.Session)

    def test_request_json_success(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"code": 1, "data": {"ok": True}}
        session.request.return_value = resp

        data = request_json(session, "GET", "https://example.test/api", timeout=1)
        self.assertEqual(data, {"code": 1, "data": {"ok": True}})

    def test_request_json_non_json(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.side_effect = ValueError("no json")
        session.request.return_value = resp

        data = request_json(session, "GET", "https://example.test/api", timeout=1)
        self.assertIsNone(data)

    def test_request_json_request_exception(self):
        session = MagicMock(spec=requests.Session)
        session.request.side_effect = requests.RequestException("boom")

        data = request_json(session, "GET", "https://example.test/api", timeout=1)
        self.assertIsNone(data)

    def test_request_json_response_returns_response(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"code": 1}
        session.request.return_value = resp

        data, raw = request_json_response(session, "POST", "https://example.test/api", timeout=1, json={"x": 1})
        self.assertEqual(data, {"code": 1})
        self.assertIs(raw, resp)


if __name__ == "__main__":
    unittest.main()
