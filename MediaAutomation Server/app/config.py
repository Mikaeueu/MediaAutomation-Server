"""Configuration helpers.

Keep this module minimal to avoid circular imports. It only reads config.json
and returns a dictionary. Callers should handle missing keys and provide defaults.
"""

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"


def get_config() -> Dict[str, Any]:
    """Return parsed configuration from config.json.

    If the file is missing or invalid, return an empty dict to allow the app
    to start with defaults. Callers should validate required keys.
    """
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as cfg:
            return json.load(cfg)
    except Exception:
        return {}
