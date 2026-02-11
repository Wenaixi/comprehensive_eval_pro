import requests
import os
import time
import logging
import uuid
from comprehensive_eval_pro.utils.http_client import create_session, request_json, request_json_response
from comprehensive_eval_pro.services.vision import VisionService

logger = logging.getLogger("AuthModule")

class ProAuthService:
    """
    专业的 SSO 认证服务 (精简独立版)
    """
    def __init__(self, sso_base="https://www.nazhisoft.com"):
        self.session = create_session()
        self.sso_base = sso_base
        self.token = None
        self.user_info = {}  # 存储完整的用户信息
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": sso_base,
            "Referer": f"{sso_base}/uiStudentLogin/login"
        }
        
        # 初始化运行时目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.captcha_dir = os.path.join(base_dir, "runtime", "captchas")
        os.makedirs(self.captcha_dir, exist_ok=True)
        self._cleanup_old_captchas() # 初始化时清理旧验证码

        self.vision = VisionService()

    def _cleanup_old_captchas(self, max_age_seconds=3600):
        """清理过期的验证码文件（默认 1 小时前）"""
        try:
            now = time.time()
            for f in os.listdir(self.captcha_dir):
                if not f.startswith("captcha_"):
                    continue
                path = os.path.join(self.captcha_dir, f)
                if os.path.isfile(path):
                    if now - os.path.getmtime(path) > max_age_seconds:
                        try:
                            os.remove(path)
                        except:
                            pass
        except Exception as e:
            logger.debug(f"清理验证码失败: {e}")

    def _init_session(self):
        """初始化 Session，确保只初始化一次"""
        if hasattr(self, "_session_initialized") and self._session_initialized:
            return
        try:
            logger.info("正在初始化 SSO 会话...")
            self.session.get(f"{self.sso_base}/uiStudentLogin/login", headers=self.headers, timeout=10)
            self._session_initialized = True
        except Exception as e:
            logger.error(f"初始化 Session 失败: {e}")

    def get_captcha(self, auto_open=False, engine: str = "auto", ai_model: str | None = None) -> tuple[str, str]:
        """获取并识别验证码"""
        self._init_session()
        # 增加随机数防止缓存
        captcha_url = f"{self.sso_base}/kaptcha/kaptcha.jpg?t={int(time.time() * 1000)}"
        
        try:
            # 必须使用当前 Session 获取图片以保持 Cookie 一致
            res = self.session.get(captcha_url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                # 生成唯一的验证码文件名以支持并发
                file_name = f"captcha_{uuid.uuid4().hex[:8]}.jpg"
                img_path = os.path.join(self.captcha_dir, file_name)
                
                with open(img_path, "wb") as f:
                    f.write(res.content)
                
                logger.info(f"验证码已保存至: {img_path}")
                
                # 使用统一的视觉服务进行识别
                ocr_result = self.vision.see(
                    img_path, 
                    task_type="ocr", 
                    engine=engine, 
                    model=ai_model
                )
                logger.info(f"验证码识别结果 ({engine}): {ocr_result}")
                
                if auto_open:
                    if os.name == "nt" and hasattr(os, "startfile"):
                        os.startfile(img_path)
                    else:
                        logger.warning(f"当前环境不支持自动打开图片，请手动查看: {img_path}")
                
                return img_path, ocr_result
        except Exception as e:
            logger.error(f"获取验证码失败: {e}")
        return "", ""

    def validate_captcha(self, captcha_code: str) -> bool:
        """预校验验证码"""
        url = f"{self.sso_base}/uiStudentLogin/validateCaptcha"
        # 必须严格模拟浏览器请求头
        v_headers = self.headers.copy()
        v_headers["Content-Type"] = "application/json;charset=UTF-8"
        
        payload = {"captcha": captcha_code}
        try:
            data = request_json(self.session, "POST", url, json=payload, headers=v_headers, timeout=10, logger=logger)
            if not isinstance(data, dict):
                return False
            # 这里的逻辑要更严谨：只要后端返回成功（通常是 code=1 或 msg="验证码验证通过"）
            if data.get('code') == 1 or "通过" in data.get('msg', ''):
                return True
            logger.warning(f"验证码校验未通过，完整响应: {data}")
            return False
        except Exception as e:
            logger.error(f"验证码校验请求异常: {e}")
            return False

    def get_school_meta(self, username: str) -> dict:
        url = f"{self.sso_base}/teacher/auth/studentLogin/getSchoolIdByStudentNumber?userName={username}"
        try:
            data = request_json(self.session, "POST", url, json={"key": ""}, headers=self.headers, timeout=10, logger=logger)
            if not isinstance(data, dict):
                return {}
            if data.get('code') == 1 and data.get('dataList'):
                item = data['dataList'][0] if isinstance(data['dataList'], list) and data['dataList'] else {}
                if not isinstance(item, dict):
                    return {}
                school_id = item.get('school_id') or item.get('schoolID') or item.get('schoolId')
                school_name = (item.get('NAME') or item.get('name') or item.get('schoolName') or '').strip()
                meta = {}
                if school_id:
                    meta['id'] = str(school_id)
                if school_name:
                    meta['name'] = school_name
                if meta:
                    logger.info(f"成功获取学校信息: {meta.get('id', '')} ({meta.get('name', '未知学校')})")
                return meta
            return {}
        except Exception as e:
            logger.error(f"获取学校信息发生异常: {e}")
            return {}

    def get_school_id(self, username: str) -> str:
        """自动溯源学校 ID"""
        meta = self.get_school_meta(username)
        return (meta.get('id') or '').strip()

    def login(self, username, password, captcha_code, school_id=None) -> bool:
        """执行最终登录并获取 Token"""
        # 1. 如果没有传入 school_id，则获取
        if not school_id:
            school_id = self.get_school_id(username)
        
        if school_id:
            school_id = str(school_id).strip()

        if not school_id:
            logger.error("无法获取学校 ID")
            return False

        # 2. 必须先进行预校验 (SSO 强制要求)
        logger.info(f"正在预校验验证码: {captcha_code}...")
        if not self.validate_captcha(captcha_code):
            logger.error("验证码预校验失败，请重试")
            return False

        # 3. 正式登录
        url = f"{self.sso_base}/teacher/auth/studentLogin/validate"
        payload = {
            "schoolId": school_id,
            "username": username,
            "password": password,
            "captcha": captcha_code
        }
        
        try:
            data, res = request_json_response(self.session, "POST", url, json=payload, headers=self.headers, timeout=10, logger=logger)
            if not isinstance(data, dict) or res is None:
                return False
            if data.get('code') == 1:
                # 增强 Token 捕获逻辑 (究极进化版：支持根目录、returnData 嵌套、Headers 捕获)
                # 1. 尝试从根目录获取
                token = data.get('token') or data.get('data')
                
                # 2. 尝试从 returnData 嵌套获取 (针对最新的 SSO 响应格式)
                if not token and isinstance(data.get('returnData'), dict):
                    token = data.get('returnData', {}).get('token')
                
                # 3. 尝试从响应头获取 (X-Auth-Token)
                if not token:
                    token = res.headers.get("X-Auth-Token") or res.headers.get("x-auth-token")
                
                if token:
                    self.token = token
                    self.user_info = data.get('returnData', {}) # 捕获完整 returnData
                    logger.info("登录成功，Token 已捕获")
                    return True
                else:
                    logger.error("登录成功但未发现 Token，请检查响应结构")
                    return False
            
            logger.error(f"登录失败，完整响应: {data}")
            return False
        except Exception as e:
            logger.error(f"登录请求异常: {e}")
            return False
