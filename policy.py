import os
from typing import Any, List
from . import config_store as _store

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        _store.ensure_configs_exist()
        self.base_dir = _store.get_base_dir()
        self.configs_dir = _store.get_configs_dir()
        self.settings_path = os.path.join(self.configs_dir, "settings.yaml")
        self.state_path = os.path.join(self.configs_dir, "state.json")
        
        self.settings = _store.load_yaml_config(self.settings_path)
        self.state = _store.load_json_config(self.state_path)
        self._initialized = True

    def resolve_path(self, path: str) -> str:
        """
        智能路径解析：
        1. 展开环境变量和用户目录
        2. 如果是相对路径，自动拼接为相对于项目根目录 (base_dir) 的绝对路径
        """
        if not path:
            return path
        
        # 1. 展开环境变量 (如 %TEMP%) 和 ~
        path = os.path.expandvars(os.path.expanduser(path.strip().strip('"').strip("'")))
        
        # 2. 判断是否为绝对路径
        if os.path.isabs(path):
            return path
        
        # 3. 相对路径则拼接 base_dir
        return os.path.normpath(os.path.join(self.base_dir, path))

    def get_setting(self, key: str, default: Any = None, env_name: str = None, is_path: bool = False) -> Any:
        # 1. 优先检查环境变量
        val = None
        if env_name:
            env_val = os.getenv(env_name)
            if env_val is not None:
                val = self._parse_val(env_val, type(default) if default is not None else str)
        
        # 2. 检查配置文件
        if val is None:
            val = self.settings.get(key)
            
        # 3. 使用默认值
        if val is None:
            val = default
            
        # 4. 如果是路径，进行智能解析
        if is_path and isinstance(val, str):
            return self.resolve_path(val)
            
        return val

    def _parse_val(self, val: str, target_type: type) -> Any:
        if target_type == bool:
            return str(val).lower() in ("1", "true", "t", "yes", "y", "on")
        if target_type == int:
            try:
                return int(val)
            except ValueError:
                return 0
        if target_type == list:
            return [x.strip() for x in str(val).split(",") if x.strip()]
        return str(val).strip()

    def save_state(self):
        _store.save_json_config(self.state, self.state_path)

    # --- 兼容性方法 (Compatibility methods) ---
    # 使 ConfigManager 行为在某种程度上像 dict，主要用于 get_account_entry 等操作动态状态的方法

    def get(self, key: str, default: Any = None) -> Any:
        """从动态状态 (state) 中获取值，主要用于兼容旧代码"""
        return self.state.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.state[key]

    def __setitem__(self, key: str, value: Any):
        self.state[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.state

# 全局配置实例
config = ConfigManager()

def env_str(name: str, default: str = "") -> str:
    """兼容旧代码的 env_str，优先读配置"""
    # 尝试寻找对应的配置键
    key = name.lower()
    if key.startswith("cep_"):
        key = key[4:]
    return config.get_setting(key, default, env_name=name)

def env_int(name: str, default: int) -> int:
    key = name.lower()
    if key.startswith("cep_"):
        key = key[4:]
    return config.get_setting(key, default, env_name=name)

def env_bool(name: str, default: bool) -> bool:
    key = name.lower()
    if key.startswith("cep_"):
        key = key[4:]
    return config.get_setting(key, default, env_name=name)

# --- 具体配置获取函数 ---

def get_diversity_every() -> int:
    return config.get_setting("diversity_every", 3, env_name="CEP_DIVERSITY_EVERY")

def should_use_cache(submit_index: int, diversity_every: int) -> bool:
    if diversity_every <= 0:
        return True
    if submit_index < 0:
        return True
    return (submit_index + 1) % diversity_every != 0

def get_ocr_max_retries() -> int:
    return config.get_setting("ocr_max_retries", 10, env_name="CEP_OCR_MAX_RETRIES")

def get_ai_ocr_max_retries() -> int:
    v = config.get_setting("ai_ocr_max_retries", 0, env_name="CEP_AI_OCR_MAX_RETRIES")
    if v > 0:
        return v
    return get_ai_ocr_retries_per_model()

def get_ai_ocr_retries_per_model() -> int:
    return config.get_setting("ai_ocr_retries_per_model", 3, env_name="CEP_AI_OCR_RETRIES_PER_MODEL")

def get_ddddocr_max_retries() -> int:
    v = config.get_setting("ddddocr_max_retries", -1, env_name="CEP_DDDDOCR_MAX_RETRIES")
    if v >= 0:
        return v
    legacy = config.get_setting("ddddocr_max_retries", 9, env_name="CEP_DDDOCR_MAX_RETRIES")
    return legacy

def get_manual_ocr_max_retries() -> int:
    default_retries = get_ocr_max_retries()
    v = config.get_setting("manual_ocr_max_retries", -1, env_name="CEP_MANUAL_OCR_MAX_RETRIES")
    if v >= 0:
        return v
    return 3 # 默认手动 3 次

def get_default_task_mode() -> str:
    return config.get_setting("default_task_mode", "", env_name="CEP_DEFAULT_TASK_MODE").lower()

def get_default_task_indices() -> str:
    return config.get_setting("default_task_indices", "", env_name="CEP_DEFAULT_TASK_INDICES")

def parse_indices(text: str):
    indices = []
    for part in (text or "").split():
        if part.isdigit():
            indices.append(int(part) - 1)
    return sorted(set(indices))
