import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_eval_pro import main as app_main


class TestAccountsFile(unittest.TestCase):
    def test_load_accounts_from_txt_parses_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "accounts.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("\n")
                f.write("# comment\n")
                f.write("user1 pass1\n")
                f.write("user2    pass2   extra\n")
                f.write("badlineonlyuser\n")
            accounts = app_main.load_accounts_from_txt(p)
            self.assertEqual(accounts, [("user1", "pass1"), ("user2", "pass2")])


if __name__ == "__main__":
    unittest.main()

