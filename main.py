import json
import logging
import os
import time
import sys
import re

# 自动处理模块搜索路径，确保在项目任何位置都能正确导入
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 即使在 comprehensive_eval_pro 目录下运行，也能通过完整路径导入
from comprehensive_eval_pro.services.auth import ProAuthService
from comprehensive_eval_pro.services.task_manager import ProTaskManager
from comprehensive_eval_pro.services.content_gen import AIContentGenerator

# 加载 .env 环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger("Main")

# 配置文件绝对路径
CONFIG_FILE = os.getenv("CEP_CONFIG_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CONFIG_EXAMPLE_FILE = os.getenv("CEP_CONFIG_EXAMPLE_FILE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.json")

def _mask_secret(value: str, prefix: int = 10, suffix: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= prefix + suffix + 3:
        return value
    return f"{value[:prefix]}...{value[-suffix:]}"

def _looks_like_class_meeting(task_name: str) -> bool:
    name = re.sub(r"\s+", "", task_name or "")
    if "班会" in name:
        return True
    if re.search(r"班[《“\"']", name):
        return True
    return False

def _print_ai_key_notice():
    api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
    if api_key:
        return
    print("[!] 未配置 SILICONFLOW_API_KEY：AI 在线生成将不可用，将仅使用本地缓存/默认文案。")
    print("    解决：复制 .env.example 为 .env 并填写 SILICONFLOW_API_KEY（不要提交到仓库），或直接设置环境变量。")

def load_config():
    if not os.path.exists(CONFIG_FILE) and os.path.exists(CONFIG_EXAMPLE_FILE):
        try:
            with open(CONFIG_EXAMPLE_FILE, "r", encoding="utf-8") as f:
                example = json.load(f)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(example, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            loaded = {}
    else:
        loaded = {}

    config = {
        "model": "deepseek-ai/DeepSeek-V3.2",
        "username": "",
        "password": "",
        "token": "",
        "user_info": {},
        "base_url": "http://139.159.205.146:8280",
        "upload_url": "http://doc.nazhisoft.com/common/upload/uploadImage?bussinessType=12&groupName=other",
        "sso_base": "https://www.nazhisoft.com",
    }

    if isinstance(loaded, dict):
        config.update({k: v for k, v in loaded.items() if v is not None})
    return config

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def display_user_profile(user_info, token):
    """
    极简黑客风用户信息展示
    """
    print("\n" + ">>> 👤 用户信息 <<<")
    
    # 提取基本信息
    real_name = user_info.get('realName', 'N/A')
    info = user_info.get('studentSchoolInfo', {})
    
    # 定义展示项
    profile = [
        ("姓名", real_name),
        ("学号", info.get('studentNumber')),
        ("学校", info.get('schoolName') or "福清第一中学"),
        ("班级", f"{info.get('gradeName', '')} {info.get('className', '')}"),
        ("状态", info.get('statusName')),
        ("性别", info.get('genderName')),
        ("生日", info.get('birthdayStr', '').split(' ')[0]),
        ("团员", "是" if info.get('youthLeagueFlag') == 1 else "否"),
        ("座号", info.get('seat')),
        ("学籍号", info.get('nationalStudentNumber')),
    ]
    
    # 循环打印
    for label, value in profile:
        if value is not None:
            print(f"  [+] {label:<6} : {value}")
    
    masked_token = _mask_secret(token)
    if masked_token:
        print(f"  [!] {'TOKEN':<6} : {masked_token}")
    print(">>> 完成 <<<\n")
    time.sleep(0.5)

def main():
    print("="*60)
    print("      综合评价自动化系统")
    print("="*60)

    config = load_config()
    _print_ai_key_notice()
    token = config.get("token")
    
    if token:
        print(f"[*] 系统状态: 检测到持久化 Token ({_mask_secret(token)})")
    else:
        print(f"[*] 系统状态: 未检测到持久化 Token，需要执行登录。")

    # 1. 认证流程
    auth = ProAuthService(sso_base=config.get("sso_base") or "https://www.nazhisoft.com")
    
    use_existing = False
    if token:
        # 如果有持久化信息，尝试恢复
        user_info = config.get("user_info")
        if user_info:
            print(f"[*] 欢迎回来，{user_info.get('realName', '同学')}！")
        
        choice = input(f"[*] 检测到已有登录会话，是否直接进入？(y: 直接进入 / n: 登录新账号): ").lower()
        if choice == 'y' or choice == '':
            use_existing = True
        else:
            print("[*] 正在准备切换账号...")
            token = None
            config["user_info"] = {} # 切换账号清空旧信息

    if not use_existing:
        username = config.get("username") or input("请输入学生学号: ")
        password = config.get("password") or input("请输入登录密码: ")
        
        # 先获取学校 ID
        print(f"[*] 正在溯源学校信息...")
        school_id = auth.get_school_id(username)
        if not school_id:
            print("[❌] 无法溯源学校 ID，请检查学号是否正确。")
            return

        max_retries = 3
        for attempt in range(max_retries):
            if attempt == 0:
                print(f"[*] 正在尝试 OCR 自动登录 (第 {attempt+1} 次)...")
                captcha_path, captcha_code = auth.get_captcha(auto_open=False)
            else:
                print(f"\n[⚠️] 登录失败，尝试手动输入 (第 {attempt+1} 次)...")
                captcha_path, _ = auth.get_captcha(auto_open=True)
                captcha_code = input("请输入验证码 (查看弹出的图片): ").strip()

            if not captcha_code:
                continue

            if auth.login(username, password, captcha_code, school_id=school_id):
                token = auth.token
                # 立即持久化 Token 和 用户信息
                config["token"] = token
                config["user_info"] = auth.user_info
                save_config(config)
                print("\n[✅] 登录成功并已保存会话！")
                
                # 展示装逼信息 (极简风 + 红色 Token)
                display_user_profile(auth.user_info, token)
                break
            else:
                print(f"[❌] 第 {attempt+1} 次登录尝试失败。")
                if attempt == max_retries - 1:
                    print("[💥] 达到最大重试次数，程序退出。")
                    return

    if not token:
        print("[❌] 未能获取有效 Token，请重新运行并登录。")
        return
    else:
        # 确保后续使用的 token 是最新的
        config["token"] = token
        save_config(config)

    # 2. 初始化业务管理
    ai_gen = AIContentGenerator(model=config.get("model"))
    # 注入 user_info 解决“未知”问题
    task_mgr = ProTaskManager(
        token=token,
        user_info=config.get("user_info"),
        base_url=config.get("base_url") or "http://139.159.205.146:8280",
        upload_url=config.get("upload_url"),
    )
    
    # 激活 Session (获取学生姓名)
    if not task_mgr.activate_session():
        print("[⚠️] 业务 Session 激活失败 (Token 可能已过期)。")
        # 清除无效 Token
        if "token" in config:
            del config["token"]
            save_config(config)
        print("[*] 请重新运行程序进行登录。")
        return

    # 3. 获取任务
    print("[*] 正在扫描全维度任务...")
    tasks = task_mgr.get_all_tasks(force_refresh=False) # 内部不再重复 activate

    unsubmitted_tasks = []
    for t in tasks:
        # 优先使用 circleTaskStatus，兼容 checkResult 或 status
        status = t.get('circleTaskStatus') or t.get('checkResult') or t.get('status') or "未知状态"
        name = t.get('name', '未知任务')
        
        if any(word in status for word in ["未提交", "待写实", "待完成"]):
            unsubmitted_tasks.append(t)
        else:
            logger.debug(f"跳过已处理任务: {name} [状态: {status}]")

    print(f"[+] 扫描完成。共发现 {len(tasks)} 个任务，其中 {len(unsubmitted_tasks)} 个处于待处理状态。")
    
    if unsubmitted_tasks:
        print("\n" + "="*80)
        print(f"{'序号':<4} | {'任务名称':<40} | {'所属维度'}")
        print("-" * 80)
        for i, t in enumerate(unsubmitted_tasks):
            # 优先显示维度名称
            dim_display = t.get('dimensionName') or f"维度{t.get('dimensionId', 'N/A')}"
            print(f"{i+1:<4} | {t.get('name', '未命名'):<42} | {dim_display}")
        print("="*80)
    
    if not unsubmitted_tasks:
        print("[!] 没有待处理的任务，程序退出。")
        return

    # 4. 全局处理确认 (支持单点测试与关键词批量)
    print("\n" + "="*40)
    prompt = f"[*] 发现 {len(unsubmitted_tasks)} 个待办任务。\n"
    prompt += "[*] 操作指南:\n"
    prompt += "    [y]  : 处理 班会 + 军训 + 国旗下讲话 + 劳动 (四大专项一键批量)\n"
    prompt += "    [bh] : 自动筛选所有“班会”任务\n"
    prompt += "    [gq] : 自动筛选所有“国旗下讲话”任务\n"
    prompt += "    [ld] : 自动筛选所有“劳动”相关任务\n"
    prompt += "    [bh] : 自动筛选所有“班会”相关任务\n"
    prompt += "    [序号] : 处理单个或多个序号 (如: 1 或 1 3 5)\n"
    prompt += "    [n]  : 退出程序\n"
    print(prompt)
    raw_choice = input("[?] 请输入你的选择: ").strip().lower()

    target_tasks = []
    
    # 解析输入逻辑
    if raw_choice == 'y':
        # 专项批量：包含 班会、军训、国旗、劳动
        target_tasks = [
            t
            for t in unsubmitted_tasks
            if (
                any(word in (t.get("name", "") or "") for word in ["军训", "国旗下讲话", "劳动"])
                or _looks_like_class_meeting(t.get("name", ""))
            )
        ]
        print(f"\n[*] 已筛选出 {len(target_tasks)} 个专项任务 (班会/军训/国旗/劳动)")
    elif raw_choice == 'jx':
        target_tasks = [t for t in unsubmitted_tasks if "军训" in t.get('name', '')]
        print(f"\n[*] 已筛选出 {len(target_tasks)} 个“军训”任务:")
    elif raw_choice == 'gq':
        target_tasks = [t for t in unsubmitted_tasks if "国旗下讲话" in t.get('name', '')]
        print(f"\n[*] 已筛选出 {len(target_tasks)} 个“国旗下讲话”任务:")
    elif raw_choice == 'ld':
        target_tasks = [t for t in unsubmitted_tasks if "劳动" in t.get('name', '')]
        print(f"\n[*] 已筛选出 {len(target_tasks)} 个“劳动”相关任务:")
    elif raw_choice == 'bh':
        target_tasks = [t for t in unsubmitted_tasks if _looks_like_class_meeting(t.get("name", ""))]
        print(f"\n[*] 已筛选出 {len(target_tasks)} 个“班会”相关任务:")
    elif any(c.isdigit() for c in raw_choice):
        # 支持空格分隔的多个序号
        try:
            indices = [int(i) - 1 for i in raw_choice.split() if i.isdigit()]
            for idx in indices:
                if 0 <= idx < len(unsubmitted_tasks):
                    target_tasks.append(unsubmitted_tasks[idx])
                else:
                    print(f"[⚠️] 序号 {idx+1} 超出范围，已忽略。")
            if target_tasks:
                print(f"[*] 已选择 {len(target_tasks)} 个指定序号的任务。")
        except ValueError:
            print("[❌] 序号解析失败，请确保输入格式正确（如: 1 3 5）。")
            return
    else:
        print("[*] 用户取消或输入无效，程序退出。")
        return

    # 打印选中的任务列表确认
    if target_tasks:
        print("\n" + "="*80)
        print(f"{'序号':<4} | {'任务名称':<40} | {'所属维度'}")
        print("-" * 80)
        for i, t in enumerate(target_tasks):
            dim_display = t.get('dimensionName') or f"维度{t.get('dimensionId', 'N/A')}"
            print(f"{i+1:<4} | {t.get('name', '未命名'):<42} | {dim_display}")
        print("="*80)

    if not target_tasks:
        print("[!] 没有待处理的任务，程序退出。")
        return

    # 5. 究极流程控制
    skip_review = False
    use_cache_pref = True
    
    # 只要是批量筛选指令（y, jx, gq, ld, bh, test）或选择了多个任务，就进入策略配置
    is_batch_mode = raw_choice in ['y', 'jx', 'gq', 'ld', 'bh', 'test'] or len(target_tasks) > 1
    
    if is_batch_mode:
        print("\n" + ">>> 🚀 自动化策略配置 <<<")
        auto_choice = input("[?] 是否开启自动模式 (跳过所有预览审查直接提交)? (y/n): ").lower()
        if auto_choice == 'y':
            skip_review = True
            print("[🔥] 自动模式已开启，系统将全速处理...")
        
        cache_choice = input("[?] 是否优先使用已持久化的相同提示词响应? (y: 使用持久化库 / n: 生成新响应增加多样性): ").lower().strip()
        if cache_choice == 'n':
            use_cache_pref = False
            print("[🌈] 多样性模式已开启，将为任务生成并持久化全新响应...")
        else:
            print("[⚡] 极速模式已开启，将从持久化库中轮询匹配响应...")

    # 6. 遍历处理目标任务
    for task in target_tasks:
        task_name = task.get('name', '未命名')
        print(f"\n{'-'*20} 正在处理: {task_name} {'-'*20}")
        
        # 预览/处理
        if not skip_review:
            preview = task_mgr.submit_task(task, ai_gen, dry_run=True, use_cache=use_cache_pref)
            payload = preview.get('payload', {})
            
            print("\n[Payload 审查预览]:")
            print(f"  > 任务名称: {payload.get('name')}")
            print(f"  > 所属维度: {task.get('dimensionName')}")
            print(f"  > 地点: {payload.get('address')}")
            print(f"  > 文案长度: {len(payload.get('content', ''))} 字")
            print(f"  > 预览文案: {payload.get('content')[:100]}...")
            
            confirm = input(f"\n[?] 确认提交该任务? (y: 确认提交 / n: 跳过 / q: 退出全部): ").lower()
            if confirm == 'n':
                continue
            elif confirm == 'q':
                break
        
        # 正式提交 (如果开启了 skip_review，则直接运行到这里)
        result = task_mgr.submit_task(task, ai_gen, dry_run=False, use_cache=use_cache_pref)
        if result.get('code') == 1:
            print(f"[✅] {task_name} 提交成功！")
        else:
            print(f"[❌] {task_name} 提交失败: {result.get('msg')}")

    print("\n[*] 所有选定任务处理完毕。")

if __name__ == "__main__":
    main()
