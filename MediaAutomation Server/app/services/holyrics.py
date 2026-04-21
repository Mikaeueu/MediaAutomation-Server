"""Holyrics client for local Holyrics server.

Provides simple polling helpers and a synchronous client to fetch the
current page/state. Designed to be integrated with the scheduler package
for periodic checks.
"""

from typing import Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)


class HolyricsError(RuntimeError):
    """Raised when Holyrics client encounters an error."""


class HolyricsClient:
    """Simple client to query Holyrics endpoints.

    The client is synchronous and lightweight so it can be used inside
    background jobs or request handlers.
    """

    def __init__(self, base_url: str, timeout: float = 2.0) -> None:
        """Initialize HolyricsClient.

        Args:
            base_url: Base URL of Holyrics local server (e.g., http://127.0.0.1:5000).
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_current(self) -> Optional[Dict[str, Any]]:
        """Get current page/state from Holyrics.

        Returns:
            Parsed JSON response or None on failure.
        """
        url = f"{self.base_url}/current"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url)
                resp.raise_for_status()
                data = resp.json()
                logger.debug("Holyrics current: %s", data)
                return data
        except Exception as exc:
            logger.debug("Holyrics get_current failed: %s", exc)
            return None

    def poll_once(self) -> Optional[Dict[str, Any]]:
        """Alias for get_current to make intent explicit in scheduler usage."""
        return self.get_current()
