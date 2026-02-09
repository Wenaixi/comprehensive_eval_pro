import os
import random
import logging
import requests
import difflib
import re
import unicodedata
from urllib.parse import urlparse
from comprehensive_eval_pro.services.content_gen import AIContentGenerator
from comprehensive_eval_pro.services.file_service import ProFileService
from comprehensive_eval_pro.utils.excel_parser import ExcelParser
from comprehensive_eval_pro.utils.http_client import create_session, request_json, request_json_response

logger = logging.getLogger("TaskManager")

DEFAULT_TIMEOUT = 10

class ProTaskManager:
    """
    专业的任务管理与提交系统
    """
    IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')
    def __init__(self, token: str, base_url: str = "http://139.159.205.146:8280", user_info: dict = None, upload_url: str = None):
        self.token = token
        self.base_url = (base_url or "").rstrip("/")
        self.user_info = user_info or {}
        self.upload_url = upload_url
        self.student_name = self.user_info.get('realName') or self.user_info.get('NAME') or '未知'
        self.dimension_map = {} # ID -> Name 映射
        self.session = create_session()
        self.headers = {
            "X-Auth-Token": token,
            "accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/management",
            "Origin": self.base_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 预设请求头到 Session
        self.session.headers.update(self.headers)
        # 究极修复：同步 Token 到 Cookie，部分业务接口强依赖 Cookie 中的 Token
        parsed = urlparse(self.base_url)
        host = (parsed.hostname or "").strip()
        if host:
            self.session.cookies.set("X-Auth-Token", token, domain=host)
        
        # 初始化文件服务
        self.file_service = ProFileService(self.session, upload_url=self.upload_url)

    def activate_session(self):
        """
        深度激活业务 Session (获取菜单 + 获取学生基本信息)
        """
        try:
            # 如果已经有名字且不是“未知”，则只需静默激活 Session
            if self.student_name and self.student_name != '未知':
                logger.debug(f"使用预存姓名: {self.student_name}，执行静默激活...")
            else:
                logger.info("正在激活业务 Session (获取菜单与学生信息)...")

            # 1. 模拟首页访问，初始化后端 Session 上下文
            self.session.get(f"{self.base_url}/", timeout=DEFAULT_TIMEOUT)
            
            # 2. 模拟菜单点击
            menu_url = f"{self.base_url}/api/studentInfo/getMenu"
            menu_data, menu_resp = request_json_response(self.session, "GET", menu_url, timeout=DEFAULT_TIMEOUT, logger=logger)
            
            # 3. 模拟获取学生信息
            info_url = f"{self.base_url}/api/studentInfo/getMyInfo"
            res, resp = request_json_response(self.session, "GET", info_url, timeout=DEFAULT_TIMEOUT, logger=logger)
            if not isinstance(res, dict):
                return False
            
            if res.get('code') == 1:
                data = res.get('data') or res.get('returnData') or {}
                # 仅在当前为“未知”时尝试更新姓名
                if self.student_name == '未知':
                    self.student_name = data.get('NAME') or data.get('realName') or data.get('studentName')
                    if not self.student_name and isinstance(menu_data, dict):
                        self.student_name = (menu_data.get('data') or {}).get('realName')
                
                self.student_name = self.student_name or '未知'
                logger.info(f"业务 Session 激活成功，当前学生: {self.student_name}")
                return True
        except Exception as e:
            logger.error(f"Session 激活失败: {e}")
        return False

    @staticmethod
    def _normalize_task_name(name: str) -> str:
        return re.sub(r"\s+", "", name or "")

    @classmethod
    def _looks_like_class_meeting(cls, task_name: str, dimension_name: str = "") -> bool:
        name = cls._normalize_task_name(task_name)
        dim = cls._normalize_task_name(dimension_name or "")
        if "班会" in name:
            return True
        dim_hit = any(k in dim for k in ("思想", "品德", "德育", "心理", "班会"))
        if re.search(r"(?:^|[^级])班[《“\"'‘]", name) and dim_hit:
            return True
        return False

    def get_all_tasks(self, force_refresh: bool = False):
        """
        全方位扫描任务
        """
        if force_refresh:
            self.activate_session()
        
        all_tasks = []
        task_ids = set()

        try:
            # 1. 获取真实维度列表并建立映射
            dim_url = f"{self.base_url}/api/studentCircleNew/getDimensions"
            dim_res = request_json(self.session, "GET", dim_url, timeout=DEFAULT_TIMEOUT, logger=logger)
            dimensions = []
            if isinstance(dim_res, dict) and dim_res.get('code') == 1:
                dimensions = dim_res.get('dataList') or dim_res.get('data') or []
            
            # 建立维度映射
            cleaned_dimensions = []
            for d in dimensions:
                raw_id = d.get("id") or d.get("dimensionId")
                if raw_id is None:
                    continue
                d_id = str(raw_id).strip()
                if not d_id or d_id.lower() == "none":
                    continue
                d_name = d.get('name') or d.get('dimensionName') or f"维度{d_id}"
                self.dimension_map[d_id] = d_name
                cleaned_dimensions.append(d)
            dimensions = cleaned_dimensions

            if not dimensions:
                # 兜底常用维度
                dimensions = [{"id": i} for i in range(1, 16)]
            
            logger.info(f"开始扫描 {len(dimensions)} 个业务维度...")

            # 2. 遍历维度获取任务
            for dim in dimensions:
                raw_id = dim.get("id") or dim.get("dimensionId")
                if raw_id is None:
                    continue
                d_id = str(raw_id).strip()
                if not d_id or d_id.lower() == "none":
                    continue
                d_name = self.dimension_map.get(d_id, f"维度{d_id}")
                
                url = f"{self.base_url}/api/studentCircleNew/getCircleStatistics?dimensionId={d_id}"
                try:
                    res = request_json(self.session, "GET", url, timeout=DEFAULT_TIMEOUT, logger=logger)
                    if isinstance(res, dict) and res.get('code') == 1:
                        data = res.get('data', {}) or {}
                        tasks = data.get('taskList') or res.get('dataList') or []
                        for t in tasks:
                            if t.get('id') not in task_ids:
                                t['dimensionId'] = d_id
                                t['dimensionName'] = d_name # 注入维度名称
                                all_tasks.append(t)
                                task_ids.add(t.get('id'))
                except Exception as e:
                    logger.debug(f"维度 {d_id} ({d_name}) 扫描跳过: {e}")

            # 3. 兜底扫描：直接调用 getCircleTask
            if not all_tasks:
                try:
                    task_url = f"{self.base_url}/api/studentCircleNew/getCircleTask"
                    res = request_json(self.session, "GET", task_url, timeout=DEFAULT_TIMEOUT, logger=logger)
                    if isinstance(res, dict) and res.get('code') == 1:
                        data = res.get('data') or {}
                        tasks = res.get('dataList') or data.get('taskList') or []
                        for t in tasks:
                            if t.get('id') not in task_ids:
                                all_tasks.append(t)
                                task_ids.add(t.get('id'))
                except Exception as e:
                    logger.debug(f"兜底任务扫描跳过: {e}")

        except Exception as e:
            logger.error(f"全方位扫描发生异常: {e}")

        return all_tasks

    def _extract_date(self, text):
        """
        从文本中提取日期模式 (如 9.8, 09.08, 2025.9.8)
        """
        if not text:
            return None
        pattern = r'(\d{1,4}\.)?(\d{1,2})\.(\d{1,2})'
        match = re.search(pattern, text)
        if not match:
            return None
        try:
            return int(match.group(2)), int(match.group(3))
        except Exception:
            return None

    @staticmethod
    def _normalize_match_text(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", "", text)
        text = re.sub(r"[，,。．·!！?？:：;；“”\"'‘’《》〈〉()（）【】\[\]{}<>]", "", text)
        return text.lower()

    @classmethod
    def _extract_quoted_title(cls, text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", text)
        patterns = [
            r"《([^》]{1,80})》",
            r"“([^”]{1,80})”",
            r"\"([^\"]{1,80})\"",
            r"『([^』]{1,80})』",
            r"「([^」]{1,80})」",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return cls._normalize_match_text(m.group(1))
        return ""

    def _find_best_matching_folder(self, task_name, base_dir):
        """
        匹配最符合任务名称的文件夹（优先按引号内容匹配）
        """
        if not os.path.exists(base_dir):
            return None
        
        # 获取所有包含资源的有效子文件夹
        all_entries = os.listdir(base_dir)
        folders = []
        for f in all_entries:
            path = os.path.join(base_dir, f)
            if os.path.isdir(path):
                # 检查文件夹是否包含图片或 Excel
                files = os.listdir(path)
                has_res = any(fname.lower().endswith(self.IMAGE_EXTS + ('.xls',)) for fname in files)
                if has_res:
                    folders.append(f)
                    
        if not folders:
            return None
            
        task_date = self._extract_date(task_name)
        task_title = self._extract_quoted_title(task_name)
        task_key = task_title or self._normalize_match_text(task_name)

        scored = []
        for folder in folders:
            folder_title = self._extract_quoted_title(folder)
            folder_key = folder_title or self._normalize_match_text(folder)
            similarity = difflib.SequenceMatcher(None, task_key, folder_key).ratio()
            date_match = 1 if (task_date and self._extract_date(folder) == task_date) else 0
            scored.append((similarity, date_match, len(folder_key), folder))

        scored.sort(reverse=True)
        best = scored[0][3] if scored else None
        return os.path.join(base_dir, best) if best else None

    def submit_task(
        self,
        task,
        ai_generator: AIContentGenerator,
        dry_run: bool = True,
        use_cache: bool = True,
        content_override: str | None = None,
        attachment_ids_override: list[int] | None = None,
    ):
        """
        执行任务提交逻辑
        :param use_cache: 是否使用缓存文案
        """
        task_name = task.get('name', '')
        task_id = task.get('id')
        dim_id = task.get('dimensionId')
        type_id = task.get('circleTypeId')
        dim_name = task.get("dimensionName") or ""

        # 1. 识别任务类型
        is_flag_speech = "国旗下讲话" in task_name
        is_labor_task = "劳动" in task_name
        is_military_task = "军训" in task_name
        is_class_meeting = self._looks_like_class_meeting(task_name, dim_name)
        
        # 2. 获取附件与内容
        attachment_ids = list(attachment_ids_override) if isinstance(attachment_ids_override, list) else []
        target_sub_dir = None
        chosen_img_path = None
        upload_paths = []
        xls_content = ""
        
        # 确定资源目录
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if is_flag_speech:
            target_sub_dir = "国旗下讲话"
        elif is_labor_task:
            target_sub_dir = "劳动"
        elif is_military_task:
            target_sub_dir = "军训"
        elif is_class_meeting:
            # 1. 班会专项处理: 匹配文件夹并解析 Excel
            logger.info(f"检测到班会专项任务: {task_name}")
            # 班会逻辑：模糊匹配文件夹
            base_meeting_dir = os.path.join(current_dir, "assets", "images", "主题班会")
            matched_folder = self._find_best_matching_folder(task_name, base_meeting_dir)
            
            if matched_folder:
                logger.info(f"✅ 班会任务【{task_name}】智能匹配到资源包: {os.path.basename(matched_folder)}")
                # 寻找图片和 Excel
                files = os.listdir(matched_folder)
                imgs = [os.path.join(matched_folder, f) for f in files if f.lower().endswith(self.IMAGE_EXTS)]
                
                if (not attachment_ids) and imgs:
                    chosen_img_path = random.choice(imgs)
                    logger.info(f"📸 已从资源包随机抽取照片: {os.path.basename(chosen_img_path)}")
                    if not dry_run:
                        img_id = self.file_service.upload_image(chosen_img_path)
                        if img_id: attachment_ids.append(img_id)
                    else:
                        attachment_ids.append(888888) # 预览 ID
                        upload_paths.append(chosen_img_path)
                
                if content_override is None:
                    from comprehensive_eval_pro.utils.record_parser import extract_first_record_text

                    xls_content, used_file = extract_first_record_text(matched_folder)
                    if xls_content:
                        logger.info(f"📊 已成功解析班会记录，来源: {os.path.basename(used_file) if used_file else '未知'}，提取文本长度: {len(xls_content)}")
                    else:
                        logger.warning(f"⚠️ 资源包【{os.path.basename(matched_folder)}】内未能解析到可用记录文本，将使用任务名通用生成逻辑")
            else:
                logger.warning(f"❌ 班会任务【{task_name}】未能匹配到任何资源包，请检查 assets/images/主题班会 目录")

        # 通用图片挂载 (针对专项任务)
        if not attachment_ids and (not is_class_meeting) and target_sub_dir:
            img_dir = os.path.join(current_dir, "assets", "images", target_sub_dir)
            if os.path.exists(img_dir):
                imgs = [os.path.join(img_dir, f) for f in os.listdir(img_dir) if f.lower().endswith(self.IMAGE_EXTS)]
                if imgs:
                    chosen_img_path = random.choice(imgs)
                    if not dry_run:
                        img_id = self.file_service.upload_image(chosen_img_path)
                        if img_id: 
                            attachment_ids.append(img_id)
                            logger.info(f"成功为任务【{task_name}】从文件夹【{target_sub_dir}】挂载图片附件 ID: {img_id}")
                    else:
                        attachment_ids.append(999999) 
                        upload_paths.append(chosen_img_path)

        # 3. 内容生成
        if content_override is not None:
            content = str(content_override)
        else:
            if is_labor_task and chosen_img_path:
                content = ai_generator.generate_labor_content(chosen_img_path, task_name, use_cache=use_cache)
            elif is_military_task:
                content = ai_generator.generate_military_content(task_name, use_cache=use_cache)
            elif is_class_meeting:
                if xls_content:
                    content = ai_generator.generate_class_meeting_content(xls_content, task_name, use_cache=use_cache)
                else:
                    content = ai_generator.generate_speech_content(task_name, use_cache=use_cache)
            else:
                content = ai_generator.generate_speech_content(task_name, use_cache=use_cache)
            
        if not content:
            content = f"参加了{task_name}活动，收获颇丰。"

        # 4. 组装 Payload (像素级复刻实战 HAR)
        # 提取学生年级和班级信息 (用于班会地点)
        student_info = self.user_info.get('studentSchoolInfo', {})
        grade_name = student_info.get('gradeName', '高一')
        class_name = student_info.get('className', '八班')
        
        # 智能拼接：如果班级名中已包含年级名，则不重复拼接
        if grade_name in class_name:
            full_class_name = class_name
        else:
            full_class_name = f"{grade_name}{class_name}"

        # 核心 Payload 参数对齐
        is_labor_or_military = is_labor_task or is_military_task
        
        payload = {
            "id": None, 
            "name": "班会" if is_class_meeting else ("" if is_military_task else task_name), 
            "hostName": "", 
            "circleDate": "", 
            "rank": "", 
            "level": "5" if is_labor_task else "", 
            "content": content, 
            "pictureList": attachment_ids, 
            "circleTaskId": task_id,
            "circleTypeId": type_id, 
            "dimensionId": dim_id, 
            "hours": 1.0 if is_class_meeting else (32.0 if is_military_task else (2.0 if is_labor_task else 0.5)), 
            "circleBeginDate": "",
            "circleEndDate": "", 
            "checkResult": "1" if is_military_task else "", 
            "patentType": "", 
            "patentNum": "", 
            "address": full_class_name if is_class_meeting else ("福清一中" if is_labor_or_military else ""), 
            "termName": "", 
            "activityName": "", 
            "sportsName": "", 
            "teamName": "", 
            "orgName": "福清一中" if is_labor_or_military else "", 
            "resultsName": "", 
            "obtainTime": "", 
            "specialtyTechnology": "", 
            "playRole": "3" if (is_class_meeting or not is_labor_or_military) else "", 
            "likeSpecialty1": "", 
            "likeSpecialty2": "", 
            "likeSpecialty3": "",
            "isCheck": "0", 
            "isCircle": "1" 
        }

        if dry_run:
            return {"code": 1, "msg": "预览生成成功", "payload": payload, "upload_paths": upload_paths}

        try:
            url = f"{self.base_url}/api/studentCircleNew/addCircle"
            res = request_json(self.session, "POST", url, json=payload, timeout=20, logger=logger)
            return res if isinstance(res, dict) else {"code": 0, "msg": "提交失败：响应解析异常"}
        except Exception as e:
            return {"code": 0, "msg": f"提交异常: {e}"}
