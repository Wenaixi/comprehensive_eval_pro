import os
from . import cli as _cli
from . import config_store as _config_store
from . import flows as _flows
from . import policy as _policy

# 导出新配置单例
config = _policy.config

def load_config():
    """保持向前兼容：获取当前状态"""
    return config.state

def save_config(config_dict: dict):
    """保持向前兼容：保存当前状态"""
    # 如果传入的 config_dict 不是当前的 state，则更新它（虽然不推荐这样做）
    if config_dict is not config.state:
        config.state.clear()
        config.state.update(config_dict)
    return config.save_state()


load_accounts_from_txt = _config_store.load_accounts_from_txt

_mask_secret = _cli.mask_secret
display_user_profile = _cli.display_user_profile

_env_str = _policy.env_str
_env_int = _policy.env_int
_env_bool = _policy.env_bool
_get_diversity_every = _policy.get_diversity_every
_should_use_cache = _policy.should_use_cache
_get_ocr_max_retries = _policy.get_ocr_max_retries
_get_default_task_mode = _policy.get_default_task_mode
_get_default_task_indices = _policy.get_default_task_indices
_parse_indices = _policy.parse_indices

_looks_like_class_meeting = _flows.looks_like_class_meeting
_is_y_special_task = _flows.is_y_special_task
_get_task_status = _cli.get_task_status
_is_pending_status = _cli.is_pending_status
run_task_flow = _flows.run_task_flow


def main():
    return _flows.main()


if __name__ == "__main__":
    main()
