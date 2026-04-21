"""Streaming routes: gerar transmissões e registrar chaves.

Endpoints:
- POST /stream/generate : generate title/description and attempt to create FB live
- POST /stream/keys     : register (store) youtube/facebook keys securely
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.youtube import gerar_titulo_e_descricao
from app.services.facebook import FacebookService
from app.utils.secure_store import SecureStore
from app.config import get_config
from app.auth.jwt import get_current_active_user
from app.auth.schemas import User

router = APIRouter(tags=["streaming"])


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

    This endpoint returns generated title/description and attempts to create
    live entries via service clients. If API credentials are not configured,
    it returns None for the corresponding key and the frontend should allow
    manual paste.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        GenerateResponse with keys (may be None) and metadata.
    """
    cfg = get_config()
    title, description = gerar_titulo_e_descricao()
    youtube_key = None
    facebook_key = None

    # YouTube: placeholder - real implementation requires OAuth flow
    # youtube_key = youtube_service.create_live(...)

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
    """Register (store) stream keys securely.

    Args:
        payload: KeysPayload with optional youtube_key and facebook_key.
        current_user: Authenticated user (injected).

    Returns:
        dict: status message.
    """
    cfg = get_config()
    store_path = cfg.get("secrets_file", "keys.enc")
    store = SecureStore(store_path)
    if payload.youtube_key:
        store.set("youtube_key", payload.youtube_key)
    if payload.facebook_key:
        store.set("facebook_key", payload.facebook_key)
    return {"status": "saved"}
