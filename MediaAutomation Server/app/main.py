"""FastAPI application entrypoint: configure logging, routers and startup tasks."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_config
from app.utils.logger import configure_logging
from app.routes import auth_router, obs_router, streaming_router, system_router
from app.scheduler.tasks import start_scheduler

app = FastAPI(title="Control OBS Local", version="0.1.0")


def _configure_app() -> None:
    """Configure logging and CORS using configuration file."""
    cfg = get_config()
    log_file = cfg.get("logging", {}).get("file", "logs/app.log")
    debug = cfg.get("debug", False)
    configure_logging(log_file, level=logging.DEBUG if debug else logging.INFO)

    # CORS for local network access from mobile devices
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )


_configure_app()

# Register routers with explicit prefixes
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(obs_router, prefix="/obs", tags=["obs"])
app.include_router(streaming_router, prefix="/stream", tags=["stream"])
app.include_router(system_router, prefix="/system", tags=["system"])


@app.on_event("startup")
def _on_startup() -> None:
    """Application startup tasks.

    Start the background scheduler lazily here to avoid creating it at import time.
    """
    # Start scheduler singleton
    start_scheduler()


@app.on_event("shutdown")
def _on_shutdown() -> None:
    """Application shutdown tasks.

    Currently no-op; keep for future cleanup (e.g., closing DB connections).
    """
    logging.getLogger(__name__).info("Shutting down application")
