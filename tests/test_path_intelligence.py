import os
import pytest
from comprehensive_eval_pro.policy import ConfigManager

def test_resolve_path_basic():
    """测试基本的路径解析逻辑"""
    config = ConfigManager()
    base_dir = config.base_dir
    
    # 1. 测试相对路径
    assert config.resolve_path("accounts.txt") == os.path.join(base_dir, "accounts.txt")
    assert config.resolve_path("runtime/app.log") == os.path.join(base_dir, "runtime", "app.log")
    
    # 2. 测试带 ./ 的路径
    assert config.resolve_path("./accounts.txt") == os.path.join(base_dir, "accounts.txt")
    
    # 3. 测试绝对路径 (Windows 风格)
    abs_path = "C:\\test\\accounts.txt"
    assert config.resolve_path(abs_path) == abs_path
    
    # 4. 测试带引号的路径
    assert config.resolve_path("'accounts.txt'") == os.path.join(base_dir, "accounts.txt")
    assert config.resolve_path('"accounts.txt"') == os.path.join(base_dir, "accounts.txt")

def test_get_setting_with_path():
    """测试 get_setting 自动解析路径"""
    config = ConfigManager()
    base_dir = config.base_dir
    
    # 模拟配置中存在相对路径
    config.settings["test_path_key"] = "test_sub/file.txt"
    
    # 不开启 is_path
    assert config.get_setting("test_path_key") == "test_sub/file.txt"
    
    # 开启 is_path
    resolved = config.get_setting("test_path_key", is_path=True)
    assert resolved == os.path.join(base_dir, "test_sub", "file.txt")
    assert os.path.isabs(resolved)

def test_resolve_path_env_vars(monkeypatch):
    """测试环境变量扩展"""
    config = ConfigManager()
    
    # 设置模拟环境变量
    monkeypatch.setenv("MY_TEST_VAR", "my_value")
    
    # Windows 风格环境变量
    path_with_env = "%MY_TEST_VAR%/data.txt"
    resolved = config.resolve_path(path_with_env)
    assert "my_value" in resolved
    assert resolved.endswith("data.txt")

if __name__ == "__main__":
    pytest.main([__file__])
