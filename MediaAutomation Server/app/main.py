"""FastAPI application entrypoint and router registration."""

import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth as auth_router
from app.routes import obs_control as obs_router

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config(path: Path) -> dict:
    """Load JSON configuration from disk.

    Args:
        path: Path to the config.json file.

    Returns:
        Parsed configuration dictionary.
    """
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


config = load_config(CONFIG_PATH)

app = FastAPI(title="Control OBS Local", version="0.1.0")

# CORS for local network access from mobile devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
app.include_router(obs_router.router, prefix="/obs", tags=["obs"])
