"""OBS service wrapper using obs-websocket-py.

Thin, robust abstraction over the obs-websocket client. Provides safe connect/
disconnect semantics, context manager and defensive extraction of streaming
status to avoid runtime errors across different client/server versions.
"""

from typing import Optional, Dict, Any
import logging
from contextlib import contextmanager

try:
    from obswebsocket import obsws, requests, exceptions  # type: ignore
except Exception:  # pragma: no cover - allow module import even if obs libs missing
    obsws = None
    requests = None
    exceptions = None

logger = logging.getLogger(__name__)


class OBSConnectionError(RuntimeError):
    """Raised when OBS connection or operation fails."""


class OBSService:
    """Thin wrapper around obs-websocket client to encapsulate operations."""

    def __init__(self, host: str, port: int, password: Optional[str] = None) -> None:
        """Initialize OBSService.

        Args:
            host: OBS websocket host (IP or hostname).
            port: OBS websocket port (int or str convertible to int).
            password: Optional password for OBS websocket.
        """
        self._host = host
        try:
            self._port = int(port)
        except Exception:
            raise ValueError("port must be an integer or string representing an integer")
        self._password = password or ""
        self._client = None  # type: Optional[obsws]

    def connect(self) -> None:
        """Establish connection to OBS websocket.

        Safe to call multiple times; subsequent calls are no-ops if already connected.

        Raises:
            OBSConnectionError: If connection fails or obs-websocket client missing.
        """
        if obsws is None:
            raise OBSConnectionError("obs-websocket-py is not installed or could not be imported")

        if self._client is not None:
            # Already connected
            return

        try:
            self._client = obsws(self._host, self._port, self._password)
            self._client.connect()
            logger.debug("Connected to OBS at %s:%s", self._host, self._port)
        except Exception as exc:
            # Ensure client reference is cleared on failure
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
            try:
                self._client.disconnect()
            except Exception:
                # Some client versions raise on disconnect; log and continue
                logger.exception("Error while disconnecting from OBS client")
        finally:
            self._client = None
            logger.debug("OBS client cleared")

    @contextmanager
    def connection(self):
        """Context manager that ensures connect/disconnect around operations."""
        try:
            self.connect()
            yield self
        finally:
            try:
                self.disconnect()
            except Exception:
                logger.exception("Error during OBS disconnect in context manager")

    def _ensure_client(self):
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
        if requests is None:
            raise OBSConnectionError("obs-websocket requests not available")
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
        if requests is None:
            raise OBSConnectionError("obs-websocket requests not available")
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
        if requests is None:
            raise OBSConnectionError("obs-websocket requests not available")
        try:
            client.call(requests.StopStreaming())
            logger.debug("Stop streaming requested")
        except Exception as exc:
            logger.exception("Failed to stop streaming: %s", exc)
            raise OBSConnectionError(f"Failed to stop streaming: {exc}") from exc

    def get_stream_status(self) -> Dict[str, Any]:
        """Return a minimal streaming status dict.

        The function is defensive: it attempts multiple fallbacks to extract
        streaming/recording flags from the response object returned by the
        obs-websocket client.

        Returns:
            Dict with keys 'streaming' (bool), 'recording' (bool) and optional 'raw' data.

        Raises:
            OBSConnectionError: If operation fails.
        """
        client = self._ensure_client()
        if requests is None:
            raise OBSConnectionError("obs-websocket requests not available")
        try:
            resp = client.call(requests.GetStreamingStatus())
            # resp may be an object with methods or attributes depending on client version.
            streaming = False
            recording = False
            raw = None

            # Try common method names / attributes
            try:
                # Some versions expose methods like getStreaming()
                if hasattr(resp, "getStreaming"):
                    streaming = bool(resp.getStreaming())
                elif hasattr(resp, "streaming"):
                    streaming = bool(getattr(resp, "streaming"))
                elif isinstance(resp, dict) and "streaming" in resp:
                    streaming = bool(resp.get("streaming"))
            except Exception:
                logger.debug("Fallback while extracting streaming flag failed", exc_info=True)

            try:
                if hasattr(resp, "getRecording"):
                    recording = bool(resp.getRecording())
                elif hasattr(resp, "recording"):
                    recording = bool(getattr(resp, "recording"))
                elif isinstance(resp, dict) and "recording" in resp:
                    recording = bool(resp.get("recording"))
            except Exception:
                logger.debug("Fallback while extracting recording flag failed", exc_info=True)

            # Keep raw representation for debugging if possible
            try:
                # Some response objects implement to_json or similar
                if hasattr(resp, "get"):
                    # treat as mapping-like
                    raw = dict(resp)
                else:
                    raw = repr(resp)
            except Exception:
                raw = repr(resp)

            status = {"streaming": streaming, "recording": recording, "raw": raw}
            logger.debug("Streaming status: %s", status)
            return status
        except Exception as exc:
            logger.exception("Failed to get streaming status: %s", exc)
            raise OBSConnectionError(f"Failed to get streaming status: {exc}") from exc
