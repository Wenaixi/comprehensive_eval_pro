import datetime
import logging
import os
import re

from .cli import (
    display_user_profile,
    get_task_status,
    is_pending_status,
    mask_secret,
    print_ai_key_notice,
    print_all_tasks,
)
from .logging_setup import setup_logging
from .config_store import get_account_entry, load_accounts_from_txt
from .policy import (
    config,
    get_default_task_indices,
    get_default_task_mode,
    get_diversity_every,
    get_ai_ocr_max_retries,
    get_ai_ocr_retries_per_model,
    get_ddddocr_max_retries,
    get_manual_ocr_max_retries,
    get_ocr_max_retries,
    parse_indices,
    should_use_cache,
)
from .services.auth import ProAuthService
from .services.content_gen import AIContentGenerator
from .services.task_manager import ProTaskManager
from .flow_logic import compute_base_entries, compute_target_entries, should_use_cache_for_task, mark_task_generated

logger = logging.getLogger("Main")


def _account_sort_key(username: str):
    u = (username or "").strip()
    if u.isdigit():
        return 0, len(u), u
    return 1, u


def get_account_real_name(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return ""
    real_name = str(user_info.get("realName") or user_info.get("NAME") or "").strip()
    if real_name:
        return real_name
    info = user_info.get("studentSchoolInfo")
    if not isinstance(info, dict):
        return ""
    return str(info.get("studentName") or "").strip()


def _extract_cached_real_name(config: dict, username: str) -> str:
    entry = get_account_entry(config, username)
    user_info = entry.get("user_info") if isinstance(entry.get("user_info"), dict) else {}
    return get_account_real_name(user_info)


def log_missing_resources(student_name: str, username: str, missing_list: list[str], detail_info: dict = None):
    """
    将缺失资源记录到 missing_resources.log 文件中。
    采用结构化日志格式，便于后续审计。
    """
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "missing_resources.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 提取学校/年级/班级等上下文信息
    school = detail_info.get("school", "未知学校") if detail_info else "未知学校"
    grade = detail_info.get("grade", "未知年级") if detail_info else "未知年级"
    clazz = detail_info.get("class", "未知班级") if detail_info else "未知班级"

    header = f"[{timestamp}] [RESOURCE_MISSING] {school} | {grade} | {clazz} | {student_name} ({username})"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{header}\n")
        for m in missing_list:
            f.write(f"  └─ 缺失路径: {m}\n")
        f.write("-" * 80 + "\n")

def generate_resource_health_report(prepared_accounts: list[dict]):
    """
    汇总所有就绪账号的资源需求并生成体检报告 (深度检查图片与 Excel 记录)
    """
    ready_accounts = [a for a in prepared_accounts if a.get("status") == "已就绪" and a.get("task_mgr")]
    if not ready_accounts:
        return

    print("\n" + "=" * 95)
    print("      🔍 资源体检报告 (Resource Health Check)")
    print("=" * 95)
    
    # 聚合：(School, Grade, Class) -> list of usernames
    groups = {}
    for a in ready_accounts:
        tm = a["task_mgr"]
        school = tm._school_name()
        grade = tm._grade_name()
        clazz = tm._pure_class_name()
        key = (school, grade, clazz)
        if key not in groups:
            groups[key] = []
        groups[key].append(a["username"])

    print(f"{'学校':<15} | {'年级':<10} | {'班级':<10} | {'劳动':<6} | {'军训':<6} | {'国旗':<6} | {'班会图':<7} | {'班会记录':<8} | {'账号数'}")
    print("-" * 115)

    for (school, grade, clazz), users in groups.items():
        # 寻找该组的一个代表账号进行资源检查 (因为同班同学资源需求一致)
        rep_username = users[0]
        rep_account = next(a for a in prepared_accounts if a["username"] == rep_username)
        tm: ProTaskManager = rep_account["task_mgr"]
        
        health = tm.check_resource_health()
        
        ld_ok = "✅" if health["labor"] else "❌"
        jx_ok = "✅" if health["military"] else "❌"
        gq_ok = "✅" if health.get("speech", False) else "❌"
        bh_img_ok = "✅" if health["class_meeting_img"] else "❌"
        bh_record_ok = "✅" if health["class_meeting_record"] else "❌"

        # 处理空学校名称显示
        display_school = school if school else "未知学校"
        if len(display_school) > 15:
            display_school = display_school[:12] + "..."

        print(f"{display_school:<15} | {grade:<12} | {clazz:<12} | {ld_ok:<8} | {jx_ok:<8} | {gq_ok:<8} | {bh_img_ok:<9} | {bh_record_ok:<10} | {len(users)}")

    print("=" * 115)
    print("[注] ✅ 表示资源已就绪，❌ 表示缺失。")
    print("[💡] 班会资源包必须包含图片和 记录文件 (PDF/Excel/Word/TXT) 才能获得最佳 AI 生成效果。")
    print("-" * 95)


def parse_account_selection(raw: str, total: int, current: set[int]) -> tuple[set[int] | None, str]:
    text = (raw or "").strip().lower()
    if text in ("", "ok", "yes", "y"):
        return set(current), "keep"
    if text in ("q", "quit", "exit", "nq"):
        return None, "cancel"
    if text in ("a", "all"):
        return set(range(total)), "all"
    if text in ("i", "inv", "invert"):
        return set(range(total)) - set(current), "invert"
    if text in ("n", "none", "clear"):
        return set(), "none"

    mode = "replace"
    if text.startswith("+"):
        mode = "add"
        text = text[1:].strip()
    elif text.startswith("-"):
        mode = "remove"
        text = text[1:].strip()

    if not text:
        return set(current), "keep"

    picked: set[int] = set()
    parts = re.split(r"[\s,，]+", text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("+") or part.startswith("-"):
            part = part[1:].strip()
            if not part:
                continue
        if "-" in part:
            a, b = part.split("-", 1)
            if a.isdigit() and b.isdigit():
                start = int(a)
                end = int(b)
                if start > end:
                    start, end = end, start
                for x in range(start, end + 1):
                    idx = x - 1
                    if 0 <= idx < total:
                        picked.add(idx)
                continue
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < total:
                picked.add(idx)

    if mode == "add":
        return set(current) | picked, "add"
    if mode == "remove":
        return set(current) - picked, "remove"
    return picked, "replace"


def _print_accounts_table(prepared_accounts: list[dict], config: dict):
    print("\n" + "=" * 90)
    print(f"{'序号':<4} | {'账号':<16} | {'姓名':<10} | {'Token':<5} | {'状态'}")
    print("-" * 90)
    for i, item in enumerate(prepared_accounts):
        username = item.get("username") or ""
        name = item.get("real_name") or _extract_cached_real_name(config, username) or "-"
        has_token = "是" if (item.get("token") or "").strip() else "否"
        status = item.get("status") or "-"
        print(f"{i+1:<4} | {username:<16} | {name:<10} | {has_token:<5} | {status}")
    print("=" * 90)


def prepare_accounts_for_selection(
    accounts: list[tuple[str, str]],
    config: dict,
    sso_base: str,
):
    prepared: list[dict] = []
    for i, (username, password) in enumerate(accounts):
        username = (username or "").strip()
        password = (password or "").strip()
        if not username or not password:
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": "",
                    "token": "",
                    "status": "缺少账号/密码",
                    "task_mgr": None,
                }
            )
            continue

        print("\n" + "-" * 60)
        print(f"[*] 预登录 {i+1}/{len(accounts)}：{username}")
        print("-" * 60)

        token_flow = try_use_token_flow(config, username, sso_base=sso_base)
        if token_flow:
            # 究极持久化：即使是复用 Token，也要同步最新的 user_info (如学校/班级)
            entry = get_account_entry(config, username)
            entry["token"] = token_flow["token"]
            entry["user_info"] = token_flow["user_info"]
            # 保存状态
            if hasattr(config, "save_state"):
                config.save_state()
            
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": get_account_real_name(token_flow["user_info"]),
                    "token": token_flow["token"],
                    "status": "已就绪",
                    "task_mgr": token_flow["task_mgr"],
                }
            )
            continue

        auth = ProAuthService(sso_base=sso_base)
        print("[*] 正在溯源学校信息...")
        school_id = auth.get_school_id(username)
        if not school_id:
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": "",
                    "token": "",
                    "status": "溯源失败",
                    "task_mgr": None,
                }
            )
            continue

        ok = ocr_login_with_retries(auth, username, password, school_id)
        if not ok:
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": "",
                    "token": "",
                    "status": "登录失败",
                    "task_mgr": None,
                }
            )
            continue

        task_mgr = build_task_manager(auth.token, auth.user_info, config)
        if not task_mgr.activate_session():
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": get_account_real_name(auth.user_info),
                    "token": auth.token or "",
                    "status": "会话激活失败",
                    "task_mgr": None,
                }
            )
            continue

        # 补全学校信息
        _patch_school_info(task_mgr, auth, username)

        auth_user_info = auth.user_info if isinstance(getattr(auth, "user_info", None), dict) else {}
        tm_user_info = task_mgr.user_info if isinstance(getattr(task_mgr, "user_info", None), dict) else {}
        merged_user_info = dict(auth_user_info)
        merged_user_info.update(tm_user_info)
        if hasattr(task_mgr, "user_info"):
            task_mgr.user_info = merged_user_info

        token_value = (auth.token or getattr(task_mgr, "token", "") or "").strip()
        if token_value and hasattr(task_mgr, "token"):
            task_mgr.token = token_value

        # 究极持久化：同步激活 Session 后获取的更全信息（学校/班级/年级）到配置
        entry = get_account_entry(config, username)
        entry["token"] = auth.token
        entry["user_info"] = merged_user_info
        if hasattr(config, "save_state"):
            config.save_state()

        try:
            task_mgr.print_resource_setup_hints()
        except Exception:
            pass

        prepared.append(
            {
                "username": username,
                "password": password,
                "real_name": get_account_real_name(merged_user_info),
                "token": token_value,
                "status": "已就绪",
                "task_mgr": task_mgr,
            }
        )

    ready_count = len([a for a in prepared if a.get("status") == "已就绪"])
    fail_count = len(prepared) - ready_count
    print(f"\n[*] 预登录阶段结束。总计: {len(prepared)}，就绪: {ready_count}，失败: {fail_count}")
    
    failures = [a for a in prepared if a.get("status") != "已就绪"]
    if failures:
        print("[⚠️] 以下账号预登录失败，将无法执行后续任务：")
        for f in failures:
            print(f"    - {f['username']}: {f['status']}")

    return prepared


def looks_like_class_meeting(task: dict, existing_folders: list[str] = None) -> bool:
    return ProTaskManager._looks_like_class_meeting(
        task.get("name", ""), 
        task.get("dimensionName", ""), 
        existing_folders=existing_folders
    )


def is_y_special_task(task: dict, existing_folders: list[str] = None) -> bool:
    name = (task.get("name", "") or "")
    dim = (task.get("dimensionName", "") or "")
    
    # 1. 军训与国旗
    is_special = any(word in name for word in ["军训", "国旗下讲话"])
    
    # 2. 劳动与班会 (采用三位一体识别)
    is_ld = ProTaskManager._is_labor_task(name, dim)
    is_bh = looks_like_class_meeting(task, existing_folders=existing_folders)
    
    return is_special or is_ld or is_bh


def ocr_login_with_retries(auth: ProAuthService, username: str, password: str, school_id: str):
    """
    带重试机制的登录流程，统一由 VisionService 调度
    """
    def _manual_login(manual_retries: int):
        print("[*] 已切换到手动验证码输入。")
        for attempt in range(manual_retries):
            print(f"[*] 正在尝试手动验证码登录 (第 {attempt+1}/{manual_retries} 次)...")
            img_path, _ = auth.get_captcha(auto_open=True, engine="manual")
            if not img_path:
                print("[❌] 获取验证码失败。")
                continue
            print(f"[*] 请查看验证码图片并输入：{img_path}")
            captcha_code = input("[?] 验证码（输入 q 退出）: ").strip()
            if not captcha_code:
                continue
            if captcha_code.lower() in ("q", "quit", "exit"):
                return False
            if auth.login(username, password, captcha_code, school_id=school_id):
                return True
            print(f"[❌] 第 {attempt+1} 次登录尝试失败。")
        return False

    # 1. 尝试自动识别登录 (AI 轮询 + 本地兜底)
    # 这里重试次数可以从 policy 获取，或者直接设定一个合理的固定值，因为 VisionService 内部已经有模型间的重试
    auto_retries = get_ocr_max_retries() or 5 
    
    print(f"[*] 开始自动验证码识别登录 (最多尝试 {auto_retries} 次)...")
    for attempt in range(auto_retries):
        print(f"[*] 正在尝试自动登录 (第 {attempt+1}/{auto_retries} 次)...")
        # engine="auto" 会自动按 AI -> Local 顺序尝试
        _, captcha_code = auth.get_captcha(auto_open=False, engine="auto")
        captcha_code = (captcha_code or "").strip()
        
        if not captcha_code:
            logger.warning(f"第 {attempt+1} 次自动识别未获得有效结果")
            continue
            
        if auth.login(username, password, captcha_code, school_id=school_id):
            return True
            
        print(f"[❌] 第 {attempt+1} 次自动登录尝试失败（验证码可能识别错误）。")

    # 2. 自动识别全部失败，回退到手动
    print("[⚠️] 自动验证码识别已连续失败，将回退到手动验证码输入。")
    manual_retries = get_manual_ocr_max_retries() or 3
    return _manual_login(manual_retries)


def build_task_manager(token: str, user_info: dict, config: dict):
    return ProTaskManager(
        token=token,
        user_info=user_info,
        base_url=config.get("base_url") or "http://139.159.205.146:8280",
        upload_url=config.get("upload_url"),
    )


def _patch_school_info(task_mgr: ProTaskManager, auth: ProAuthService, username: str):
    """
    当 TaskManager 中缺失学校信息时，通过 AuthService 补全并回填
    """
    school_name_fn = getattr(task_mgr, "_school_name", None)
    has_school = bool(callable(school_name_fn) and (school_name_fn() or "").strip())
    if not has_school:
        try:
            meta = auth.get_school_meta(username)
            school_name = str(meta.get("name") or "").strip()
            if school_name:
                ssi = task_mgr.user_info.setdefault("studentSchoolInfo", {})
                if isinstance(ssi, dict) and not str(ssi.get("schoolName") or "").strip():
                    ssi["schoolName"] = school_name
                school_id = str(meta.get("id") or "").strip()
                if isinstance(ssi, dict) and school_id and not str(ssi.get("schoolId") or "").strip():
                    ssi["schoolId"] = school_id
        except Exception as e:
            logger.debug(f"补全学校信息失败: {e}")


def try_use_token_flow(config: dict, username: str, sso_base: str | None = None):
    entry = get_account_entry(config, username)
    token = (entry.get("token") or "").strip()
    user_info = entry.get("user_info") if isinstance(entry.get("user_info"), dict) else {}
    if not token:
        return None

    print(f"[*] 检测到该账号持久化 Token，正在校验有效性：{username}")
    task_mgr = build_task_manager(token, user_info, config)
    if not task_mgr.activate_session():
        print("[⚠️] Token 失效，将重新登录。")
        return None

    if sso_base:
        auth = ProAuthService(sso_base=sso_base)
        _patch_school_info(task_mgr, auth, username)

    # 返回最新的 user_info (可能在 activate_session 或 _patch_school_info 中被补充了信息)
    return {"token": task_mgr.token, "user_info": task_mgr.user_info, "task_mgr": task_mgr}


def run_task_flow(task_mgr: ProTaskManager, ai_gen: AIContentGenerator, preset=None, strict: bool = True, account_username: str | None = None):
    print("[*] 正在扫描全维度任务...")
    tasks = task_mgr.get_all_tasks(force_refresh=False)

    pending_tasks = []
    for t in tasks:
        status = get_task_status(t)
        if is_pending_status(status):
            pending_tasks.append(t)
        else:
            logger.debug(f"跳过已处理任务: {t.get('name', '未知任务')} [状态: {status}]")

    print(f"[+] 扫描完成。共发现 {len(tasks)} 个任务，其中 {len(pending_tasks)} 个处于待处理状态。")
    print_all_tasks(tasks)
    if not pending_tasks:
        print("[!] 当前没有待处理任务。若需重做已完成任务，请在下一步“处理范围”里选择对应选项。")

    if preset is None:
        default_mode = get_default_task_mode()
        if default_mode:
            indices = parse_indices(get_default_task_indices())
            preset = {
                "mode": default_mode,
                "indices": indices,
                "selection": None,
                "scope": None,
                "skip_review": config.get_setting("auto_mode", False, env_name="CEP_AUTO_MODE"),
                "confirmed_resubmit": config.get_setting("auto_confirm_resubmit", False, env_name="CEP_AUTO_CONFIRM_RESUBMIT"),
                "diversity_every": get_diversity_every(),
                "submit_index": 0,
            }
        else:
            print("\n" + "=" * 40)
            prompt = f"[*] 总任务 {len(tasks)} 个，待处理 {len(pending_tasks)} 个。\n"
            prompt += "[*] 操作指南:\n"
            prompt += "    [y]  : 选择 班会 + 军训 + 国旗下讲话 + 劳动 (四大专项)\n"
            prompt += "    [bh] : 选择所有“班会”任务\n"
            prompt += "    [gq] : 选择所有“国旗下讲话”任务\n"
            prompt += "    [ld] : 选择所有“劳动”相关任务\n"
            prompt += "    [jx] : 选择所有“军训”任务\n"
            prompt += "    [序号] : 选择指定序号任务 (如: 1 或 1 3 5)\n"
            prompt += "    [n]  : 退出程序\n"
            print(prompt)
            raw_choice = input("[?] 请输入你的选择: ").strip().lower()

            if raw_choice in ("n", "q", "quit", "exit"):
                if strict:
                    print("[*] 用户取消，程序退出。")
                    return None
                return None

            indices = []
            selection = raw_choice
            if any(c.isdigit() for c in raw_choice):
                selection = "indices"
                for part in raw_choice.split():
                    if part.isdigit():
                        indices.append(int(part) - 1)

            preset = {
                "mode": selection,
                "indices": sorted(set(indices)),
                "selection": selection,
                "scope": None,
                "skip_review": None,
                "confirmed_resubmit": False,
                "diversity_every": get_diversity_every(),
                "submit_index": 0,
            }

    mode = (preset.get("mode") or "").lower()
    indices = preset.get("indices") or []

    if mode == "ry":
        preset["selection"] = "y"
        preset["scope"] = "all"
        mode = "y"
    elif mode == "r":
        preset["selection"] = "indices"
        preset["scope"] = "all"
        mode = "indices"

    selection = (preset.get("selection") or mode or "").lower()
    if selection not in {"y", "bh", "gq", "ld", "jx", "indices"}:
        print("[*] 用户取消或输入无效，跳过。")
        if strict:
            return None
        return preset

    if not preset.get("scope"):
        print("\n" + "=" * 40)
        print("[*] 处理范围:")
        print("    [1] 完成未完成（只处理待提交）")
        print("    [2] 重做已完成（只处理已提交/已完成）")
        print("    [3] 全部重做（待提交 + 已完成）")
        print("    [0] 取消")
        raw_scope = input("[?] 请选择处理范围: ").strip().lower()
        if raw_scope in ("0", "n", "q", "quit", "exit"):
            if strict:
                print("[*] 用户取消，程序退出。")
                return None
            return preset
        if raw_scope == "1":
            preset["scope"] = "pending"
        elif raw_scope == "2":
            preset["scope"] = "done"
        elif raw_scope == "3":
            preset["scope"] = "all"
        else:
            if strict:
                print("[*] 用户取消或输入无效，程序退出。")
                return None
            return preset

    scope = (preset.get("scope") or "pending").lower()
    if scope not in {"pending", "done", "all"}:
        scope = "pending"
        preset["scope"] = scope

    # 获取已有的班会资源文件夹，用于 SVS 3.0 Reality Layer 识别
    existing_folders = task_mgr.get_class_meeting_folders()

    base_entries = compute_base_entries(
        tasks=tasks,
        selection=selection,
        indices=indices,
        looks_like_class_meeting=lambda t: looks_like_class_meeting(t, existing_folders=existing_folders),
        is_y_special_task=lambda t: is_y_special_task(t, existing_folders=existing_folders),
        is_labor_task=ProTaskManager._is_labor_task,
    )
    if selection == "y":
        print("\n[*] 已选择四大专项任务集合 (班会/军训/国旗/劳动)")
    elif selection == "jx":
        print("\n[*] 已选择所有“军训”任务")
    elif selection == "gq":
        print("\n[*] 已选择所有“国旗下讲话”任务")
    elif selection == "ld":
        print("\n[*] 已选择所有“劳动”相关任务")
    elif selection == "bh":
        print("\n[*] 已选择所有“班会”相关任务")
    elif selection == "indices":
        for idx in indices:
            if not (0 <= idx < len(tasks)):
                print(f"[⚠️] 序号 {idx+1} 超出范围，已忽略。")
        print(f"\n[*] 已选择 {len(base_entries)} 个指定序号任务")

    target_entries, pending_count, done_count = compute_target_entries(
        base_entries=base_entries,
        scope=scope,
        get_task_status=get_task_status,
        is_pending_status=is_pending_status,
    )

    if scope == "pending":
        print(f"[*] 处理范围：仅未完成（候选 {len(base_entries)}，待处理 {pending_count}）")
    elif scope == "done":
        print(f"[*] 处理范围：仅重做已完成（候选 {len(base_entries)}，已完成 {done_count}）")
    else:
        print(f"[*] 处理范围：全部重做（候选 {len(base_entries)}，待处理 {pending_count}，已完成 {done_count}）")

    if not target_entries:
        print("[!] 没有选中任何任务。")
        if strict:
            return None
        return preset

    need_resubmit_confirm = scope in {"done", "all"} and done_count > 0
    if need_resubmit_confirm and not preset.get("confirmed_resubmit"):
        confirm_resubmit = input("[!] 本次操作会再次提交任务，可能产生重复记录。确认继续? (y/n): ").strip().lower()
        if confirm_resubmit != "y":
            if strict:
                print("[*] 用户取消，程序退出。")
                return None
            print("[*] 已跳过该账号。")
            return preset
        preset["confirmed_resubmit"] = True

    print("\n" + "=" * 100)
    print(f"{'总表序号':<8} | {'任务名称':<40} | {'所属维度':<14} | {'完成过':<4} | {'状态'}")
    print("-" * 100)
    for idx, t in target_entries:
        dim_display = t.get("dimensionName") or f"维度{t.get('dimensionId', 'N/A')}"
        status = get_task_status(t)
        finished = "是" if not is_pending_status(status) else "否"
        print(f"{idx+1:<8} | {t.get('name', '未命名'):<42} | {dim_display:<14} | {finished:<4} | {status}")
    print("=" * 100)

    if preset.get("skip_review") is None:
        skip_review = False
        is_batch_mode = selection in ["y", "jx", "gq", "ld", "bh"] or scope in {"done", "all"} or len(target_entries) > 1
        if is_batch_mode:
            print("\n" + ">>> 🚀 自动化策略配置 <<<")
            if config.get_setting("auto_mode", "", env_name="CEP_AUTO_MODE"):
                skip_review = config.get_setting("auto_mode", False, env_name="CEP_AUTO_MODE")
                if skip_review:
                    print("[🔥] 自动模式已开启，系统将全速处理...")
            else:
                auto_choice = input("[?] 是否开启自动模式 (跳过所有预览审查直接提交)? (y/n): ").lower()
                if auto_choice == "y":
                    skip_review = True
                    print("[🔥] 自动模式已开启，系统将全速处理...")
        preset["skip_review"] = skip_review

    skip_review = bool(preset.get("skip_review"))
    diversity_every = preset.get("diversity_every")
    if not isinstance(diversity_every, int):
        diversity_every = get_diversity_every()
        preset["diversity_every"] = diversity_every

    for _, task in target_entries:
        task_name = task.get("name", "未命名")
        print(f"\n{'-'*20} 正在处理: {task_name} {'-'*20}")
        use_cache_for_this = should_use_cache_for_task(
            preset=preset,
            task_name=task_name,
            diversity_every=diversity_every,
            should_use_cache=should_use_cache,
        )

        if not skip_review:
            preview = task_mgr.submit_task(task, ai_gen, dry_run=True, use_cache=use_cache_for_this)
            payload = preview.get("payload", {})

            print("\n[Payload 审查预览]:")
            print(f"  > 任务名称: {payload.get('name')}")
            print(f"  > 所属维度: {task.get('dimensionName')}")
            print(f"  > 地点: {payload.get('address')}")
            print(f"  > 文案长度: {len(payload.get('content', ''))} 字")
            print(f"  > 预览文案: {payload.get('content')[:100]}...")

            confirm = input("\n[?] 确认提交该任务? (y: 确认提交 / n: 跳过 / q: 退出全部): ").lower()
            if confirm == "n":
                continue
            if confirm == "q":
                break
            upload_paths = preview.get("upload_paths") or []
            attachment_ids = []
            for p in upload_paths:
                img_id = task_mgr.file_service.upload_image(p)
                if img_id:
                    attachment_ids.append(img_id)
            if upload_paths:
                payload["pictureList"] = attachment_ids
            result = task_mgr.submit_task(
                task,
                ai_gen,
                dry_run=False,
                use_cache=use_cache_for_this,
                content_override=payload.get("content"),
                attachment_ids_override=payload.get("pictureList"),
            )
        else:
            result = task_mgr.submit_task(task, ai_gen, dry_run=False, use_cache=use_cache_for_this)

        mark_task_generated(preset=preset, task_name=task_name)
        if result.get("code") == 1:
            print(f"[✅] {task_name} 提交成功！")
        else:
            print(f"[❌] {task_name} 提交失败: {result.get('msg')}")
        if account_username:
            try:
                from .summary_log import append_summary

                append_summary(
                    username=account_username,
                    user_info=getattr(task_mgr, "user_info", {}) or {},
                    task_name=task_name,
                    ok=(result.get("code") == 1),
                    msg=str(result.get("msg") or ""),
                )
            except Exception:
                pass


    print("\n[*] 所有选定任务处理完毕。")
    return preset


def _get_selected_accounts_display_name(selected_indices: set[int], prepared_accounts: list[dict]) -> str:
    """获取已选账号的显示名称字符串，用于 UI 回显"""
    selected_names = []
    for idx in sorted(selected_indices):
        if idx < 0 or idx >= len(prepared_accounts):
            continue
        item = prepared_accounts[idx]
        name = item.get("real_name") or item.get("username") or f"账号{idx + 1}"
        selected_names.append(name)
    
    if not selected_names:
        return ""
    return f"：({', '.join(selected_names)})"


def main():
    try:
        _main_impl()
    except KeyboardInterrupt:
        print("\n\n" + "!" * 60)
        print("  👋 检测到用户中断 (Ctrl+C)，正在安全退出...")
        print("  感谢使用，祝您生活愉快！")
        print("!" * 60 + "\n")
    except Exception as e:
        logger.error(f"系统发生致命错误: {e}", exc_info=True)
        print(f"\n[💥] 程序因不可预知错误崩溃: {e}")

def _main_impl():
    setup_logging()

    print("=" * 60)
    print("      综合评价自动化系统")
    print("=" * 60)

    # 使用新的配置系统
    state = config.state
    print_ai_key_notice()

    sso_base = config.get_setting("sso_base", "https://www.nazhisoft.com")
    ai_gen = AIContentGenerator(model=config.get_setting("model"))

    default_accounts_file = config.get_setting("accounts_file", "accounts.txt", env_name="CEP_ACCOUNTS_FILE", is_path=True)
    path = input(f"[?] 请输入账号txt路径（默认: {default_accounts_file}）: ").strip()
    if not path:
        path = default_accounts_file
    else:
        # 用户手动输入也进行解析
        path = config.resolve_path(path)

    try:
        accounts = load_accounts_from_txt(path)
    except FileNotFoundError:
        print(f"[❌] 文件不存在: {path}")
        return

    if not accounts:
        print("[❌] 账号文件为空或格式不对（每行：账号 空格 密码）。")
        return

    accounts = sorted(accounts, key=lambda x: _account_sort_key(x[0]))
    print(f"[*] 已读取到 {len(accounts)} 个账号，将先对所有账号执行预登录并持久化会话。")

    prepared_accounts = prepare_accounts_for_selection(
        accounts=accounts,
        config=state,
        sso_base=sso_base,
    )

    selectable = [i for i, a in enumerate(prepared_accounts) if a.get("status") == "已就绪"]
    selected = set()  # 默认不选中任何账号，由用户决定
    while True:
        _print_accounts_table(prepared_accounts, config)
        generate_resource_health_report(prepared_accounts)

        print("\n" + "=" * 40)
        names_str = _get_selected_accounts_display_name(selected, prepared_accounts)
        print(f"[*] 当前已选 {len(selected)}/{len(prepared_accounts)} 个账号{names_str}。")
        print("[*] 选择操作：")
        print("    输入序号多选：1 3 4 5 或 1,3,4,5（支持 1-N、区间 1-10）")
        print("    a  : 全选")
        print("    i  : 反选")
        print("    n  : 清空")
        print("    +  : 追加选择（如 +2 +5）")
        print("    -  : 移除选择（如 -1 -3）")
        print("    q  : 退出")
        raw_sel = input("[?] 请选择要处理的账号（回车确认当前选择）: ").strip()
        new_selected, action = parse_account_selection(raw_sel, len(prepared_accounts), selected)
        if action == "cancel":
            print("[*] 用户取消，程序退出。")
            return
        if new_selected is None:
            print("[*] 用户取消，程序退出。")
            return
        selected = new_selected
        if raw_sel.strip() == "":
            break

    if not selected:
        print("[!] 未选择任何账号，程序退出。")
        return

    prepared_accounts = [prepared_accounts[i] for i in sorted(selected)]
    print(f"[*] 将对所选 {len(prepared_accounts)} 个账号批量执行同一套操作。")

    preset = None
    success_count = 0
    for i, item in enumerate(prepared_accounts):
        username = item.get("username")
        password = item.get("password")
        print("\n" + "=" * 60)
        print(f"[*] 批量处理账号 {i+1}/{len(prepared_accounts)}：{username}")
        print("=" * 60)

        task_mgr = item.get("task_mgr")
        if task_mgr is None:
            token_flow = try_use_token_flow(config, username)
            if token_flow:
                task_mgr = token_flow["task_mgr"]
            else:
                print("[❌] 该账号未预登录成功，跳过。")
                continue

        try:
            # 资源深度审计
            missing = task_mgr.audit_resources()
            if missing:
                student_name = getattr(task_mgr, "student_name", "未知")
                print(f"[⚠️] 账号 {username} ({student_name}) 资源审计未通过，将跳过处理。")
                for m in missing:
                    print(f"    - {m}")
                log_missing_resources(
                    student_name,
                    username,
                    missing,
                    detail_info={
                        "school": task_mgr._school_name(),
                        "grade": task_mgr._grade_name(),
                        "class": task_mgr._pure_class_name(),
                    },
                )
                continue

            if preset is None:
                entry = get_account_entry(config, username)
                if isinstance(entry.get("user_info"), dict) and entry.get("token"):
                    display_user_profile(entry.get("user_info"), entry.get("token"))
                preset = run_task_flow(task_mgr, ai_gen, preset=None, strict=True, account_username=username)
                if preset is None:
                    return
            else:
                run_task_flow(task_mgr, ai_gen, preset=preset, strict=False, account_username=username)
            success_count += 1
        except Exception as e:
            logger.error(f"处理账号 {username} 时发生未捕获异常: {e}", exc_info=True)
            print(f"[❌] 账号 {username} 处理失败，已跳过。")

    print(f"\n[🏁] 所有流程处理完毕。成功执行账号数: {success_count}/{len(prepared_accounts)}")
