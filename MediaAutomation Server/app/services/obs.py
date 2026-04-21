"""OBS service wrapper using obs-websocket-py.

Provides a thin, testable abstraction over the obs-websocket client.
Designed to be used by routes or background tasks without leaking
implementation details.
"""

from typing import Optional, Dict, Any
import logging
from contextlib import contextmanager

from obswebsocket import obsws, requests, exceptions

logger = logging.getLogger(__name__)


class OBSConnectionError(RuntimeError):
    """Raised when OBS connection or operation fails."""


class OBSService:
    """Thin wrapper around obs-websocket client to encapsulate operations.

    Usage:
        cfg = get_config()["obs"]
        obs = OBSService(cfg["host"], cfg["port"], cfg.get("password"))
        obs.connect()
        obs.start_stream()
        obs.disconnect()
    """

    def __init__(self, host: str, port: int, password: Optional[str] = None) -> None:
        """Initialize OBSService.

        Args:
            host: OBS websocket host (IP or hostname).
            port: OBS websocket port (int).
            password: Optional password for OBS websocket.
        """
        self._host = host
        self._port = int(port)
        self._password = password or ""
        self._client: Optional[obsws] = None

    def connect(self, timeout: float = 5.0) -> None:
        """Establish connection to OBS websocket.

        Args:
            timeout: Not used by obsws but kept for API compatibility.

        Raises:
            OBSConnectionError: If connection fails.
        """
        if self._client is not None:
            # Already connected
            return
        try:
            self._client = obsws(self._host, self._port, self._password)
            self._client.connect()
            logger.debug("Connected to OBS at %s:%s", self._host, self._port)
        except Exception as exc:
            self._client = None
            logger.exception("Failed to connect to OBS: %s", exc)
            raise OBSConnectionError(f"Failed to connect to OBS: {exc}") from exc

    def disconnect(self) -> None:
        """Disconnect from OBS websocket.

        Safe to call even if not connected.
        """
        if not self._client:
            return
        try:
            self._client.disconnect()
            logger.debug("Disconnected from OBS")
        except Exception:
            logger.exception("Error while disconnecting from OBS")
        finally:
            self._client = None

    @contextmanager
    def connection(self):
        """Context manager that ensures connect/disconnect around operations."""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()

    def _ensure_client(self) -> obsws:
        """Return connected client or raise.

        Raises:
            OBSConnectionError: If not connected.
        """
        if not self._client:
            raise OBSConnectionError("OBS client is not connected")
        return self._client

    def set_scene(self, scene_name: str) -> None:
        """Set current scene in OBS.

        Args:
            scene_name: Name of the scene to switch to.

        Raises:
            OBSConnectionError: If operation fails.
        """
        client = self._ensure_client()
        try:
            client.call(requests.SetCurrentScene(scene_name))
            logger.debug("Scene set to %s", scene_name)
        except Exception as exc:
            logger.exception("Failed to set scene: %s", exc)
            raise OBSConnectionError(f"Failed to set scene: {exc}") from exc

    def start_stream(self) -> None:
        """Start streaming in OBS.

        Raises:
            OBSConnectionError: If operation fails.
        """
        client = self._ensure_client()
        try:
            client.call(requests.StartStreaming())
            logger.debug("Start streaming requested")
        except Exception as exc:
            logger.exception("Failed to start streaming: %s", exc)
            raise OBSConnectionError(f"Failed to start streaming: {exc}") from exc

    def stop_stream(self) -> None:
        """Stop streaming in OBS.

        Raises:
            OBSConnectionError: If operation fails.
        """
        client = self._ensure_client()
        try:
            client.call(requests.StopStreaming())
            logger.debug("Stop streaming requested")
        except Exception as exc:
            logger.exception("Failed to stop streaming: %s", exc)
            raise OBSConnectionError(f"Failed to stop streaming: {exc}") from exc

    def get_stream_status(self) -> Dict[str, Any]:
        """Return a minimal streaming status dict.

        Returns:
            Dict with keys like 'streaming' (bool) and 'status' (str).

        Raises:
            OBSConnectionError: If operation fails.
        """
        client = self._ensure_client()
        try:
            resp = client.call(requests.GetStreamingStatus())
            status = {
                "streaming": getattr(resp, "getStreaming", False),
                "recording": getattr(resp, "getRecording", False),
            }
            logger.debug("Streaming status: %s", status)
            return status
        except Exception as exc:
            logger.exception("Failed to get streaming status: %s", exc)
            raise OBSConnectionError(f"Failed to get streaming status: {exc}") from exc
