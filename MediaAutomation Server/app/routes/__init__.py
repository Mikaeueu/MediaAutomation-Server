"""Routes package initializer.

This module exposes the FastAPI routers defined in the package so they can be
imported cleanly from `app.routes`. Import names are explicit and stable to
avoid naming conflicts when registering routers in `app.main`.
"""

from .auth import router as auth_router
from .obs_control import router as obs_router
from .streaming import router as streaming_router
from .system_control import router as system_router

__all__ = [
    "auth_router",
    "obs_router",
    "streaming_router",
    "system_router",
]
