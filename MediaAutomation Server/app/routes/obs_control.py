"""OBS control routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.config import get_config
from app.services.obs import OBSService

router = APIRouter()


class StartStreamResponse(BaseModel):
    """Response for start stream action."""
    status: str


@router.post("/start", response_model=StartStreamResponse)
def start_stream():
    """Start OBS streaming using configured OBS websocket.

    Returns:
        StartStreamResponse indicating status.
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
    return StartStreamResponse(status="started")


@router.post("/stop", response_model=StartStreamResponse)
def stop_stream():
    """Stop OBS streaming."""
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
    return StartStreamResponse(status="stopped")
