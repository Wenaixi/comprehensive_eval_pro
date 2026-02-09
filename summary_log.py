import datetime as _dt
import os


def _safe_filename(name: str) -> str:
    s = (name or "").strip()
    out = []
    for ch in s:
        if ch.isalnum() or ch in ("-", "_", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "unknown"


def _extract_class_display(user_info: dict) -> str:
    if not isinstance(user_info, dict):
        return "-"
    info = user_info.get("studentSchoolInfo") if isinstance(user_info.get("studentSchoolInfo"), dict) else {}
    grade = (info.get("gradeName") or "").strip()
    clazz = (info.get("className") or "").strip()
    if not grade and not clazz:
        return "-"
    if grade and clazz and grade in clazz:
        return clazz
    return f"{grade}{clazz}".strip() or "-"


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
    target_dir = (log_dir or os.getenv("CEP_SUMMARY_LOG_DIR") or os.path.join(base_dir, "runtime", "summary_logs")).strip()
    target_dir = os.path.expandvars(os.path.expanduser(target_dir))
    os.makedirs(target_dir, exist_ok=True)

    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    class_display = _extract_class_display(user_info)
    status = "OK" if ok else "FAIL"
    task = (task_name or "").strip() or "-"
    m = (msg or "").replace("\n", " ").strip()
    if len(m) > 120:
        m = m[:120] + "..."

    line = f"{ts} | {class_display:<12} | {status:<4} | {task}"
    if m and (not ok):
        line += f" | {m}"
    line += "\n"

    path = os.path.join(target_dir, f"{_safe_filename(username)}.log")
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)

