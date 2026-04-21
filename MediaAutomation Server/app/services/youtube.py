"""YouTube service helpers.

This module provides utilities to generate titles/descriptions and a
skeleton YouTubeService class. Creating live broadcasts via YouTube API
requires OAuth2 credentials and the google-api-python-client; here we keep
a testable, explicit interface and a safe fallback for manual stream keys.
"""

from datetime import datetime
from typing import Tuple, Optional, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

_STREAM_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{8,}$")


def gerar_titulo_por_dia_semana(dia_semana: int) -> str:
    """Generate a default title based on weekday.

    Args:
        dia_semana: Weekday as integer where Monday is 0.

    Returns:
        Suggested title string.
    """
    mapping = {
        0: "Culto Segunda",
        1: "Culto Terça",
        2: "Culto Quarta",
        3: "Culto Quinta",
        4: "Culto Sexta",
        5: "Culto Sábado",
        6: "Culto Domingo",
    }
    return mapping.get(dia_semana, "Live")


def gerar_titulo_e_descricao() -> Tuple[str, str]:
    """Return a generated title and description based on current date.

    Returns:
        Tuple of (title, description).
    """
    hoje = datetime.utcnow()
    title = gerar_titulo_por_dia_semana(hoje.weekday())
    description = f"Transmissão automática gerada para {hoje.date().isoformat()}"
    logger.debug("Generated title=%s description=%s", title, description)
    return title, description


class YouTubeService:
    """Skeleton YouTube service.

    Real implementation requires OAuth2 flow and google-api-python-client.
    This class defines the interface and provides helpers for local flows.
    """

    def __init__(self, credentials: Optional[Dict[str, Any]] = None) -> None:
        """Initialize YouTubeService.

        Args:
            credentials: Optional dict with OAuth2 credentials or tokens.
        """
        self._credentials = credentials

    def create_live_broadcast(self, title: str, description: str) -> Dict[str, Optional[str]]:
        """Create a live broadcast and return stream key info.

        This is a placeholder. In production implement OAuth2 flow and call
        YouTube Data API (liveBroadcasts.insert + liveStreams.insert).

        Returns:
            Dict with keys 'broadcast_id', 'stream_id', 'stream_key' or raises.
        """
        # Placeholder behavior: raise to indicate not implemented
        logger.debug("create_live_broadcast called with title=%s", title)
        raise NotImplementedError(
            "YouTube live creation is not implemented. Implement OAuth2 flow and "
            "use google-api-python-client to create liveBroadcasts and liveStreams."
        )

    @staticmethod
    def validate_stream_key(key: str) -> bool:
        """Validate a stream key format (basic heuristic).

        Args:
            key: Stream key string.

        Returns:
            True if key looks valid, False otherwise.
        """
        return bool(_STREAM_KEY_RE.match(key))
