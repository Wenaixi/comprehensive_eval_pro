import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import flows


class DummyTaskMgr:
    def __init__(self):
        self.token = "t"
        self.user_info = {}

    def activate_session(self):
        return True


class TestPrepareAccounts(unittest.TestCase):
    def test_prepare_uses_token_flow_when_available(self):
        accounts = [("u1", "p1")]
        config = {}

        with mock.patch.object(flows, "try_use_token_flow", return_value={"token": "t1", "user_info": {"realName": "A"}, "task_mgr": DummyTaskMgr()}), mock.patch.object(
            flows, "get_account_entry", return_value={"token": "t1", "user_info": {"realName": "A"}}
        ):
            prepared = flows.prepare_accounts_for_selection(
                accounts=accounts,
                config=config,
                sso_base="https://example.com",
            )

        self.assertEqual(prepared[0]["status"], "已就绪")
        self.assertEqual(prepared[0]["token"], "t1")
        self.assertEqual(prepared[0]["real_name"], "A")
        self.assertIsNotNone(prepared[0]["task_mgr"])

    def test_prepare_login_and_persist_when_no_token(self):
        accounts = [("u2", "p2")]
        config = {}

        class DummyAuth:
            def __init__(self, sso_base=None):
                self.sso_base = sso_base
                self.token = "t2"
                self.user_info = {"realName": "B"}

            def get_school_id(self, username):
                return "sid"

            def get_school_meta(self, username):
                return {}

        with mock.patch.object(flows, "try_use_token_flow", return_value=None), mock.patch.object(
            flows, "ProAuthService", DummyAuth
        ), mock.patch.object(flows, "ocr_login_with_retries", return_value=True), mock.patch.object(
            flows, "build_task_manager", return_value=DummyTaskMgr()
        ), mock.patch.object(flows, "get_account_entry", return_value={}):
            prepared = flows.prepare_accounts_for_selection(
                accounts=accounts,
                config=config,
                sso_base="https://example.com",
            )

        self.assertEqual(prepared[0]["status"], "已就绪")

    def test_prepare_school_id_fail(self):
        accounts = [("u3", "p3")]
        config = {}

        class DummyAuth:
            def __init__(self, sso_base=None):
                self.sso_base = sso_base
                self.token = ""
                self.user_info = {}

            def get_school_id(self, username):
                return None

        with mock.patch.object(flows, "try_use_token_flow", return_value=None), mock.patch.object(
            flows, "ProAuthService", DummyAuth
        ):
            prepared = flows.prepare_accounts_for_selection(
                accounts=accounts,
                config=config,
                sso_base="https://example.com",
            )

        self.assertEqual(prepared[0]["status"], "溯源失败")


if __name__ == "__main__":
    unittest.main()
