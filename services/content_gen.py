import logging
import os
import json
import random
import hashlib
import threading
from ..policy import config
from comprehensive_eval_pro.services.ai_tool import AIModelTool
from comprehensive_eval_pro.services.vision import VisionService

logger = logging.getLogger("ContentGen")

class AIContentGenerator:
    """
    对接 AI API 生成写实内容，并支持本地持久化缓存
    """
    def __init__(self, api_key: str = None, model: str = None):
        self.model = model or config.get_setting("content_gen_model", "deepseek-ai/DeepSeek-V3.2")
        
        # 获取基础 URL
        base_url = config.get_setting("ai_base_url", "https://api.siliconflow.cn/v1", env_name="CEP_AI_BASE_URL")
        
        self.ai = AIModelTool(api_key=api_key, base_url=base_url)
        self.vision = VisionService(ai=self.ai)
        self.lock = threading.Lock()
        
        # 缓存文件路径
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_file = config.get_setting("cache_file", os.path.join(current_dir, "content_cache.json"), env_name="CEP_CACHE_FILE")
        self.cache = self._load_cache()
        
        if not self.ai.enabled():
            logger.warning("未检测到有效 API Key，AI 生成功能将仅依赖缓存或返回默认值。")

    def _get_image_hash(self, image_path):
        """计算图片 MD5 哈希"""
        hasher = hashlib.md5()
        with open(image_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def _clean_ai_content(self, content: str) -> str:
        """清洗 AI 生成的内容，去除常见的废话前缀"""
        if not content:
            return ""
        
        # 移除常见的 AI 开场白
        prefixes = [
            "好的", "根据图片", "任务内容", "这是一段", "心得体会", "：", ":", 
            "我为您生成了", "如下", "如下内容", "。 ", "，"
        ]
        
        cleaned = content.strip()
        # 循环移除开头，直到不再变化
        changed = True
        while changed:
            original = cleaned
            for p in prefixes:
                if cleaned.startswith(p):
                    cleaned = cleaned[len(p):].lstrip(" ，。：:")
            changed = (original != cleaned)
            
        return cleaned.strip()

    def generate_labor_content(self, image_path, task_name, use_cache=True, school_name: str = "学校"):
        """生成劳动教育内容"""
        return self._generate_common_content("labor", image_path, task_name, use_cache, school_name)

    def generate_military_content(self, task_name, use_cache=True, school_name: str = "学校"):
        """生成军事训练/国防教育内容"""
        return self._generate_common_content("military", None, task_name, use_cache, school_name)

    def generate_speech_content(self, task_name, use_cache=True, school_name: str = "学校"):
        """生成演讲/征文内容"""
        return self._generate_common_content("speech", None, task_name, use_cache, school_name)

    def generate_class_meeting_content(self, text_content: str, task_name: str, use_cache=True, school_name: str = "学校"):
        """生成班会记录内容（基于提取的文本）"""
        return self.generate_class_meeting_summary(text_content, task_name, use_cache)

    def _generate_common_content(self, category, image_path, task_name, use_cache, school_name):
        # 统一的内容生成逻辑
        cache_key = f"{category}_{task_name}_{school_name}"
        if use_cache and cache_key in self.cache:
            return random.choice(self.cache[cache_key])

        prompt = f"请作为一名{school_name}的学生，针对'{task_name}'这一{category}活动，写一段100字左右的心得体会。"
        
        try:
            if image_path and category == "labor":
                content = self.vision.see(image_path, task_type="analysis", prompt=prompt)
            else:
                content = self.ai.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            
            content = self._clean_ai_content(content)
            if content:
                self._update_cache(cache_key, content)
                return content
        except Exception as e:
            logger.error(f"AI 生成{category}内容失败: {e}")
            
        return f"在参加了{school_name}组织的{task_name}活动后，我深有感触。通过这次实践，我不仅学到了知识，更锻炼了意志。"

    def generate_class_meeting_summary(self, text_content: str, task_name: str, use_cache=True):
        """
        根据班会文本生成摘要/心得 (纯文本模型逻辑)
        """
        text_hash = hashlib.md5(text_content.encode('utf-8')).hexdigest()
        cache_key = f"TEXT_HASH_{text_hash}"

        if use_cache and cache_key in self.cache and self.cache[cache_key]:
            contents = self.cache[cache_key]
            chosen = random.choice(contents)
            logger.info(f"命中班会文本缓存 (库容量: {len(contents)}): 【{task_name}】")
            return chosen

        logger.info(f"正在分析班会记录: 【{task_name}】...")
        
        default_content = f"通过参加‘{task_name}’主题班会，我学习到了很多相关知识，对自己的成长很有帮助。"
        
        if not self.ai.enabled():
            return default_content

        messages = [
            {"role": "system", "content": "你是一个学生，负责根据班会记录内容撰写100字左右的学习心得。"},
            {"role": "user", "content": f"以下是班会记录内容：\n{text_content[:2000]}\n\n请根据以上内容，以第一人称写一段关于‘{task_name}’的学习心得，语言要朴实、贴近学生身份。严禁废话，直接输出心得内容。"}
        ]

        try:
            content = self.ai.chat(
                model=self.model,
                messages=messages,
                max_tokens=300,
                temperature=0.8
            )
            if not content:
                return default_content
            
            content = self._clean_ai_content(content)
            
            self._update_cache(cache_key, content)
            
            return content
        except Exception as e:
            logger.error(f"AI 生成班会心得异常: {e}")
            return default_content

    def _update_cache(self, key, content):
        """更新缓存并持久化"""
        with self.lock:
            if key not in self.cache:
                self.cache[key] = []
            if content not in self.cache[key]:
                self.cache[key].append(content)
                if len(self.cache[key]) > 5:
                    self.cache[key].pop(0)
                self._save_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载缓存文件失败: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")
