"""Logging helpers.

Provide a small centralized logging configuration to be used by the app.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def configure_logging(log_file: Optional[str] = None, level: int = logging.INFO) -> None:
    """Configure root logger with console and optional rotating file handler.

    Args:
        log_file: Optional path to a log file. If provided, a rotating file
            handler will be added.
        level: Logging level (default INFO).
    """
    root = logging.getLogger()
    if root.handlers:
        # Already configured
        return

    root.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(str(path), maxBytes=10 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(name)
