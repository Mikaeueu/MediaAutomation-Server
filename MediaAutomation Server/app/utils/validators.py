"""Validation helpers used across services and routes."""

import re
from typing import Optional

# Basic heuristic for stream keys (YouTube/Facebook style)
_STREAM_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{8,}$")


def is_valid_stream_key(key: Optional[str]) -> bool:
    """Return True if the provided key looks like a valid stream key.

    This is a heuristic check to provide early feedback in the UI. It does
    not guarantee the key is valid for the provider.

    Args:
        key: Stream key string or None.

    Returns:
        bool: True if key matches basic pattern.
    """
    if not key:
        return False
    return bool(_STREAM_KEY_RE.match(key))
