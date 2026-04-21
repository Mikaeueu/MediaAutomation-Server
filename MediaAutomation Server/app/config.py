"""Configuration helpers."""

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config.json"


def get_config() -> Dict[str, Any]:
    """Return parsed configuration from config.json.

    Returns:
        Dictionary with configuration values.
    """
    with CONFIG_FILE.open("r", encoding="utf-8") as cfg:
        return json.load(cfg)
