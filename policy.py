import os


def env_str(name: str, default: str = "") -> str:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip()


def env_int(name: str, default: int) -> int:
    raw = env_str(name, "")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    raw = env_str(name, "")
    if not raw:
        return default
    raw = raw.lower()
    if raw in ("1", "true", "t", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "f", "no", "n", "off"):
        return False
    return default


def get_diversity_every() -> int:
    return env_int("CEP_DIVERSITY_EVERY", 3)


def should_use_cache(submit_index: int, diversity_every: int) -> bool:
    if diversity_every <= 0:
        return True
    if submit_index < 0:
        return True
    return (submit_index + 1) % diversity_every != 0


def get_ocr_max_retries() -> int:
    v = env_int("CEP_OCR_MAX_RETRIES", 10)
    return v if v > 0 else 10


def get_default_task_mode() -> str:
    return env_str("CEP_DEFAULT_TASK_MODE", "").lower()


def get_default_task_indices() -> str:
    return env_str("CEP_DEFAULT_TASK_INDICES", "")


def parse_indices(text: str):
    indices = []
    for part in (text or "").split():
        if part.isdigit():
            indices.append(int(part) - 1)
    return sorted(set(indices))
