"""OBS control routes.

Provides endpoints to start/stop streaming, change scenes and query status.
All endpoints require an authenticated user.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.config import get_config
from app.services.obs import OBSService
from app.auth.jwt import get_current_active_user
from app.auth.schemas import User

router = APIRouter(tags=["obs"])


class ActionResponse(BaseModel):
    """Generic action response."""
    status: str
    detail: Optional[str] = None


class ScenePayload(BaseModel):
    """Payload to change scene."""
    scene_name: str


@router.post("/start", response_model=ActionResponse)
def start_stream(current_user: User = Depends(get_current_active_user)):
    """Start OBS streaming using configured OBS websocket.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        ActionResponse indicating status.
    """
    cfg = get_config()
    obs_cfg = cfg.get("obs", {})
    obs = OBSService(obs_cfg["host"], obs_cfg["port"], obs_cfg.get("password", ""))
    try:
        obs.connect()
        obs.start_stream()
    except Exception as exc:  # pragma: no cover - surface errors to caller
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        obs.disconnect()
    return ActionResponse(status="started")


@router.post("/stop", response_model=ActionResponse)
def stop_stream(current_user: User = Depends(get_current_active_user)):
    """Stop OBS streaming.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        ActionResponse indicating status.
    """
    cfg = get_config()
    obs_cfg = cfg.get("obs", {})
    obs = OBSService(obs_cfg["host"], obs_cfg["port"], obs_cfg.get("password", ""))
    try:
        obs.connect()
        obs.stop_stream()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        obs.disconnect()
    return ActionResponse(status="stopped")


@router.post("/scene", response_model=ActionResponse)
def set_scene(payload: ScenePayload, current_user: User = Depends(get_current_active_user)):
    """Set current OBS scene.

    Args:
        payload: ScenePayload with scene_name.
        current_user: Authenticated user (injected).

    Returns:
        ActionResponse indicating status.
    """
    cfg = get_config()
    obs_cfg = cfg.get("obs", {})
    obs = OBSService(obs_cfg["host"], obs_cfg["port"], obs_cfg.get("password", ""))
    try:
        obs.connect()
        obs.set_scene(payload.scene_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        obs.disconnect()
    return ActionResponse(status="scene_set", detail=payload.scene_name)


@router.get("/status", response_model=ActionResponse)
def obs_status(current_user: User = Depends(get_current_active_user)):
    """Return a minimal OBS connection status.

    Args:
        current_user: Authenticated user (injected).

    Returns:
        ActionResponse with status 'ok' or error detail.
    """
    cfg = get_config()
    obs_cfg = cfg.get("obs", {})
    obs = OBSService(obs_cfg["host"], obs_cfg["port"], obs_cfg.get("password", ""))
    try:
        obs.connect()
        # If connect succeeded, we consider OBS reachable
        return ActionResponse(status="ok")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"OBS unreachable: {exc}")
    finally:
        try:
            obs.disconnect()
        except Exception:
            pass
