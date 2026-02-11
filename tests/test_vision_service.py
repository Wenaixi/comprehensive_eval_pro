import unittest
import os
import base64
import logging
from unittest.mock import MagicMock, patch
from comprehensive_eval_pro.services.vision import VisionService
from comprehensive_eval_pro.services.ai_tool import AIModelTool

# 配置日志
logging.basicConfig(level=logging.INFO)

class TestVisionService(unittest.TestCase):
    def setUp(self):
        self.ai_mock = MagicMock(spec=AIModelTool)
        self.ai_mock.enabled.return_value = True
        self.vision = VisionService(ai=self.ai_mock)
        
        # 创建一个标准的 100x100 RGB 测试图片
        from PIL import Image as PILImage
        self.test_img = "test_vision.jpg"
        img = PILImage.new('RGB', (100, 100), color=(255, 0, 0))
        img.save(self.test_img, "JPEG")

    def tearDown(self):
        # 清理所有可能的临时文件
        for f in [self.test_img, "test_large.jpg", "test_vision_compressed.jpg", "corrupted.jpg"]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

    def test_corrupted_image_handling(self):
        """测试损坏图片的优雅处理"""
        # 创建一个损坏的图片文件
        corrupted_path = "corrupted.jpg"
        with open(corrupted_path, "wb") as f:
            f.write(b"this is not an image at all")
        
        # 应该返回空字符串而不是报错
        result = self.vision.see(corrupted_path, task_type="ocr")
        self.assertEqual(result, "")

    def test_engine_auto_fallback(self):
        """测试 auto 引擎的降级逻辑 (AI 失败 -> 本地)"""
        self.ai_mock.chat.side_effect = Exception("AI 挂了")
        
        with patch('comprehensive_eval_pro.services.vision.ddddocr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = " local_res "
            mock_ddddocr.DdddOcr.return_value = mock_instance
            self.vision._local_ocr = None
            
            result = self.vision.see(self.test_img, engine="auto", task_type="ocr")
            self.assertEqual(result, "local_res")

    def test_bytes_input(self):
        """测试直接传入字节流"""
        self.ai_mock.chat.return_value = "bytes_ok"
        with open(self.test_img, "rb") as f:
            img_bytes = f.read()
            
        result = self.vision.see(img_bytes, engine="ai", task_type="analysis")
        self.assertEqual(result, "bytes_ok")

    def test_clean_ocr_result(self):
        """测试验证码清洗逻辑"""
        self.assertEqual(self.vision._clean_ocr_result("A b 1 2 !"), "Ab12")
        self.assertEqual(self.vision._clean_ocr_result(None), "")
        self.assertEqual(self.vision._clean_ocr_result(" \n123 "), "123")

    @patch('comprehensive_eval_pro.services.vision.ddddocr')
    def test_run_local(self, mock_ddddocr):
        """测试本地 OCR 调用"""
        if mock_ddddocr is None:
            self.skipTest("ddddocr not installed")
        
        mock_instance = MagicMock()
        mock_instance.classification.return_value = " ab12 "
        mock_ddddocr.DdddOcr.return_value = mock_instance
        
        # 强制重置以触发 mock
        self.vision._local_ocr = None
        result = self.vision._run_local(self.test_img)
        self.assertEqual(result, "ab12")

    def test_run_ai_ocr(self):
        """测试 AI OCR 识别流程"""
        self.ai_mock.chat.return_value = " K8S9 "
        
        # 模拟调用
        result = self.vision.see(self.test_img, task_type="ocr", engine="ai", prompt="识别验证码")
        
        self.assertEqual(result, "K8S9")
        self.ai_mock.chat.assert_called()
        
        # 检查参数
        call_args = self.ai_mock.chat.call_args[1]
        self.assertEqual(call_args['temperature'], 0.0)
        self.assertEqual(call_args['max_tokens'], 32)

    def test_run_ai_analysis(self):
        """测试 AI 视觉描述流程"""
        self.ai_mock.chat.return_value = "这是一个劳动场景。"
        
        result = self.vision.see(self.test_img, task_type="analysis", engine="ai")
        
        self.assertEqual(result, "这是一个劳动场景。")
        call_args = self.ai_mock.chat.call_args[1]
        self.assertEqual(call_args['temperature'], 0.7)
        self.assertEqual(call_args['max_tokens'], 512)

    def test_image_compression_trigger(self):
        """测试图片压缩触发逻辑"""
        # 创建一个较大的文件 (1.1MB)
        large_file = "test_large.jpg"
        with open(large_file, "wb") as f:
            f.write(b"\0" * (1100 * 1024))
        
        # 模拟 AI 返回
        self.ai_mock.chat.return_value = "OK"
        
        # 我们 mock utils.image_convert.compress_image
        with patch('comprehensive_eval_pro.services.vision.compress_image') as mock_compress:
            # 模拟压缩后返回原路径
            mock_compress.return_value = (large_file, False)
            self.vision.see(large_file, engine="ai")
            
            # 验证是否调用了压缩，且 max_size_mb 默认为 1.0
            mock_compress.assert_called()
            args, kwargs = mock_compress.call_args
            self.assertEqual(kwargs['max_size_mb'], 1.0)

    def test_engine_auto_fallback(self):
        """测试 auto 引擎的降级逻辑 (AI 失败 -> 本地)"""
        # AI 返回空
        self.ai_mock.chat.return_value = None
        
        with patch.object(self.vision, '_run_local') as mock_local:
            mock_local.return_value = "local_res"
            result = self.vision.see(self.test_img, engine="auto", task_type="ocr")
            
            self.assertEqual(result, "local_res")
            mock_local.assert_called_once()

    def test_bytes_input(self):
        """测试直接传入字节流"""
        self.ai_mock.chat.return_value = "bytes_ok"
        with open(self.test_img, "rb") as f:
            img_bytes = f.read()
        
        # 明确指定 task_type="analysis"，避免触发验证码清洗逻辑
        result = self.vision.see(img_bytes, engine="ai", task_type="analysis")
        self.assertEqual(result, "bytes_ok")

    def test_corrupted_image_handling(self):
        """测试损坏图片的鲁棒性"""
        corrupted_file = "corrupted.jpg"
        with open(corrupted_file, "wb") as f:
            f.write(b"this is not an image file")
        
        try:
            # 即使图片损坏，也不应抛出异常，而是优雅返回空
            result = self.vision.see(corrupted_file, engine="ai")
            self.assertEqual(result, "")
        finally:
            if os.path.exists(corrupted_file):
                os.remove(corrupted_file)

if __name__ == '__main__':
    unittest.main()
