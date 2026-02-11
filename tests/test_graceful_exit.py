
import unittest
from unittest.mock import patch, MagicMock
import sys
import io
from comprehensive_eval_pro.flows import main

class TestGracefulExit(unittest.TestCase):
    @patch("comprehensive_eval_pro.flows._main_impl")
    def test_keyboard_interrupt_handling(self, mock_impl):
        # 模拟 _main_impl 抛出 KeyboardInterrupt
        mock_impl.side_effect = KeyboardInterrupt()
        
        # 捕获 stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output
        
        try:
            main()
        finally:
            sys.stdout = sys.__stdout__
            
        output = captured_output.getvalue()
        self.assertIn("检测到用户中断 (Ctrl+C)", output)
        self.assertIn("感谢使用", output)

if __name__ == "__main__":
    unittest.main()
