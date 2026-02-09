import os
import time


def mask_secret(value: str, prefix: int = 10, suffix: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= prefix + suffix + 3:
        return value
    return f"{value[:prefix]}...{value[-suffix:]}"


def get_task_status(task: dict) -> str:
    return task.get("circleTaskStatus") or task.get("checkResult") or task.get("status") or "未知状态"


def is_pending_status(status: str) -> bool:
    return any(word in (status or "") for word in ["未提交", "待写实", "待完成"])


def print_all_tasks(tasks):
    print("\n" + "=" * 100)
    print(f"{'序号':<4} | {'任务名称':<40} | {'所属维度':<14} | {'完成过':<4} | {'状态'}")
    print("-" * 100)
    for i, t in enumerate(tasks):
        dim_display = t.get("dimensionName") or f"维度{t.get('dimensionId', 'N/A')}"
        status = get_task_status(t)
        finished = "是" if not is_pending_status(status) else "否"
        print(f"{i+1:<4} | {t.get('name', '未命名'):<42} | {dim_display:<14} | {finished:<4} | {status}")
    print("=" * 100)


def print_ai_key_notice():
    api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
    if api_key:
        return
    print("[!] 未配置 SILICONFLOW_API_KEY：AI 在线生成将不可用，将仅使用本地缓存/默认文案。")
    print("    解决：复制 .env.example 为 .env 并填写 SILICONFLOW_API_KEY（不要提交到仓库），或直接设置环境变量。")


def display_user_profile(user_info, token):
    print("\n" + ">>> 👤 用户信息 <<<")

    real_name = user_info.get("realName", "N/A")
    info = user_info.get("studentSchoolInfo", {})

    profile = [
        ("姓名", real_name),
        ("学号", info.get("studentNumber")),
        ("学校", info.get("schoolName") or "福清第一中学"),
        ("班级", f"{info.get('gradeName', '')} {info.get('className', '')}"),
        ("状态", info.get("statusName")),
        ("性别", info.get("genderName")),
        ("生日", info.get("birthdayStr", "").split(" ")[0]),
        ("团员", "是" if info.get("youthLeagueFlag") == 1 else "否"),
        ("座号", info.get("seat")),
        ("学籍号", info.get("nationalStudentNumber")),
    ]

    for label, value in profile:
        if value is not None:
            print(f"  [+] {label:<6} : {value}")

    masked_token = mask_secret(token)
    if masked_token:
        print(f"  [!] {'TOKEN':<6} : {masked_token}")
    print(">>> 完成 <<<\n")
    time.sleep(0.5)

