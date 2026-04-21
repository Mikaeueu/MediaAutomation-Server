"""Streaming routes including YouTube OAuth endpoints.

Endpoints:
- POST /stream/generate        : generate title/description and attempt FB live creation
- POST /stream/keys            : register (store) youtube/facebook keys securely
- GET  /stream/youtube/auth    : return authorization URL for YouTube OAuth
- GET  /stream/youtube/callback: callback to exchange code for tokens
- POST /stream/youtube/revoke  : revoke stored YouTube tokens
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from app.services.youtube import gerar_titulo_e_descricao, YouTubeService
from app.services.facebook import FacebookService
from app.utils.secure_store import SecureStore
from app.config import get_config
from app.auth.jwt import get_current_active_user
from app.auth.schemas import User

router = APIRouter()


class GenerateResponse(BaseModel):
    """Response when generation attempted."""
    youtube_key: Optional[str]
    facebook_key: Optional[str]
    title: str
    description: str


class KeysPayload(BaseModel):
    """Payload to register keys manually."""
    youtube_key: Optional[str] = None
    facebook_key: Optional[str] = None


@router.post("/generate", response_model=GenerateResponse)
def generate_stream(current_user: User = Depends(get_current_active_user)):
    """Attempt to generate live streams for YouTube and Facebook.

    Returns generated title/description and attempts to create FB live if configured.
    """
    cfg = get_config()
    title, description = gerar_titulo_e_descricao()
    youtube_key = None
    facebook_key = None

    # YouTube: if OAuth configured and credentials available, attempt creation
    yt_cfg = cfg.get("youtube", {})
    if yt_cfg.get("client_secrets_path"):
        yt_service = YouTubeService(oauth_client_secrets=yt_cfg.get("client_secrets_path"),
                                    store_path=cfg.get("secrets_file"))
        try:
            if yt_service.has_credentials():
                # create_live_broadcast not implemented; placeholder for future
                pass
        except Exception:
            # Do not fail the whole endpoint if YouTube creation fails
            pass

    # Facebook: try to create live if page access token configured
    fb_cfg = cfg.get("facebook", {})
    if fb_cfg.get("page_access_token") and fb_cfg.get("page_id"):
        fb = FacebookService(fb_cfg["page_access_token"], fb_cfg["page_id"])
        try:
            fb_result = fb.create_live(title=title, description=description)
            facebook_key = fb_result.get("stream_key")
        except Exception:
            facebook_key = None

    return GenerateResponse(
        youtube_key=youtube_key,
        facebook_key=facebook_key,
        title=title,
        description=description,
    )


@router.post("/keys")
def register_keys(payload: KeysPayload, current_user: User = Depends(get_current_active_user)):
    """Register (store) stream keys securely."""
    cfg = get_config()
    store_path = cfg.get("secrets_file", "keys.enc")
    store = SecureStore(store_path)
    if payload.youtube_key:
        store.set("youtube_key", payload.youtube_key)
    if payload.facebook_key:
        store.set("facebook_key", payload.facebook_key)
    return {"status": "saved"}


# ---------------------------
# YouTube OAuth endpoints
# ---------------------------

@router.get("/youtube/auth")
def youtube_auth(redirect_uri: str = Query(..., description="Redirect URI registered in Google Cloud Console"),
                 state: Optional[str] = None,
                 current_user: User = Depends(get_current_active_user)):
    """Return an authorization URL for the YouTube OAuth flow.

    Args:
        redirect_uri: Redirect URI that must match the one registered in Google Cloud Console.
        state: Optional state for CSRF protection.
    """
    cfg = get_config()
    yt_cfg = cfg.get("youtube", {})
    client_secrets = yt_cfg.get("client_secrets_path")
    if not client_secrets:
        raise HTTPException(status_code=400, detail="YouTube client_secrets not configured")
    # Lazy import to avoid hard dependency if google libs are missing
    from app.services.youtube_oauth import YouTubeOAuthService, YouTubeOAuthError
    oauth = YouTubeOAuthService(client_secrets_path=client_secrets, store_path=cfg.get("secrets_file"))
    try:
        url = oauth.get_authorization_url(redirect_uri=redirect_uri, state=state)
        return {"authorization_url": url}
    except YouTubeOAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/youtube/callback")
def youtube_callback(code: str = Query(...), redirect_uri: str = Query(...), state: Optional[str] = None,
                     current_user: User = Depends(get_current_active_user)):
    """Callback endpoint to exchange authorization code for tokens.

    Args:
        code: Authorization code returned by Google.
        redirect_uri: Redirect URI used in the flow.
        state: Optional state value.
    """
    cfg = get_config()
    yt_cfg = cfg.get("youtube", {})
    client_secrets = yt_cfg.get("client_secrets_path")
    if not client_secrets:
        raise HTTPException(status_code=400, detail="YouTube client_secrets not configured")
    from app.services.youtube_oauth import YouTubeOAuthService, YouTubeOAuthError
    oauth = YouTubeOAuthService(client_secrets_path=client_secrets, store_path=cfg.get("secrets_file"))
    try:
        token_data = oauth.exchange_code(code=code, redirect_uri=redirect_uri)
        return {"status": "ok", "token_data": {"has_refresh": bool(token_data.get("refresh_token"))}}
    except YouTubeOAuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/youtube/revoke")
def youtube_revoke(current_user: User = Depends(get_current_active_user)):
    """Revoke stored YouTube tokens and remove them from secure store."""
    cfg = get_config()
    yt_cfg = cfg.get("youtube", {})
    client_secrets = yt_cfg.get("client_secrets_path")
    if not client_secrets:
        raise HTTPException(status_code=400, detail="YouTube client_secrets not configured")
    from app.services.youtube_oauth import YouTubeOAuthService
    oauth = YouTubeOAuthService(client_secrets_path=client_secrets, store_path=cfg.get("secrets_file"))
    oauth.revoke()
    return {"status": "revoked"}
