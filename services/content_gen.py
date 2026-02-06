import requests
import logging
import os
import json
import random
import hashlib
import base64

from comprehensive_eval_pro.utils.http_client import create_session, request_json_response

logger = logging.getLogger("ContentGen")

class AIContentGenerator:
    """
    对接硅基流动 (SiliconFlow) API 生成写实内容，并支持本地持久化缓存
    """
    def __init__(self, api_key: str = None, model: str = "deepseek-ai/DeepSeek-V3.2"):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
        self.model = model
        self.vision_model = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
        self.url = "https://api.siliconflow.cn/v1/chat/completions"
        self.session = create_session(retries=0)
        
        # 缓存文件路径
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_file = os.getenv("CEP_CACHE_FILE") or os.path.join(current_dir, "content_cache.json")
        self.cache = self._load_cache()
        
        if not self.api_key:
            logger.warning("未检测到 SILICONFLOW_API_KEY，AI 生成功能将仅依赖缓存或返回默认值。")

    def _get_image_hash(self, image_path):
        """计算图片 MD5 哈希"""
        hasher = hashlib.md5()
        with open(image_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def _encode_image(self, image_path):
        """将图片转为 Base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def generate_labor_content(self, image_path, task_name, use_cache=True):
        """
        根据劳动图片生成心得体会 (视觉模型逻辑)
        :param image_path: 图片路径
        :param use_cache: 是否使用基于图片哈希的缓存
        """
        img_hash = self._get_image_hash(image_path)
        cache_key = f"IMG_HASH_{img_hash}"

        # 1. 检查图片哈希缓存
        if use_cache and cache_key in self.cache and self.cache[cache_key]:
            contents = self.cache[cache_key]
            chosen = random.choice(contents)
            logger.info(f"命中图片视觉缓存 (库容量: {len(contents)}): 【{task_name}】")
            return chosen

        logger.info(f"正在通过视觉模型 {self.vision_model} 分析劳动图片...")
        
        if not self.api_key:
            return f"我在福清一中参加了{task_name}活动，通过劳动体会到了付出的快乐。"

        base64_image = self._encode_image(image_path)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"我在福清一中参加了图片上的劳动，然后给我一份心得体会，不要多余内容，100字左右"

        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个学生。直接输出心得体会正文，严禁包含'好的'、'根据图片'、'我认为'等任何前缀或解释性文字。"
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.7
        }

        try:
            res_data, response = request_json_response(self.session, "POST", self.url, json=payload, headers=headers, timeout=60, logger=logger)
            if response is not None and response.status_code == 200 and isinstance(res_data, dict):
                choices = res_data.get("choices") or []
                content = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
                if not content:
                    return f"我在福清一中参加了{task_name}活动，通过劳动体会到了付出的快乐。"
                # 去除可能的 AI 引导词
                content = content.replace("好的，根据图片和任务内容：", "").strip()
                
                # 2. 更新并保存缓存
                if cache_key not in self.cache:
                    self.cache[cache_key] = []
                if content not in self.cache[cache_key]:
                    self.cache[cache_key].append(content)
                self._save_cache()
                
                return content
            else:
                logger.error(f"视觉模型响应错误: {res_data}")
        except Exception as e:
            logger.error(f"视觉模型请求异常: {e}")
            
        return f"我在福清一中参加了{task_name}活动，通过劳动体会到了付出的快乐。"

    def generate_military_content(self, task_name, use_cache=True):
        """
        根据军训任务名称生成心得体会 (文本模型逻辑，与国旗下讲话一致)
        :param task_name: 任务名称
        :param use_cache: 是否使用缓存
        """
        # 视觉逻辑已弃用，改为直接复用文本生成逻辑
        return self.generate_speech_content(task_name, use_cache=use_cache)

    def generate_class_meeting_content(self, xls_content, task_name, use_cache=True):
        """
        根据班会 Excel 内容生成心得体会 (文本摘要模式)
        :param xls_content: 从 Excel 提取的文本内容
        :param task_name: 任务名称 (用于缓存键)
        :param use_cache: 是否使用缓存
        """
        # 使用任务名称作为缓存键
        if use_cache and task_name in self.cache and self.cache[task_name]:
            contents = self.cache[task_name]
            chosen = random.choice(contents)
            logger.info(f"命中班会心得缓存 (库容量: {len(contents)}): 【{task_name}】")
            return chosen

        logger.info(f"正在基于 Excel 内容生成班会心得: 【{task_name}】...")
        
        if not self.api_key:
            return f"我参加了{task_name}，通过这次班会学到了很多。"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"以下是班会记录的内容，请帮我总结成一份100字左右的心得体会。要求：以第一人称撰写，语言通顺，体现核心收获，不要包含'好的'、'总结如下'等前缀。\n\n内容：\n{xls_content}"

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一个学生。直接输出心得体会正文，严禁包含任何前缀或解释性文字。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 400,
            "temperature": 0.7
        }

        try:
            res_data, response = request_json_response(self.session, "POST", self.url, json=payload, headers=headers, timeout=60, logger=logger)
            if response is not None and response.status_code == 200 and isinstance(res_data, dict):
                choices = res_data.get("choices") or []
                content = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
                if not content:
                    return f"我参加了{task_name}，通过这次班会学到了很多。"
                
                # 缓存
                if task_name not in self.cache:
                    self.cache[task_name] = []
                if content not in self.cache[task_name]:
                    self.cache[task_name].append(content)
                self._save_cache()
                
                return content
            else:
                logger.error(f"班会 AI 生成错误: {res_data}")
        except Exception as e:
            logger.error(f"班会 AI 请求异常: {e}")
            
        return f"我参加了{task_name}，通过这次班会学到了很多。"

    def _load_cache(self):
        """加载本地缓存 (支持一对多列表结构)"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 兼容性处理：如果旧缓存是字符串，自动转为列表
                    for k, v in data.items():
                        if isinstance(v, str):
                            data[k] = [v]
                    return data
            except Exception as e:
                logger.error(f"加载缓存文件失败: {e}")
        return {}

    def _save_cache(self):
        """保存到本地缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"保存缓存文件失败: {e}")

    def generate_speech_content(self, task_name, use_cache=True):
        """
        生成心得体会
        :param task_name: 任务名称
        :param use_cache: 是否优先使用缓存。如果为 False，则生成新的并追加到缓存库。
        """
        # 1. 检查并使用缓存
        if use_cache and task_name in self.cache and self.cache[task_name]:
            contents = self.cache[task_name]
            # 随机选择一个文案以增加多样性，或者是轮询
            chosen = random.choice(contents)
            logger.info(f"命中本地究极库 (库容量: {len(contents)}): 【{task_name}】")
            return chosen

        logger.info(f"正在获取新文案 (多样性模式: {'开启' if not use_cache else '库为空'})... ")
        
        # 针对军训任务进行微调
        if "军训" in task_name:
            prompt = f"我在福清一中参加了‘{task_name}’活动，请以此为主题给我一份心得体会，要求充满正能量，体现拼搏精神，不要多余内容，150字左右"
            system_msg = "你是一个刚参加完军训的高中生。直接输出心得体会正文，严禁包含'好的'、'根据任务'、'我认为'等任何前缀或解释性文字。"
            max_tokens = 500
        else:
            prompt = f"请为名为‘{task_name}’的校园活动生成一段心得体会。要求：主题明确，情感真挚，字数在100字左右。"
            system_msg = "你是一个优秀的中学生，擅长撰写校园活动心得体会。"
            max_tokens = 200
        
        if not self.api_key:
            return ""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }

        try:
            res_data, response = request_json_response(self.session, "POST", self.url, json=payload, headers=headers, timeout=30, logger=logger)
            if response is not None and response.status_code == 200 and isinstance(res_data, dict):
                choices = res_data.get("choices") or []
                content = ((choices[0].get("message") or {}).get("content") or "").strip() if choices else ""
                if not content:
                    return ""
                logger.info("AI 内容生成成功")
                
                # 2. 更新并保存缓存 (追加模式)
                if task_name not in self.cache:
                    self.cache[task_name] = []
                
                # 只有当文案不重复时才添加
                if content not in self.cache[task_name]:
                    self.cache[task_name].append(content)
                    self._save_cache()
                    logger.info(f"新文案已归档至究极库，当前库容量: {len(self.cache[task_name])}")
                
                return content
            else:
                if isinstance(res_data, dict):
                    logger.error(f"AI 生成失败: {res_data.get('message', '未知错误')}")
                else:
                    logger.error("AI 生成失败: 响应解析异常")
                return ""
        except Exception as e:
            logger.error(f"AI 请求发生异常: {e}")
            return ""

if __name__ == "__main__":
    # 测试代码结构
    gen = AIContentGenerator(api_key="YOUR_API_KEY")
    # print(gen.generate_speech_content("国旗下讲话—以笔为剑 决胜期末"))
