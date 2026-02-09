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
from .config_store import default_config_paths, get_account_entry, load_accounts_from_txt, load_config, save_config
from .policy import (
    env_bool,
    env_str,
    get_default_task_indices,
    get_default_task_mode,
    get_diversity_every,
    get_ocr_max_retries,
    parse_indices,
    should_use_cache,
)
from .services.auth import ProAuthService
from .services.content_gen import AIContentGenerator
from .services.task_manager import ProTaskManager

logger = logging.getLogger("Main")


def _account_sort_key(username: str):
    u = (username or "").strip()
    if u.isdigit():
        return 0, len(u), u
    return 1, u


def _extract_cached_real_name(config: dict, username: str) -> str:
    entry = get_account_entry(config, username)
    user_info = entry.get("user_info") if isinstance(entry.get("user_info"), dict) else {}
    real_name = (user_info.get("realName") or user_info.get("NAME") or "").strip()
    if real_name:
        return real_name
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    return (info.get("studentName") or "").strip()


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
    *,
    accounts: list[tuple[str, str]],
    config: dict,
    config_file: str,
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

        token_flow = try_use_token_flow(config, username)
        if token_flow:
            entry = get_account_entry(config, username)
            user_info = entry.get("user_info") if isinstance(entry.get("user_info"), dict) else {}
            real_name = (user_info.get("realName") or user_info.get("NAME") or "").strip()
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": real_name,
                    "token": token_flow.get("token") or "",
                    "status": "已就绪",
                    "task_mgr": token_flow.get("task_mgr"),
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

        ok = ocr_login_with_retries(auth, username, password, school_id, max_retries=get_ocr_max_retries())
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

        entry = get_account_entry(config, username)
        entry["token"] = auth.token
        entry["user_info"] = auth.user_info
        save_config(config, config_file)

        task_mgr = build_task_manager(auth.token, auth.user_info, config)
        if not task_mgr.activate_session():
            prepared.append(
                {
                    "username": username,
                    "password": password,
                    "real_name": (auth.user_info or {}).get("realName") or "",
                    "token": auth.token or "",
                    "status": "会话激活失败",
                    "task_mgr": None,
                }
            )
            continue

        prepared.append(
            {
                "username": username,
                "password": password,
                "real_name": (auth.user_info or {}).get("realName") or "",
                "token": auth.token or "",
                "status": "已就绪",
                "task_mgr": task_mgr,
            }
        )

    return prepared


def looks_like_class_meeting(task: dict) -> bool:
    return ProTaskManager._looks_like_class_meeting(task.get("name", ""), task.get("dimensionName", ""))


def is_y_special_task(task: dict) -> bool:
    name = (task.get("name", "") or "")
    return any(word in name for word in ["军训", "国旗下讲话", "劳动"]) or looks_like_class_meeting(task)


def ocr_login_with_retries(auth: ProAuthService, username: str, password: str, school_id: str, max_retries: int = 10):
    def _manual_login(manual_retries: int):
        print("[*] 已切换到手动验证码输入。")
        for attempt in range(manual_retries):
            print(f"[*] 正在尝试手动验证码登录 (第 {attempt+1}/{manual_retries} 次)...")
            img_path, _ = auth.get_captcha(auto_open=True)
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

    if not getattr(auth, "ocr", None):
        print("[⚠️] 未检测到 OCR 引擎（ddddocr），将直接使用手动验证码登录。")
        print("    你可以安装 ddddocr 以启用自动识别：pip install ddddocr")
        return _manual_login(max_retries)

    for attempt in range(max_retries):
        print(f"[*] 正在尝试 OCR 自动登录 (第 {attempt+1}/{max_retries} 次)...")
        _, captcha_code = auth.get_captcha(auto_open=False)
        captcha_code = (captcha_code or "").strip()
        if not captcha_code:
            continue
        if auth.login(username, password, captcha_code, school_id=school_id):
            return True
        print(f"[❌] 第 {attempt+1} 次登录尝试失败。")

    print("[⚠️] OCR 自动识别已连续失败，将回退到手动验证码输入。")
    return _manual_login(max_retries)


def build_task_manager(token: str, user_info: dict, config: dict):
    return ProTaskManager(
        token=token,
        user_info=user_info,
        base_url=config.get("base_url") or "http://139.159.205.146:8280",
        upload_url=config.get("upload_url"),
    )


def try_use_token_flow(config: dict, username: str):
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

    return {"token": token, "user_info": user_info, "task_mgr": task_mgr}


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
                "skip_review": env_bool("CEP_AUTO_MODE", False),
                "confirmed_resubmit": env_bool("CEP_AUTO_CONFIRM_RESUBMIT", False),
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

    base_entries = []
    if selection == "y":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if is_y_special_task(t)]
        print("\n[*] 已选择四大专项任务集合 (班会/军训/国旗/劳动)")
    elif selection == "jx":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if "军训" in t.get("name", "")]
        print("\n[*] 已选择所有“军训”任务")
    elif selection == "gq":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if "国旗下讲话" in t.get("name", "")]
        print("\n[*] 已选择所有“国旗下讲话”任务")
    elif selection == "ld":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if "劳动" in t.get("name", "")]
        print("\n[*] 已选择所有“劳动”相关任务")
    elif selection == "bh":
        base_entries = [(idx, t) for idx, t in enumerate(tasks) if looks_like_class_meeting(t)]
        print("\n[*] 已选择所有“班会”相关任务")
    elif selection == "indices":
        for idx in indices:
            if 0 <= idx < len(tasks):
                base_entries.append((idx, tasks[idx]))
            else:
                print(f"[⚠️] 序号 {idx+1} 超出范围，已忽略。")
        print(f"\n[*] 已选择 {len(base_entries)} 个指定序号任务")

    target_entries = []
    done_count = 0
    pending_count = 0
    for idx, t in base_entries:
        pending = is_pending_status(get_task_status(t))
        if pending:
            pending_count += 1
        else:
            done_count += 1
        if scope == "pending" and pending:
            target_entries.append((idx, t))
        elif scope == "done" and (not pending):
            target_entries.append((idx, t))
        elif scope == "all":
            target_entries.append((idx, t))

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
            if env_str("CEP_AUTO_MODE", ""):
                skip_review = env_bool("CEP_AUTO_MODE", False)
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
    gen_counts = preset.get("gen_counts")
    if not isinstance(gen_counts, dict):
        gen_counts = {}
        preset["gen_counts"] = gen_counts

    for _, task in target_entries:
        task_name = task.get("name", "未命名")
        print(f"\n{'-'*20} 正在处理: {task_name} {'-'*20}")
        gen_key = task_name
        current_count = gen_counts.get(gen_key, 0)
        use_cache_for_this = should_use_cache(int(current_count), diversity_every)

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

        gen_counts[gen_key] = int(current_count) + 1
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


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)
    except ImportError:
        pass
    setup_logging()

    print("=" * 60)
    print("      综合评价自动化系统")
    print("=" * 60)

    config_file, example_file = default_config_paths()
    config = load_config(config_file, example_file)
    print_ai_key_notice()

    env_model = env_str("CEP_MODEL", "")
    if env_model:
        config["model"] = env_model
    env_sso_base = env_str("CEP_SSO_BASE", "")
    if env_sso_base:
        config["sso_base"] = env_sso_base
    env_base_url = env_str("CEP_BASE_URL", "")
    if env_base_url:
        config["base_url"] = env_base_url
    env_upload_url = env_str("CEP_UPLOAD_URL", "")
    if env_upload_url:
        config["upload_url"] = env_upload_url

    sso_base = config.get("sso_base") or "https://www.nazhisoft.com"
    ai_gen = AIContentGenerator(model=config.get("model"))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_accounts_file = env_str("CEP_ACCOUNTS_FILE", "") or os.path.join(base_dir, "accounts.txt")
    path = input(f"[?] 请输入账号txt路径（默认: {default_accounts_file}）: ").strip()
    if not path:
        path = default_accounts_file

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
        config=config,
        config_file=config_file,
        sso_base=sso_base,
    )

    _print_accounts_table(prepared_accounts, config)

    selectable = [i for i, a in enumerate(prepared_accounts) if a.get("status") == "已就绪"]
    selected = set(selectable)
    while True:
        print("\n" + "=" * 40)
        print(f"[*] 当前已选 {len(selected)}/{len(prepared_accounts)} 个账号。")
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

    print(f"\n[*] 批量处理结束：成功处理 {success_count}/{len(prepared_accounts)} 个账号。")
