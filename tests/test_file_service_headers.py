import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests

from comprehensive_eval_pro.services.file_service import ProFileService


class TestFileServiceHeaders(unittest.TestCase):
    def test_upload_does_not_inherit_business_token_headers(self):
        business_session = requests.Session()
        business_session.headers["X-Auth-Token"] = "secret"

        svc = ProFileService(session=business_session, upload_url="http://example.com/upload")

        with tempfile.TemporaryDirectory() as d:
            img_path = os.path.join(d, "a.jpg")
            with open(img_path, "wb") as f:
                f.write(b"\xff\xd8\xff\xd9")

            def fake_request_json(session, method, url, **kwargs):
                self.assertFalse("X-Auth-Token" in session.headers)
                return {"code": 1, "returnData": {"id": 123}}

            with mock.patch("comprehensive_eval_pro.services.file_service.request_json", side_effect=fake_request_json):
                img_id = svc.upload_image(img_path)

        self.assertEqual(img_id, 123)


if __name__ == "__main__":
    unittest.main()

