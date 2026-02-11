import logging
import os
from logging.handlers import RotatingFileHandler
from .policy import config

class ColoredFormatter(logging.Formatter):
    """自定义 ANSI 彩色日志格式化器"""
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[41m',  # 红底白字
    }
    RESET = '\033[0m'
    TIME_COLOR = '\033[90m'     # 灰色

    def format(self, record):
        level_color = self.COLORS.get(record.levelname, self.RESET)
        
        # 组装彩色格式
        fmt = (
            f"{self.TIME_COLOR}%(asctime)s{self.RESET} | "
            f"{level_color}%(levelname)-7s{self.RESET} | "
            f"\033[35m%(name)s:%(lineno)d\033[0m | "  # 紫色显示文件名行号
            f"%(message)s"
        )
        
        formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(
    *,
    level: str | None = None,
    log_file: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    console: bool | None = None,
):
    level = (level or config.get_setting("log_level", "INFO", env_name="CEP_LOG_LEVEL")).upper()
    log_file = log_file or config.get_setting("log_file", "", env_name="CEP_LOG_FILE", is_path=True)
    max_bytes = max_bytes if max_bytes is not None else config.get_setting("log_max_bytes", 5 * 1024 * 1024, env_name="CEP_LOG_MAX_BYTES")
    backup_count = backup_count if backup_count is not None else config.get_setting("log_backup_count", 5, env_name="CEP_LOG_BACKUP_COUNT")
    console = console if console is not None else config.get_setting("log_console", True, env_name="CEP_LOG_CONSOLE")

    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    for h in list(root.handlers):
        root.removeHandler(h)

    # 普通文件日志格式
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        ch = logging.StreamHandler()
        ch.setLevel(root.level)
        ch.setFormatter(ColoredFormatter())  # 控制台使用彩色格式
        root.addHandler(ch)

    if log_file:
        log_path = log_file # 已经是解析过的绝对路径了
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        try:
            fh = RotatingFileHandler(log_path, maxBytes=max(0, max_bytes), backupCount=max(0, backup_count), encoding="utf-8")
            fh.setLevel(root.level)
            fh.setFormatter(file_fmt)
            root.addHandler(fh)
        except Exception as e:
            print(f"无法初始化文件日志: {e}")
