import datetime as _dt
import os
import threading

from .policy import config

# 全局线程锁，确保日志写入的原子性
_log_lock = threading.Lock()


def _safe_filename(name: str) -> str:
    s = (name or "").strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "unknown"


def _extract_school_name(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return "未知学校"
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    return (info.get("schoolName") or "未知学校").strip()


def _extract_grade_name(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return "未知年级"
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    return (info.get("gradeName") or "未知年级").strip()


def _extract_class_display(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return "未知班级"
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    grade = (info.get("gradeName") or "").strip()
    clazz = (info.get("className") or "").strip()
    if not grade and not clazz:
        return "未知班级"
    if grade and clazz and grade in clazz:
        return clazz
    return f"{grade}{clazz}".strip() or "未知班级"


def _extract_pure_class_name(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return "未知班级"
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    return (info.get("className") or "未知班级").strip()


def append_summary(
    *,
    username: str,
    user_info: dict,
    task_name: str,
    ok: bool,
    msg: str = "",
    log_dir: str | None = None,
):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_log_dir = (log_dir or config.get_setting("summary_log_dir", os.path.join(base_dir, "runtime", "summary_logs"), env_name="CEP_SUMMARY_LOG_DIR")).strip()
    
    # 1. 提取学校、年级和班级，构建分层路径 (彻底分层：学校/年级/班级)
    school_name = _safe_filename(_extract_school_name(user_info))
    grade_name = _safe_filename(_extract_grade_name(user_info))
    class_name = _safe_filename(_extract_pure_class_name(user_info))
    
    target_dir = os.path.join(root_log_dir, school_name, grade_name, class_name)
    target_dir = os.path.expandvars(os.path.expanduser(target_dir))
    os.makedirs(target_dir, exist_ok=True)

    # 2. 准备彩色日志行 (使用 ANSI 转义码，Windows 10+ 原生支持，也可配合 colorama)
    # 颜色定义
    C_RESET = "\033[0m"
    C_TIME = "\033[90m"     # 灰色
    C_CLASS = "\033[36m"    # 青色
    C_OK = "\033[32m"       # 绿色
    C_FAIL = "\033[31m"      # 红色
    C_TASK = "\033[33m"     # 黄色
    C_MSG = "\033[91m"      # 亮红

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    class_display = _extract_class_display(user_info)
    status_text = "OK" if ok else "FAIL"
    status_color = C_OK if ok else C_FAIL
    task = (task_name or "").strip() or "-"
    
    m = (msg or "").replace("\n", " ").strip()
    if len(m) > 120:
        m = m[:120] + "..."

    # 构建带颜色的行
    line = f"{C_TIME}{ts}{C_RESET} | {C_CLASS}{class_display:<12}{C_RESET} | {status_color}{status_text:<4}{C_RESET} | {C_TASK}{task}{C_RESET}"
    if m and (not ok):
        line += f" | {C_MSG}{m}{C_RESET}"
    line += "\n"

    path = os.path.join(target_dir, f"{_safe_filename(username)}.log")
    with _log_lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)

