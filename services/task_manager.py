import os
import random
import logging
import threading
import requests
import difflib
import re
import unicodedata
import base64
import json
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
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
    DOC_EXTS = ('.xls', '.xlsx', '.docx', '.doc', '.txt', '.pdf')
    RESOURCE_EXTS = IMAGE_EXTS + DOC_EXTS
    # 语义黑名单：包含这些词的任务一律排除在“四大专项”之外
    SPECIAL_TASK_BLACKLIST = [
        "志愿者", "志愿服务", "评价", "考核", "打卡", "学时", 
        "证书", "测评", "辅导", "公示", "自我评价", "互评", "导师",
        "作业", "试卷", "习题", "考试", "周报"
    ]
    # 全局班会记录解析缓存 (类级别静态变量)，实现“霸道缓存”逻辑：解析一次，全校复用
    _GLOBAL_RECORD_CACHE = {}
    _RECORD_CACHE_LOCK = threading.Lock()

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
        self._cached_school = None

    @staticmethod
    def _sanitize_path_component(text: str) -> str:
        s = (text or "").strip()
        if not s:
            return ""
        s = unicodedata.normalize("NFKC", s)
        s = re.sub(r"[\\/:*?\"<>|]", "_", s)
        s = re.sub(r"\s+", "", s)
        return s.strip("._") or s

    def _student_school_info(self) -> dict:
        info = self.user_info.get("studentSchoolInfo") if isinstance(self.user_info, dict) else {}
        return info if isinstance(info, dict) else {}

    def _school_name(self) -> str:
        """
        获取学校名称，增强对不同字段名的适配，并实现实例级缓存与自动回填
        """
        if self._cached_school:
            return self._cached_school

        # 究极适配：定义所有可能的学校字段名
        possible_keys = [
            "schoolName", "SCHOOL_NAME", "school", "unitName", "UNIT_NAME", 
            "orgName", "ORG_NAME", "deptName", "DEPT_NAME", "school_name"
        ]
        
        # 1. 从学生学校信息子对象找
        info = self._student_school_info()
        name = ""
        for k in possible_keys:
            if info.get(k):
                name = str(info[k]).strip()
                break
        
        # 2. 从根 user_info 找
        if not name:
            for k in possible_keys:
                if self.user_info.get(k):
                    name = str(self.user_info[k]).strip()
                    break

        # 3. 从 Token 找
        if not name:
            token = (getattr(self, "token", None) or "").strip()
            if token.count(".") == 2:
                try:
                    payload_b64 = token.split(".", 2)[1]
                    payload_b64 += "=" * (-len(payload_b64) % 4)
                    payload_raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
                    payload = json.loads(payload_raw.decode("utf-8")) if payload_raw else {}
                    if isinstance(payload, dict):
                        info2 = payload.get("studentSchoolInfo") if isinstance(payload.get("studentSchoolInfo"), dict) else payload
                        for k in possible_keys:
                            if isinstance(info2, dict) and info2.get(k):
                                name = str(info2[k]).strip()
                                break
                except Exception:
                    pass
            
        # 4. 环境变量兜底
        if not name:
            from comprehensive_eval_pro.policy import config
            name = config.get_setting("default_school", "", env_name="CEP_DEFAULT_SCHOOL").strip()
            
        if name:
            self._cached_school = name
            # 究极回填：如果 user_info 缺失学校信息，自动补全，以便 flows.py 持久化到 config.json
            ssi = self.user_info.setdefault("studentSchoolInfo", {})
            if isinstance(ssi, dict) and not ssi.get("schoolName"):
                ssi["schoolName"] = name
            elif not isinstance(ssi, dict):
                # 如果 ssi 不是字典（异常情况），直接放根目录
                if not self.user_info.get("schoolName"):
                    self.user_info["schoolName"] = name

        return name

    def _grade_name(self) -> str:
        return (self._student_school_info().get("gradeName") or "").strip()

    def _class_display(self) -> str:
        info = self._student_school_info()
        grade_name = (info.get("gradeName") or "").strip()
        class_name = (info.get("className") or "").strip()
        if not grade_name and not class_name:
            return ""
        if grade_name and class_name and grade_name in class_name:
            return class_name
        return f"{grade_name}{class_name}".strip()

    def _has_any_images(self, folder: str) -> bool:
        if not folder or not os.path.isdir(folder):
            return False
        try:
            for f in os.listdir(folder):
                p = os.path.join(folder, f)
                if os.path.isfile(p) and f.lower().endswith(self.IMAGE_EXTS):
                    return True
        except Exception:
            return False
        return False

    def _list_images(self, folder: str) -> list[str]:
        if not folder or not os.path.isdir(folder):
            return []
        out = []
        try:
            for f in os.listdir(folder):
                p = os.path.join(folder, f)
                if os.path.isfile(p) and f.lower().endswith(self.IMAGE_EXTS):
                    out.append(p)
        except Exception:
            return []
        return out

    def _pure_class_name(self) -> str:
        info = self._student_school_info()
        grade_name = (info.get("gradeName") or "").strip()
        class_name = (info.get("className") or "").strip()
        if grade_name and class_name and class_name.startswith(grade_name):
            # 剥离年级前缀，例如 "高一八班" -> "八班"
            pure = class_name[len(grade_name):].strip()
            if pure:
                return pure
        return class_name

    def _pick_image_path(self, sub_dir: str, task_name: str = "", base_assets_dir: str | None = None) -> str | None:
        """
        根据任务类型子目录寻找一张随机图片，支持任务专项路径逻辑。
        """
        if base_assets_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_assets_dir = os.path.join(current_dir, "assets")
        
        school_dir = self._sanitize_path_component(self._school_name())
        grade_dir = self._sanitize_path_component(self._grade_name())
        class_dir = self._sanitize_path_component(self._pure_class_name())

        candidates = []
        
        # 专项逻辑：国旗下讲话
        if sub_dir == "国旗下讲话":
            if school_dir:
                candidates.append(os.path.join(base_assets_dir, sub_dir, school_dir, "默认"))
            candidates.append(os.path.join(base_assets_dir, sub_dir, "默认"))
        else:
            # 通用逻辑：学校/年级/班级 彻底分层
            if school_dir:
                if grade_dir and class_dir:
                    # 1. 优先：学校/年级/班级
                    candidates.append(os.path.join(base_assets_dir, sub_dir, school_dir, grade_dir, class_dir))
                
                # 2. 次选：学校默认 (对劳动等任务作为兜底)
                candidates.append(os.path.join(base_assets_dir, sub_dir, school_dir, "默认"))

        for target in candidates:
            if not os.path.isdir(target):
                continue
            
            # 尝试在该目录下寻找最匹配任务名的子文件夹 (如 "劳动/福清一中/高一/八班/校园清洁/")
            if task_name:
                matched_folder = self._find_best_matching_folder(task_name, target)
                if matched_folder:
                    # 递归查找图片
                    imgs = self._list_images_recursive(matched_folder)
                    if imgs:
                        logger.info(f"✅ 在子目录【{os.path.basename(target)}】中通过模糊匹配找到专属文件夹: {os.path.basename(matched_folder)}")
                        return random.choice(imgs)

            # 如果没有匹配的子文件夹，或者没有提供任务名，则从当前目录直接选图
            imgs = self._list_images(target)
            if imgs:
                return random.choice(imgs)

        return None

    def _list_images_recursive(self, folder: str) -> list[str]:
        """
        深度递归查找所有图片
        """
        if not folder or not os.path.isdir(folder):
            return []
        out = []
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(self.IMAGE_EXTS):
                        out.append(os.path.join(root, f))
        except Exception as e:
            logger.debug(f"递归扫描图片失败 {folder}: {e}")
        return out

    def _print_resource_hint_once(self, key: str, message: str):
        printed = getattr(self, "_printed_resource_hints", None)
        if not isinstance(printed, set):
            printed = set()
            setattr(self, "_printed_resource_hints", printed)
        if key in printed:
            return
        printed.add(key)
        print(message)

    def _has_valid_resources(self, folder: str) -> bool:
        """
        深度检查目录下是否有任何有效的资源文件（图片或文档）
        """
        if not folder or not os.path.isdir(folder):
            return False
        try:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(self.RESOURCE_EXTS):
                        return True
        except Exception:
            pass
        return False

    def audit_resources(self, base_assets_dir: str = None) -> list[str]:
        """
        执行深度资源审计，返回缺失资源的描述列表
        :param base_assets_dir: 可选的资源根目录，默认为项目根目录下的 assets
        """
        missing = []
        school = self._school_name()
        grade = self._grade_name()
        clazz = self._pure_class_name()
        if not school or not grade or not clazz:
            return ["无法获取账号基本信息（学校/年级/班级），跳过审计"]

        school_dir = self._sanitize_path_component(school)
        grade_dir = self._sanitize_path_component(grade)
        class_dir = self._sanitize_path_component(clazz)

        if base_assets_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_assets_dir = os.path.join(current_dir, "assets")

        # 1. 国旗下讲话 (学校默认)
        gq_dir = os.path.join(base_assets_dir, "国旗下讲话", school_dir, "默认")
        if not self._has_valid_resources(gq_dir):
            missing.append(f"国旗下讲话 (缺失路径: assets/国旗下讲话/{school_dir}/默认/)")

        # 2. 劳动/军训 (班级私有 或 学校默认)
        for sub in ("劳动", "军训"):
            need = os.path.join(base_assets_dir, sub, school_dir, grade_dir, class_dir)
            fallback = os.path.join(base_assets_dir, sub, school_dir, "默认")
            if not self._has_valid_resources(need) and not self._has_valid_resources(fallback):
                missing.append(f"{sub} (缺失路径: {sub}/{school_dir}/{grade_dir}/{class_dir}/ 或 {sub}/{school_dir}/默认/)")

        # 3. 主题班会 (必须有班级目录，且目录下至少有一个资源包子文件夹)
        meeting_root = os.path.join(base_assets_dir, "主题班会", school_dir, grade_dir, class_dir)
        has_meeting_package = False
        if os.path.isdir(meeting_root):
            for item in os.listdir(meeting_root):
                item_path = os.path.join(meeting_root, item)
                if os.path.isdir(item_path) and self._has_valid_resources(item_path):
                    has_meeting_package = True
                    break
        
        if not has_meeting_package:
            missing.append(f"主题班会 (缺失路径: assets/主题班会/{school_dir}/{grade_dir}/{class_dir}/<班会资源包>/)")

        return missing

    def print_resource_setup_hints(self):
        """
        深度审计并打印资源预警
        """
        missing = self.audit_resources()
        if not missing:
            return

        school = self._school_name()
        grade = self._grade_name()
        clazz = self._pure_class_name()
        
        print("\n" + "!" * 60)
        print(f"⚠️  资源审计警告 [{school} {grade} {clazz}]")
        print("!" * 60)
        for m in missing:
            print(f"  - {m}")
        print("!" * 60 + "\n")

    def activate_session(self):
        """
        深度激活业务 Session (获取菜单 + 获取学生基本信息)
        """
        try:
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
                # 究极修复：更新完整的 user_info，确保后续路径生成（学校/年级/班级）有据可查
                self.user_info.update(data)
                
                # 尝试从菜单数据中补充更多信息
                if isinstance(menu_data, dict) and menu_data.get('code') == 1:
                    m_data = menu_data.get('data') or {}
                    for k, v in m_data.items():
                        if v and not self.user_info.get(k):
                            self.user_info[k] = v

                # 更新姓名显示
                self.student_name = self.user_info.get('NAME') or self.user_info.get('realName') or self.user_info.get('studentName') or '未知'
                
                logger.info(f"业务 Session 激活成功，当前学生: {self.student_name} ({self._school_name()})")
                
                # 确保基础资源目录结构存在
                self._ensure_resource_dirs()
                
                self.print_resource_setup_hints()
                return True
        except Exception as e:
            logger.error(f"Session 激活失败: {e}")
        return False

    @staticmethod
    def _normalize_task_name(name: str) -> str:
        return re.sub(r"\s+", "", name or "")

    def _ensure_resource_dirs(self):
        """
        根据当前账号信息，确保必要的资源分层目录已创建。
        不再自动迁移任何文件，仅创建结构。
        """
        school = self._school_name()
        grade = self._grade_name()
        clazz = self._pure_class_name()

        if not school or not grade or not clazz:
            return

        school_dir = self._sanitize_path_component(school)
        grade_dir = self._sanitize_path_component(grade)
        class_dir = self._sanitize_path_component(clazz)

        base_assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        task_types = ["劳动", "军训", "主题班会", "国旗下讲话"]
        
        for tt in task_types:
            if tt == "国旗下讲话":
                target_path = os.path.join(base_assets_dir, tt, school_dir, "默认")
            else:
                target_path = os.path.join(base_assets_dir, tt, school_dir, grade_dir, class_dir)
            
            if not os.path.exists(target_path):
                try:
                    os.makedirs(target_path, exist_ok=True)
                except Exception:
                    pass

    def get_class_meeting_folders(self) -> list[str]:
        """
        获取当前账号所属班级的班会资源文件夹列表，用于辅助识别
        """
        school_dir = self._sanitize_path_component(self._school_name())
        grade_dir = self._sanitize_path_component(self._grade_name())
        class_dir = self._sanitize_path_component(self._pure_class_name())
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        meeting_candidates = []
        if school_dir and grade_dir and class_dir:
            meeting_candidates.append(os.path.join(current_dir, "assets", "主题班会", school_dir, grade_dir, class_dir))
        
        all_folders = []
        for cand_root in meeting_candidates:
            if os.path.isdir(cand_root):
                try:
                    for item in os.listdir(cand_root):
                        if os.path.isdir(os.path.join(cand_root, item)):
                            all_folders.append(item)
                except:
                    pass
        return all_folders

    def check_resource_health(self) -> dict[str, bool]:
        """
        检查当前账号各维度资源的健康状况
        """
        results = {
            "labor": self._pick_image_path("劳动") is not None,
            "military": self._pick_image_path("军训") is not None,
            "speech": self._pick_image_path("国旗下讲话") is not None,
            "class_meeting_img": False,
            "class_meeting_record": False
        }

        # 检查班会 (图 + 记录)
        # 复用匹配逻辑寻找班会文件夹
        from comprehensive_eval_pro.utils.record_parser import extract_first_record_text
        
        # 模拟一个通用的班会任务名进行探测
        dummy_task_name = "主题班会"
        
        # 确定资源目录优先级 (与 submit_task 保持一致)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        school_dir = self._sanitize_path_component(self._school_name())
        grade_dir = self._sanitize_path_component(self._grade_name())
        class_dir = self._sanitize_path_component(self._pure_class_name())
        
        meeting_candidates = []
        if school_dir and grade_dir and class_dir:
            meeting_candidates.append(os.path.join(current_dir, "assets", "主题班会", school_dir, grade_dir, class_dir))

        # 只要能在任何候选目录下找到任何有效的班会资源包即可
        for cand_root in meeting_candidates:
            if not os.path.isdir(cand_root):
                continue
            
            # 尝试在该目录下寻找任何有效的子文件夹
            try:
                for item in os.listdir(cand_root):
                    item_path = os.path.join(cand_root, item)
                    if not os.path.isdir(item_path):
                        continue
                    
                    # 检查是否有图
                    if not results["class_meeting_img"]:
                        if self._has_any_images(item_path):
                            results["class_meeting_img"] = True
                    
                    # 检查是否有记录
                    if not results["class_meeting_record"]:
                        content, _ = extract_first_record_text(item_path)
                        if content:
                            results["class_meeting_record"] = True
                    
                    if results["class_meeting_img"] and results["class_meeting_record"]:
                        break
            except:
                pass
            
            if results["class_meeting_img"] and results["class_meeting_record"]:
                break
        
        return results

    @classmethod
    def _looks_like_class_meeting(cls, task_name: str, dimension_name: str = "", existing_folders: list[str] = None) -> bool:
        """
        SVS (Semantic-Visual-Structural) 3.0 识别系统
        """
        name = cls._normalize_task_name(task_name)
        dim = (dimension_name or "").strip()

        # 0. 语义黑名单拦截 (一票否决)
        if any(word in name for word in cls.SPECIAL_TASK_BLACKLIST):
            return False

        # 1. Reality Layer (现实层 - 资源感知)
        # 如果已经有匹配的资源文件夹，直接视为班会
        if existing_folders:
            # 简化对比名：去掉日期前缀和班级前缀
            simple_name = re.sub(r"^\d{4}[\d\.\-]*", "", name).strip()
            simple_name = re.sub(r"高[一二三]\s*[（(\s]*\d+[\s)）]*\s*班", "", simple_name).strip()
            for folder in existing_folders:
                folder_norm = cls._normalize_task_name(folder)
                folder_simple = re.sub(r"^\d{4}[\d\.\-]*", "", folder_norm).strip()
                folder_simple = re.sub(r"高[一二三]\s*[（(\s]*\d+[\s)）]*\s*班", "", folder_simple).strip()
                
                # 计算核心部分的相似度
                if simple_name and folder_simple:
                    ratio = difflib.SequenceMatcher(None, simple_name, folder_simple).ratio()
                    if ratio > 0.85:
                        return True

        # 2. Semantic Layer (语义层 - 权重评分)
        score = 0
        if "思想品德" in dim:
            score += 3
        
        # 强特征直通车
        if "主题班会" in name or "专题班会" in name:
            score += 10
        
        # 符号特征：包含书名号或引号
        if re.search(r"[《“].+[》”]", name):
            score += 5
            
        # 关键词特征
        if any(word in name for word in ["教育", "安全", "使命", "报国", "青春", "梦想", "责任", "考", "元旦", "节", "心理"]):
            score += 2
            
        # 长度特征
        if len(name) > 15:
            score += 1

        # 阈值调优：7分即通过 (例如：书名号5 + 关键词2 = 7)
        if score >= 7:
            return True

        # 3. Structural Layer (结构层 - 极致正则)
        # 极致兼容正则：处理全角/半角括号、内部空格
        if re.search(r"高[一二三]\s*[（(\s]*\d+[\s)）]*\s*班", name):
            # 如果匹配到班级，必须配合维度或关键词，不能仅靠分数
            if "思想品德" in dim or "班会" in name:
                return True
        
        # 4. 跨维度判定 (保底)
        if "班会" in name:
            if re.search(r"[^级]班会", name) or name.startswith("班会"):
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

    def _get_images_from_pdf(self, pdf_path: str, max_pages: int = 3) -> list[str]:
        """
        将 PDF 的前 N 页转换为临时图片文件，供 OCR 使用
        """
        temp_images = []
        try:
            doc = fitz.open(pdf_path)
            # 限制页数
            page_count = min(len(doc), max_pages)
            
            # 创建 runtime/temp 目录
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            for i in range(page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 提高清晰度以利于 OCR
                img_path = os.path.join(temp_dir, f"pdf_page_{i}_{os.path.basename(pdf_path)}.jpg")
                pix.save(img_path)
                temp_images.append(img_path)
            doc.close()
            if temp_images:
                logger.info(f"成功将 PDF 【{os.path.basename(pdf_path)}】的前 {len(temp_images)} 页转换为图片")
        except ImportError:
            logger.warning("未检测到 PyMuPDF (pip install pymupdf)，无法解析 PDF 图片。")
        except Exception as e:
            logger.error(f"PDF 转图片异常: {e}")
        return temp_images

    def _get_content_from_pdf_via_ocr(self, folder_path: str, task_name: str, ai_gen: AIContentGenerator) -> str:
        """
        [究极垫底] 视觉 OCR 解析逻辑
        """
        files = os.listdir(folder_path)
        pdfs = [os.path.join(folder_path, f) for f in files if f.lower().endswith(".pdf")]
        if not pdfs:
            return ""

        school = self._school_name() or "未知学校"
        logger.info(f"🔍 正在为【{school}】的任务【{task_name}】启动视觉 OCR 解析流程 (PDF Fallback)...")

        pdfs.sort()
        pdf_imgs = self._get_images_from_pdf(pdfs[0], max_pages=3)
        if not pdf_imgs:
            return ""

        try:
            content = ai_gen.generate_content_from_images(pdf_imgs, task_name, school_name=self._school_name())
            if content:
                return content
        except Exception as e:
            logger.error(f"OCR 视觉解析过程中发生异常: {e}")
        finally:
            # 究极清理：确保临时图片在任何情况下都被删除
            for f in pdf_imgs:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except Exception as ex:
                    logger.debug(f"清理临时图片失败 {f}: {ex}")
        
        return ""

    def _find_best_matching_folder(self, task_name: str, base_dir: str) -> str | None:
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
                # 检查文件夹是否包含图片或 Excel 等资源
                files = os.listdir(path)
                has_res = any(
                    fname.lower().endswith(self.IMAGE_EXTS + (".xls", ".xlsx", ".txt", ".docx", ".doc", ".pdf"))
                    for fname in files
                )
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
            
            # 日期匹配：如果有日期且不匹配，则显著降权
            folder_date = self._extract_date(folder)
            date_score = 0
            if task_date and folder_date:
                date_score = 2 if task_date == folder_date else -1 # 强匹配+2，错匹配-1
            
            # 排序元组：日期得分第一优先级，相似度第二，长度第三
            scored.append((date_score, similarity, len(folder_key), folder))

        scored.sort(reverse=True)
        # 究极过滤：如果日期冲突且相似度不高，则视为不匹配
        if scored and scored[0][0] == -1 and scored[0][1] < 0.6:
            return None
            
        best = scored[0][3] if scored else None
        return os.path.join(base_dir, best) if best else None

    @classmethod
    def _is_labor_task(cls, task_name: str, dimension_name: str = "") -> bool:
        """
        判断是否为劳动专项：必须含“劳动”且不在黑名单，且排除单纯的“素养评价”
        """
        name = cls._normalize_task_name(task_name)
        dim = (dimension_name or "").strip()

        # 1. 语义黑名单拦截
        if any(word in name for word in cls.SPECIAL_TASK_BLACKLIST):
            return False

        # 2. 核心判定
        # 只要是“劳动素养”维度，且不在黑名单，且不是纯评价，就可以放宽关键词
        is_labor_dim = "劳动" in dim or "劳动素养" in dim
        
        # 强动作词：具备跨维度穿透力
        strong_actions = ["家务", "保洁", "清理", "扫地", "扫除", "大扫除", "卫生"]
        if any(act in name for act in strong_actions):
            return "评价" not in name

        if "劳动" in name:
            # 排除干扰词
            if "劳动素养" in name and "劳动素养评价" in name:
                return False
            return "评价" not in name
            
        # 如果维度对，且有其它劳动特征词
        if is_labor_dim:
            if any(act in name for act in ["义务", "生产", "实践", "整理", "内务"]):
                return True
                
        return False

    def _calculate_task_hours(self, task_name: str, is_class_meeting: bool, is_military: bool, is_labor: bool) -> float:
        """
        根据任务类型动态计算学时
        """
        if is_military:
            return 32.0
        if is_class_meeting:
            return 1.0
        if is_labor:
            return 2.0
        return 0.5

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
        is_labor_task = self._is_labor_task(task_name)
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
            # 班会逻辑：模糊匹配文件夹，支持 学校/年级/班级 彻底分层。
            school_dir = self._sanitize_path_component(self._school_name())
            grade_dir = self._sanitize_path_component(self._grade_name())
            class_dir = self._sanitize_path_component(self._pure_class_name())
            
            # 候选匹配根目录优先级：
            # 1. 学校/年级/班级
            # 2. 默认
            # 3. 根目录 (兼容旧版)
            meeting_candidates = []
            if school_dir and grade_dir and class_dir:
                meeting_candidates.append(os.path.join(current_dir, "assets", "主题班会", school_dir, grade_dir, class_dir))

            matched_folder = None
            for cand_root in meeting_candidates:
                if os.path.isdir(cand_root):
                    matched_folder = self._find_best_matching_folder(task_name, cand_root)
                    if matched_folder:
                        break
            
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
                    # 霸道缓存：全校共享解析结果，以学校名 + 归一化任务名 为 Key
                    # 这样即使文件夹命名略有差异，只要是同一个任务，就能全校共享解析结果
                    norm_task_name = self._normalize_match_text(task_name)
                    cache_key = f"{self._school_name()}_{norm_task_name}"
                    
                    with self._RECORD_CACHE_LOCK:
                        if cache_key in self._GLOBAL_RECORD_CACHE:
                            xls_content = self._GLOBAL_RECORD_CACHE[cache_key]
                            logger.info(f"🚀 [霸道缓存] 命中全校共享解析结果: {cache_key}")
                        else:
                            from comprehensive_eval_pro.utils.record_parser import extract_first_record_text
                            xls_content, used_file = extract_first_record_text(matched_folder)
                            
                            # 究极修正：如果返回的是 PDF 占位符或者为空，则触发真正的视觉 OCR
                            if not xls_content or xls_content == "[PDF记录: 待视觉解析]":
                                logger.info(f"未发现文本记录文件或仅发现 PDF，尝试视觉解析...")
                                xls_content = self._get_content_from_pdf_via_ocr(matched_folder, task_name, ai_generator)
                            
                            if xls_content:
                                self._GLOBAL_RECORD_CACHE[cache_key] = xls_content
                                logger.info(f"📊 [霸道缓存] 解析并缓存结果: {cache_key}")
                            else:
                                logger.warning(f"⚠️ 资源包【{os.path.basename(matched_folder)}】内未能提取到任何可用文本 (含 OCR)")
            else:
                logger.error(f"❌ 班会任务【{task_name}】未能匹配到任何资源包，请检查 assets/主题班会 目录")
                return None  # 严格隔离：无资源包不提交

        # 通用图片挂载 (针对专项任务)
        if not attachment_ids and (not is_class_meeting) and target_sub_dir:
            chosen_img_path = self._pick_image_path(target_sub_dir, task_name=task_name)
            if chosen_img_path:
                if not dry_run:
                    img_id = self.file_service.upload_image(chosen_img_path)
                    if img_id:
                        attachment_ids.append(img_id)
                        logger.info(f"成功为任务【{task_name}】挂载图片附件 ID: {img_id}")
                else:
                    attachment_ids.append(999999)
                    upload_paths.append(chosen_img_path)

        # 3. 内容生成
        school_name = self._school_name() or "学校"
        if content_override is not None:
            content = str(content_override)
        else:
            if is_labor_task and chosen_img_path:
                content = ai_generator.generate_labor_content(chosen_img_path, task_name, use_cache=use_cache, school_name=school_name)
            elif is_military_task:
                content = ai_generator.generate_military_content(task_name, use_cache=use_cache, school_name=school_name)
            elif is_class_meeting:
                if xls_content:
                    content = ai_generator.generate_class_meeting_content(xls_content, task_name, use_cache=use_cache, school_name=school_name)
                else:
                    content = ai_generator.generate_speech_content(task_name, use_cache=use_cache, school_name=school_name)
            else:
                content = ai_generator.generate_speech_content(task_name, use_cache=use_cache, school_name=school_name)
            
        if not content:
            content = f"在{school_name}参加了{task_name}活动，收获颇丰。"

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
            "hours": self._calculate_task_hours(task_name, is_class_meeting, is_military_task, is_labor_task), 
            "circleBeginDate": "",
            "circleEndDate": "", 
            "checkResult": "1" if is_military_task else "", 
            "patentType": "", 
            "patentNum": "", 
            "address": full_class_name if is_class_meeting else (school_name if is_labor_or_military else ""), 
            "termName": "", 
            "activityName": "", 
            "sportsName": "", 
            "teamName": "", 
            "orgName": school_name if is_labor_or_military else "", 
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
