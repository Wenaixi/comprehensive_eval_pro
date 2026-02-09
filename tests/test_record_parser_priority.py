import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro.utils import record_parser


class TestRecordParserPriority(unittest.TestCase):
    def test_fallback_to_txt_when_excel_empty(self):
        with tempfile.TemporaryDirectory() as d:
            xls_path = os.path.join(d, "a.xls")
            txt_path = os.path.join(d, "b.txt")
            with open(xls_path, "wb") as f:
                f.write(b"x")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("hello")

            def fake_extract(path: str) -> str:
                if path.endswith(".xls"):
                    return ""
                if path.endswith(".txt"):
                    return "hello"
                return ""

            with mock.patch.object(record_parser, "extract_text_from_file", side_effect=fake_extract):
                text, used = record_parser.extract_first_record_text(d)

            self.assertEqual(text, "hello")
            self.assertTrue((used or "").endswith("b.txt"))

    def test_use_excel_when_available(self):
        with tempfile.TemporaryDirectory() as d:
            xls_path = os.path.join(d, "a.xls")
            txt_path = os.path.join(d, "b.txt")
            with open(xls_path, "wb") as f:
                f.write(b"x")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("hello")

            def fake_extract(path: str) -> str:
                if path.endswith(".xls"):
                    return "excel"
                if path.endswith(".txt"):
                    return "hello"
                return ""

            with mock.patch.object(record_parser, "extract_text_from_file", side_effect=fake_extract):
                text, used = record_parser.extract_first_record_text(d)

            self.assertEqual(text, "excel")
            self.assertTrue((used or "").endswith("a.xls"))


if __name__ == "__main__":
    unittest.main()

