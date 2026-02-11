import json
import os
import tempfile
import time
import random
import shutil

try:
    import yaml
except ImportError:
    yaml = None

def get_base_dir():
    return os.path.dirname(os.path.abspath(__file__))

def get_configs_dir():
    return os.path.join(get_base_dir(), "configs")

def get_configs_example_dir():
    return os.path.join(get_base_dir(), "configs.example")

def ensure_configs_exist():
    configs_dir = get_configs_dir()
    example_dir = get_configs_example_dir()
    
    if not os.path.exists(configs_dir):
        os.makedirs(configs_dir, exist_ok=True)
        
    # 同步 settings.yaml
    settings_file = os.path.join(configs_dir, "settings.yaml")
    settings_example = os.path.join(example_dir, "settings.example.yaml")
    if not os.path.exists(settings_file) and os.path.exists(settings_example):
        shutil.copy2(settings_example, settings_file)
        
    # 同步 state.json
    state_file = os.path.join(configs_dir, "state.json")
    state_example = os.path.join(example_dir, "state.example.json")
    if not os.path.exists(state_file) and os.path.exists(state_example):
        shutil.copy2(state_example, state_file)

def load_yaml_config(file_path: str) -> dict:
    if not yaml:
        return {}
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def load_json_config(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {}
    
    max_retries = 5
    for i in range(max_retries):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (PermissionError, json.JSONDecodeError):
            if i == max_retries - 1:
                return {}
            time.sleep(0.05 * (2 ** i) + random.uniform(0, 0.1))
        except Exception:
            return {}
    return {}

def save_json_config(config: dict, file_path: str):
    directory = os.path.dirname(os.path.abspath(file_path))
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".state_", suffix=".tmp", text=True)
    
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        max_retries = 5
        for i in range(max_retries):
            try:
                # 在 Windows 上，os.replace 可以覆盖已存在的文件，而 os.rename 会报 FileExistsError
                os.replace(temp_path, file_path)
                break
            except PermissionError:
                if i == max_retries - 1:
                    raise
                time.sleep(0.05 * (2 ** i) + random.uniform(0, 0.1))
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise e

def load_accounts_from_txt(file_path: str):
    if not file_path:
        return []
    file_path = os.path.expandvars(os.path.expanduser(file_path.strip().strip('"').strip("'")))
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    accounts = []
    with open(file_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = (raw_line or "").strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            username = parts[0].strip()
            password = parts[1].strip()
            if username and password:
                accounts.append((username, password))
    return accounts

def get_account_entry(config: dict, username: str) -> dict:
    accounts = config.get("accounts")
    if not isinstance(accounts, dict):
        accounts = {}
        config["accounts"] = accounts
    entry = accounts.get(username)
    if not isinstance(entry, dict):
        entry = {}
        accounts[username] = entry
    return entry
