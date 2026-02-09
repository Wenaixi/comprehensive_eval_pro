import logging
import os
from logging.handlers import RotatingFileHandler


def _env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env_str(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env_str(name, "")
    if not raw:
        return default
    raw = raw.lower()
    if raw in ("1", "true", "t", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def setup_logging(
    *,
    level: str | None = None,
    log_file: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    console: bool | None = None,
):
    level = (level or _env_str("CEP_LOG_LEVEL", "INFO")).upper()
    log_file = log_file or _env_str("CEP_LOG_FILE", "")
    max_bytes = max_bytes if max_bytes is not None else _env_int("CEP_LOG_MAX_BYTES", 5 * 1024 * 1024)
    backup_count = backup_count if backup_count is not None else _env_int("CEP_LOG_BACKUP_COUNT", 5)
    console = console if console is not None else _env_bool("CEP_LOG_CONSOLE", True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        ch = logging.StreamHandler()
        ch.setLevel(root.level)
        ch.setFormatter(fmt)
        root.addHandler(ch)

    if log_file:
        log_path = os.path.expandvars(os.path.expanduser(log_file.strip().strip('"').strip("'")))
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        fh = RotatingFileHandler(log_path, maxBytes=max(0, max_bytes), backupCount=max(0, backup_count), encoding="utf-8")
        fh.setLevel(root.level)
        fh.setFormatter(fmt)
        root.addHandler(fh)

    logging.captureWarnings(True)

