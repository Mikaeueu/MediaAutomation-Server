"""YouTube OAuth2 helper and token manager.

Manages authorization URL generation, code exchange, token refresh and secure
storage of tokens. Uses google-auth libraries when available; otherwise raises
a clear error. Tokens are persisted encrypted via SecureStore.
"""

from typing import Dict, Optional
from pathlib import Path
import time
import logging

from app.utils.secure_store import SecureStore
from app.config import get_config

try:
    from google_auth_oauthlib.flow import Flow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except Exception:
    Flow = None
    Credentials = None
    Request = None

logger = logging.getLogger(__name__)

_YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


class YouTubeOAuthError(RuntimeError):
    """Raised when OAuth operations fail."""


class YouTubeOAuthService:
    """Manage OAuth2 flow and tokens for YouTube API."""

    def __init__(self, client_secrets_path: str, store_path: Optional[str] = None) -> None:
        """Initialize the OAuth service.

        Args:
            client_secrets_path: Path to client_secrets.json.
            store_path: Optional path to encrypted token store.
        """
        self.client_secrets_path = str(Path(client_secrets_path).expanduser())
        cfg = get_config()
        self.store_path = store_path or cfg.get("secrets_file", "keys.enc")
        self._store = SecureStore(self.store_path)
        self._credentials: Optional["Credentials"] = None

        if Flow is None:
            logger.warning("google-auth libraries not available; OAuth endpoints will not function")

    def _store_tokens(self, token_data: Dict) -> None:
        """Persist token dict in secure store."""
        self._store.set("youtube_tokens", token_data)

    def _load_tokens(self) -> Optional[Dict]:
        """Load token dict from secure store."""
        return self._store.get("youtube_tokens")

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """Return an authorization URL to redirect the user to Google consent screen."""
        if Flow is None:
            raise YouTubeOAuthError("google-auth libraries are not installed")

        if not Path(self.client_secrets_path).exists():
            raise YouTubeOAuthError(f"client_secrets.json not found at {self.client_secrets_path}")

        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=_YOUTUBE_SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, resp_state = flow.authorization_url(access_type="offline", include_granted_scopes="true", state=state)
        return auth_url

    def exchange_code(self, code: str, redirect_uri: str) -> Dict:
        """Exchange authorization code for tokens and persist them."""
        if Flow is None:
            raise YouTubeOAuthError("google-auth libraries are not installed")

        flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=_YOUTUBE_SCOPES,
            redirect_uri=redirect_uri,
        )
        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            expiry_ts = None
            if getattr(creds, "expiry", None):
                expiry_ts = int(getattr(creds, "expiry").timestamp())
            token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if getattr(creds, "scopes", None) else None,
                "expiry": expiry_ts,
            }
            self._store_tokens(token_data)
            self._credentials = creds
            return token_data
        except Exception as exc:
            logger.exception("Failed to exchange code: %s", exc)
            raise YouTubeOAuthError(f"Failed to exchange code: {exc}") from exc

    def get_credentials(self) -> Optional["Credentials"]:
        """Return a Credentials object if tokens are available, refreshing if needed."""
        if Credentials is None:
            return None

        if self._credentials:
            return self._credentials

        token_data = self._load_tokens()
        if not token_data:
            return None

        try:
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )
            if getattr(creds, "expired", False) and creds.refresh_token:
                request = Request()
                creds.refresh(request)
                expiry_ts = None
                if getattr(creds, "expiry", None):
                    expiry_ts = int(getattr(creds, "expiry").timestamp())
                refreshed = {
                    "token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_uri": creds.token_uri,
                    "client_id": creds.client_id,
                    "client_secret": creds.client_secret,
                    "scopes": list(creds.scopes) if getattr(creds, "scopes", None) else None,
                    "expiry": expiry_ts,
                }
                self._store_tokens(refreshed)
            self._credentials = creds
            return creds
        except Exception as exc:
            logger.exception("Failed to build/refresh credentials: %s", exc)
            return None

    def revoke(self) -> None:
        """Revoke stored tokens and remove them from store."""
        token_data = self._load_tokens()
        if not token_data:
            return
        token = token_data.get("token")
        if token:
            try:
                import httpx
                httpx.post("https://oauth2.googleapis.com/revoke", data={"token": token}, timeout=5.0)
            except Exception:
                logger.debug("Failed to call revoke endpoint; continuing to delete local tokens")
        self._store.delete("youtube_tokens")
        self._credentials = None
