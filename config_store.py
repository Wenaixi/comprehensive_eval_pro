import json
import os


def default_config_paths(base_dir: str | None = None) -> tuple[str, str]:
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.getenv("CEP_CONFIG_FILE") or os.path.join(base_dir, "config.json")
    example_file = os.getenv("CEP_CONFIG_EXAMPLE_FILE") or os.path.join(base_dir, "config.example.json")
    return config_file, example_file


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


def load_config(config_file: str, example_file: str) -> dict:
    if not os.path.exists(config_file) and os.path.exists(example_file):
        try:
            with open(example_file, "r", encoding="utf-8") as f:
                example = json.load(f)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(example, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            loaded = {}
    else:
        loaded = {}

    config = {
        "model": "deepseek-ai/DeepSeek-V3.2",
        "username": "",
        "password": "",
        "token": "",
        "user_info": {},
        "accounts": {},
        "base_url": "http://139.159.205.146:8280",
        "upload_url": "http://doc.nazhisoft.com/common/upload/uploadImage?bussinessType=12&groupName=other",
        "sso_base": "https://www.nazhisoft.com",
    }

    if isinstance(loaded, dict):
        config.update({k: v for k, v in loaded.items() if v is not None})

    if not isinstance(config.get("accounts"), dict):
        config["accounts"] = {}

    legacy_username = (config.get("username") or "").strip()
    legacy_token = (config.get("token") or "").strip()
    legacy_user_info = config.get("user_info") if isinstance(config.get("user_info"), dict) else {}
    if legacy_username and legacy_token and legacy_username not in config["accounts"]:
        config["accounts"][legacy_username] = {"token": legacy_token, "user_info": legacy_user_info}

    return config


def save_config(config: dict, config_file: str):
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


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

