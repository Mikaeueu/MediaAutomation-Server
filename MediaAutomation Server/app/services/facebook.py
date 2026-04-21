"""Facebook Graph API client (minimal).

Provides a small client to create a Page live video. This is a pragmatic,
explicit implementation that returns the most useful fields. In production
you must implement token management, retries and robust error handling.
"""

from typing import Dict, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class FacebookAPIError(RuntimeError):
    """Raised when Facebook API returns an error."""


class FacebookService:
    """Client for Facebook Page Live Video creation."""

    GRAPH_BASE = "https://graph.facebook.com/v16.0"

    def __init__(self, page_access_token: str, page_id: str) -> None:
        """Initialize FacebookService.

        Args:
            page_access_token: Long-lived page access token with pages_manage_live.
            page_id: Facebook Page ID where the live will be created.
        """
        if not page_access_token or not page_id:
            raise ValueError("page_access_token and page_id are required")
        self.token = page_access_token
        self.page_id = page_id

    def create_live(self, title: str, description: str, status: str = "SCHEDULED") -> Dict[str, Optional[str]]:
        """Create a live video on the configured Facebook Page.

        Args:
            title: Title for the live.
            description: Description for the live.
            status: 'LIVE_NOW' or 'SCHEDULED' (default).

        Returns:
            Dict with keys 'id', 'stream_url', 'stream_key'.

        Raises:
            FacebookAPIError: On HTTP or API error.
        """
        url = f"{self.GRAPH_BASE}/{self.page_id}/live_videos"
        payload = {
            "access_token": self.token,
            "title": title,
            "description": description,
            "status": status,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, data=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.exception("Facebook API returned error: %s", exc)
            raise FacebookAPIError(f"Facebook API error: {exc.response.text}") from exc
        except Exception as exc:
            logger.exception("Failed to call Facebook API: %s", exc)
            raise FacebookAPIError(f"Failed to call Facebook API: {exc}") from exc

        # Facebook may return stream_url or secure_stream_url; stream_key may be nested
        result = {
            "id": data.get("id"),
            "stream_url": data.get("stream_url") or data.get("secure_stream_url"),
            "stream_key": data.get("stream_key") or data.get("stream_url")  # fallback heuristic
        }
        logger.debug("Facebook create_live result: %s", result)
        return result

    def get_live_status(self, live_id: str) -> Dict[str, Any]:
        """Get basic status for a created live video.

        Args:
            live_id: Facebook live video id.

        Returns:
            Parsed JSON response.

        Raises:
            FacebookAPIError: On failure.
        """
        url = f"{self.GRAPH_BASE}/{live_id}"
        params = {"access_token": self.token, "fields": "id,status,stream_url,secure_stream_url"}
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.exception("Failed to fetch live status: %s", exc)
            raise FacebookAPIError(f"Failed to fetch live status: {exc}") from exc
