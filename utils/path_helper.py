import sys, os
from pathlib import Path

def resource_path(relative_path):
    """ Get correct absolute path for PyInstaller and normal run """
    if hasattr(sys, '_MEIPASS'):  # Running inside EXE
        base_path = sys._MEIPASS
    else:  # Running from script
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def _get_local_appdata_dir() -> Path:
    local_appdata = (os.environ.get("LOCALAPPDATA") or "").strip()
    if local_appdata:
        return Path(local_appdata)
    return Path.home() / ".local" / "share"


def get_app_base_dir() -> Path:
    return _get_local_appdata_dir() / "M-Neo VMS"


def get_logs_dir() -> Path:
    return get_app_base_dir() / "logs"


def get_data_dir() -> Path:
    return get_app_base_dir() / "data"


def ensure_app_dirs() -> None:
    get_logs_dir().mkdir(parents=True, exist_ok=True)
    get_data_dir().mkdir(parents=True, exist_ok=True)


def get_log_file_path() -> Path:
    ensure_app_dirs()
    return get_logs_dir() / "visitor_management.log"


def get_db_file_path() -> Path:
    ensure_app_dirs()
    return get_data_dir() / "visitor_management.db"


def get_config_file_path() -> Path:
    ensure_app_dirs()
    return get_data_dir() / "config.json"
