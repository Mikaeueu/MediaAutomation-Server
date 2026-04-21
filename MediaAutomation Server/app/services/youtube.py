"""YouTube service facade that integrates with YouTubeOAuthService.

This module exposes YouTubeService which manages credentials via the OAuth
service. The actual API calls to create live broadcasts are left as
NotImplemented and should be implemented using google-api-python-client.
"""

from typing import Dict, Optional, Any
import logging

from app.config import get_config

try:
    from .youtube_oauth import YouTubeOAuthService, YouTubeOAuthError
except Exception:
    YouTubeOAuthService = None
    YouTubeOAuthError = Exception

logger = logging.getLogger(__name__)


def gerar_titulo_por_dia_semana(dia_semana: int) -> str:
    """Generate a default title based on weekday (Monday=0)."""
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


def gerar_titulo_e_descricao() -> (str, str):
    """Return a generated title and description based on current date."""
    from datetime import datetime
    hoje = datetime.utcnow()
    title = gerar_titulo_por_dia_semana(hoje.weekday())
    description = f"Transmissão automática gerada para {hoje.date().isoformat()}"
    logger.debug("Generated title=%s description=%s", title, description)
    return title, description


class YouTubeService:
    """Facade for YouTube operations that require OAuth credentials."""

    def __init__(self, oauth_client_secrets: Optional[str] = None, store_path: Optional[str] = None) -> None:
        """Initialize YouTubeService.

        Args:
            oauth_client_secrets: Path to client_secrets.json (optional).
            store_path: Optional path to encrypted token store.
        """
        self._oauth = None
        if oauth_client_secrets and YouTubeOAuthService is not None:
            self._oauth = YouTubeOAuthService(oauth_client_secrets, store_path=store_path)

    def has_credentials(self) -> bool:
        """Return True if OAuth credentials are available."""
        if not self._oauth:
            return False
        return self._oauth.get_credentials() is not None

    def create_live_broadcast(self, title: str, description: str) -> Dict[str, Optional[str]]:
        """Create a live broadcast and return stream key info.

        Raises:
            YouTubeOAuthError if OAuth not configured or credentials missing.
            NotImplementedError for the actual API call (to be implemented).
        """
        if not self._oauth:
            raise YouTubeOAuthError("OAuth client not configured for YouTubeService")

        creds = self._oauth.get_credentials()
        if not creds:
            raise YouTubeOAuthError("No valid credentials available; perform OAuth flow")

        # Real implementation would use googleapiclient.discovery.build:
        # youtube = build("youtube", "v3", credentials=creds)
        # create liveBroadcast and liveStream, bind them and return stream key.
        logger.debug("create_live_broadcast called; credentials available but API call not implemented")
        raise NotImplementedError("YouTube live creation not implemented. Implement google-api calls here.")
