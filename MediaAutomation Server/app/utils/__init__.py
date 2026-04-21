"""Utilities package exports.

Expose commonly used helpers to avoid deep imports across the codebase.
"""

from .secure_store import SecureStore
from .logger import configure_logging, get_logger
from .validators import is_valid_stream_key
from .network import get_local_ip
from .windows_autostart import register_autostart_task, unregister_autostart_task
from .file_lock import FileLock

__all__ = [
    "SecureStore",
    "configure_logging",
    "get_logger",
    "is_valid_stream_key",
    "get_local_ip",
    "register_autostart_task",
    "unregister_autostart_task",
    "FileLock",
]
