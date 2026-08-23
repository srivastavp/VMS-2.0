"""
Centralized local configuration helper.

Reads/writes data/config.json. Used for organization details as well as
visitor-pass printer settings. No server/cloud dependency — purely local
JSON file, consistent with the rest of this offline application.
"""
from pathlib import Path
import json
import logging

APP_BASE = Path(__file__).resolve().parents[1]
DATA_DIR = APP_BASE / "data"
CONFIG_PATH = DATA_DIR / "config.json"

# Config keys used for visitor-pass printing
KEY_PRINTER_NAME = "visitor_pass_printer"
KEY_LABEL_WIDTH_MM = "pass_label_width_mm"
KEY_LABEL_HEIGHT_MM = "pass_label_height_mm"

# Default label size assumption for the Brother QL-800 (62mm continuous DK
# tape is the box-standard media). THIS IS AN ASSUMPTION and should be
# confirmed against the client's actual installed label roll and adjusted
# via Printer Settings if different.
DEFAULT_LABEL_WIDTH_MM = 62.0
DEFAULT_LABEL_HEIGHT_MM = 29.0


def load_config() -> dict:
    """Load configuration from data/config.json."""
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            logging.exception("Failed to load config")
            return {}
    return {}


def save_config(data: dict) -> None:
    """Persist the full configuration dict to data/config.json."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        logging.exception("Failed to save config")


def get_config_value(key: str, default=None):
    return load_config().get(key, default)


def set_config_value(key: str, value) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def get_configured_printer_name() -> str:
    return get_config_value(KEY_PRINTER_NAME, "") or ""


def set_configured_printer_name(name: str) -> None:
    set_config_value(KEY_PRINTER_NAME, name)


def get_label_size_mm() -> tuple:
    """Return (width_mm, height_mm) for the visitor pass label."""
    cfg = load_config()
    width = cfg.get(KEY_LABEL_WIDTH_MM, DEFAULT_LABEL_WIDTH_MM)
    height = cfg.get(KEY_LABEL_HEIGHT_MM, DEFAULT_LABEL_HEIGHT_MM)
    try:
        return float(width), float(height)
    except (TypeError, ValueError):
        return DEFAULT_LABEL_WIDTH_MM, DEFAULT_LABEL_HEIGHT_MM


def get_desktop_dir() -> Path:
    """Best-effort resolution of the current user's Desktop directory."""
    desktop = Path.home() / "Desktop"
    try:
        desktop.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return desktop
