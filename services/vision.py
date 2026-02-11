import base64
import logging
import os
import threading
from typing import List, Optional, Union, Any

from ..policy import config
from comprehensive_eval_pro.utils.image_convert import compress_image, cleanup_temp_file

logger = logging.getLogger("VisionService")

try:
    import ddddocr
except ImportError:
    ddddocr = None


class VisionService:
    """
    Universal Vision 3.0: 统一视觉服务总署
    整合 AI (多模型轮询)、本地 (ddddocr) 与手动模式，支持图片自动压缩。
    """

    def __init__(self, ai: Optional[Any] = None):
        from .ai_tool import AIModelTool
        self.ai = ai or AIModelTool()
        self._local_ocr = None
        self._local_ocr_lock = threading.Lock()
        
        # 预加载配置
        self.default_ai_models = config.get_setting("ocr_models", [
            "siliconflow:PaddlePaddle/PaddleOCR-VL-1.5",
            "siliconflow:deepseek-ai/DeepSeek-OCR"
        ], env_name="CEP_OCR_MODELS")
        
        self.vision_model = config.get_setting("vision_model", "Qwen/Qwen3-Omni-30B-A3B-Instruct", env_name="CEP_VISION_MODEL")

    def _get_env_list(self, key: str) -> List[str]:
        # 此方法不再建议直接使用，保留仅为兼容性
        val = config.get_setting(key.lower().replace("cep_", ""), "", env_name=key)
        if isinstance(val, list):
            return val
        return [x.strip() for x in str(val).split(",") if x.strip()]

    def _get_local_ocr(self):
        if not ddddocr:
            return None
        with self._local_ocr_lock:
            if self._local_ocr is None:
                try:
                    self._local_ocr = ddddocr.DdddOcr(show_ad=False)
                except Exception as e:
                    logger.warning(f"本地 OCR (ddddocr) 初始化失败: {e}")
            return self._local_ocr

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def see(
        self,
        image_source: Union[str, bytes, List[Union[str, bytes]]],
        task_type: str = "ocr",
        engine: str = "auto",
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_size_mb: float = 1.0,
        timeout: int = 60
    ) -> str:
        """
        统一视觉接口
        :param image_source: 图片路径、字节流或其列表
        :param task_type: 'ocr' 或 'analysis'
        """
        sources = image_source if isinstance(image_source, list) else [image_source]
        processed_paths = []
        cleanups = []
        result = "" # 确保变量初始化
        
        try:
            # 1. 准备并压缩所有图片
            is_captcha = (task_type == "ocr" and "验证码" in (prompt or ""))
            for src in sources:
                temp_p = None
                cleanup = False
                try:
                    if isinstance(src, bytes):
                        import tempfile
                        fd, temp_p = tempfile.mkstemp(suffix=".jpg")
                        os.close(fd)
                        with open(temp_p, "wb") as f:
                            f.write(src)
                        cleanup = True
                    else:
                        temp_p = src

                    if not temp_p or not os.path.exists(temp_p):
                        logger.warning(f"图片路径无效，跳过: {temp_p}")
                        continue

                    proc_p, comp_cleanup = compress_image(temp_p, max_size_mb=max_size_mb, is_captcha=is_captcha)
                    if not proc_p:
                        logger.warning(f"图片预处理失败（可能损坏），跳过该图片: {temp_p}")
                        if cleanup: cleanup_temp_file(temp_p, True)
                        continue

                    processed_paths.append(proc_p)
                    # 记录清理逻辑
                    if cleanup: 
                        cleanups.append((temp_p, True))
                    if comp_cleanup:
                        cleanups.append((proc_p, True))
                except Exception as e:
                    logger.error(f"处理单张图片时异常: {e}")
                    if cleanup and temp_p: cleanup_temp_file(temp_p, True)

            # 2. 如果没有任何有效图片，直接返回
            if not processed_paths:
                logger.error("无有效图片可供视觉解析")
                return ""

            # 3. 执行引擎逻辑
            engine = engine.lower()
            if engine == "manual": return ""

            # 本地引擎仅支持单图 OCR
            if (engine == "local" or (engine == "auto" and task_type == "ocr" and not self.ai.enabled())) and len(processed_paths) == 1:
                result = self._run_local(processed_paths[0])
                if result: return result

            if engine in {"ai", "auto"}:
                result = self._run_ai(
                    processed_paths, 
                    task_type=task_type, 
                    prompt=prompt, 
                    model_override=model,
                    timeout=timeout
                )
                if result: return result
                
                if engine == "auto" and task_type == "ocr" and len(processed_paths) == 1:
                    result = self._run_local(processed_paths[0])
            
            return result

        except Exception as e:
            logger.error(f"VisionService.see 异常: {e}")
            return ""
        finally:
            for p, c in cleanups:
                cleanup_temp_file(p, c)

    def _clean_ocr_result(self, text: Union[str, None]) -> str:
        """清理 OCR 结果，仅保留字母数字"""
        if text is None:
            return ""
        text_str = str(text)
        return "".join([ch for ch in text_str if ch.isalnum()])

    def _run_local(self, image_path: str) -> str:
        ocr = self._get_local_ocr()
        if not ocr:
            return ""
        try:
            with open(image_path, "rb") as f:
                res = ocr.classification(f.read())
                if res:
                    res = self._clean_ocr_result(res)
                    logger.info(f"本地 OCR 识别成功: {res}")
                    return res
        except Exception as e:
            logger.debug(f"本地 OCR 异常: {e}")
        return ""

    def _run_ai(
        self, 
        image_paths: List[str], 
        task_type: str, 
        prompt: Optional[str], 
        model_override: Optional[str],
        timeout: int
    ) -> str:
        if not self.ai.enabled():
            return ""

        # 确定 Prompt
        if not prompt:
            if task_type == "ocr":
                prompt = "识别图片中的验证码字符。直接输出字符本身，不要任何解释、空格或换行。"
            else:
                prompt = "描述这张图片的内容。"
        
        # 预先进行 Base64 编码，避免在多模型轮询中重复读取磁盘
        image_contents = []
        for p in image_paths:
            try:
                b64 = self._encode_image(p)
                image_contents.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            except Exception as e:
                logger.error(f"图片编码失败: {p} ({e})")
        
        if not image_contents:
            return ""

        # 准备消息体
        user_content = [{"type": "text", "text": prompt}] + image_contents
        
        # 确定模型列表
        models = [model_override] if model_override else self.default_ai_models
        if task_type == "analysis" and not model_override:
            models = [self.vision_model] + self.default_ai_models

        for m in models:
            if not m: continue
            try:
                logger.info(f"正在尝试 AI 视觉解析 (模型: {m}, 图片数: {len(image_paths)})...")
                content = self.ai.chat(
                    model=m,
                    messages=[
                        {"role": "system", "content": "你是一个专业的视觉助手。"},
                        {"role": "user", "content": user_content},
                    ],
                    max_tokens=512 if task_type == "analysis" else 32,
                    temperature=0.0 if task_type == "ocr" else 0.7,
                    timeout=timeout,
                )
                if content:
                    content = str(content).strip()
                    # 如果是验证码，做下清洗
                    if task_type == "ocr" and "验证码" in prompt:
                        content = self._clean_ocr_result(content)
                    logger.info(f"AI 视觉解析成功 ({m})")
                    return content
            except Exception as e:
                logger.warning(f"AI 模型 {m} 请求失败: {e}")
        
        return ""
