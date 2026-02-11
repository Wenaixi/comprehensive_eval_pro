import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.services.ai_tool import AIModelTool


class TestAITool(unittest.TestCase):
    def test_disabled_returns_empty(self):
        tool = AIModelTool(api_key="", base_url="https://example.test/v1")
        out = tool.chat(model="m", messages=[{"role": "user", "content": "hi"}], max_tokens=1)
        self.assertEqual(out, "")

    def test_chat_builds_payload_and_parses_content(self):
        tool = AIModelTool(api_key="k", base_url="https://example.test/v1")

        class Resp:
            status_code = 200

        def fake_request(session, method, url, **kwargs):
            return {"choices": [{"message": {"content": "ok"}}]}, Resp()

        with mock.patch("comprehensive_eval_pro.services.ai_tool.request_json_response", side_effect=fake_request) as m:
            out = tool.chat(
                model="default:m1",
                messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
                max_tokens=123,
                temperature=0.1,
                timeout=9,
            )

        self.assertEqual(out, "ok")
        _, kwargs = m.call_args
        self.assertEqual(kwargs["timeout"], 9)
        self.assertIn("headers", kwargs)
        self.assertEqual(kwargs["json"]["model"], "m1")
        self.assertEqual(kwargs["json"]["max_tokens"], 123)
        self.assertEqual(kwargs["json"]["temperature"], 0.1)
        self.assertEqual(len(kwargs["json"]["messages"]), 2)

    def test_provider_prefix_resolves(self):
        tool = AIModelTool(api_key="k", base_url="https://example.test/v1")

        class Resp:
            status_code = 200

        def fake_request(session, method, url, **kwargs):
            return {"choices": [{"message": {"content": "ok"}}]}, Resp()

        with mock.patch("comprehensive_eval_pro.services.ai_tool.request_json_response", side_effect=fake_request):
            out = tool.chat(model="default::m1", messages=[{"role": "user", "content": "u"}], max_tokens=1)
        self.assertEqual(out, "ok")

    def test_siliconflow_base_url_env_applies_without_init_args(self):
        old = dict(os.environ)
        try:
            os.environ["SILICONFLOW_API_KEY"] = "k"
            os.environ["CEP_AI_BASE_URL"] = "https://example.test/v1"
            os.environ["CEP_AI_PROVIDER_DEFAULT"] = "siliconflow"
            tool = AIModelTool()

            class Resp:
                status_code = 200

            def fake_request(session, method, url, **kwargs):
                return {"choices": [{"message": {"content": "ok"}}]}, Resp()

            with mock.patch("comprehensive_eval_pro.services.ai_tool.request_json_response", side_effect=fake_request) as m:
                out = tool.chat(model="siliconflow:m1", messages=[{"role": "user", "content": "u"}], max_tokens=1)

            self.assertEqual(out, "ok")
            call_args, _ = m.call_args
            self.assertTrue(call_args[2].startswith("https://example.test/v1/"))
        finally:
            os.environ.clear()
            os.environ.update(old)


if __name__ == "__main__":
    unittest.main()
