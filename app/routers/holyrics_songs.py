"""Endpoints de musicas/letras do Holyrics via API HTTP oficial.

Pivotamos pra API HTTP em vez de ler do disco — o Holyrics nao expoe
o banco em formato relacional, e a API ja temos token configurado.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.dependencies import get_current_user
from app.services import holyrics_songs_service as svc
from app.services.holyrics_service import HolyricsConnectionError, HolyricsError

router = APIRouter(
    prefix="/api/holyrics/songs",
    tags=["holyrics-songs"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/status")
async def status():
    """Ping rapido da API do Holyrics."""
    return {"ok": True, "data": await svc.get_status()}


@router.get("/search")
async def search(q: str = "", limit: int = 50):
    """Busca musicas por nome.

    Query vazia retorna a lista completa (limitada por ``limit``).
    """
    try:
        results = await svc.search_songs(q, limit=limit)
        return {"ok": True, "data": results}
    except HolyricsConnectionError as exc:
        return {"ok": False, "message": str(exc), "data": []}
    except HolyricsError as exc:
        return {"ok": False, "message": str(exc), "data": []}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": f"{type(exc).__name__}: {exc}", "data": []}


@router.post("/{song_id}/show-slide/{slide_index}")
async def show_slide(song_id: str, slide_index: int):
    """Projeta um slide especifico de uma musica (via initial_index)."""
    sid: int | str
    try:
        sid = int(song_id)
    except ValueError:
        sid = song_id
    try:
        return {"ok": True, "data": await svc.show_slide(sid, slide_index)}
    except HolyricsConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except HolyricsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@router.post("/close")
async def close():
    """Fecha a projecao atual."""
    try:
        return {"ok": True, "data": await svc.close_presentation()}
    except HolyricsConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except HolyricsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@router.post("/{song_id}/show")
async def show(song_id: str):
    """Projeta o hino no Holyrics."""
    sid: int | str
    try:
        sid = int(song_id)
    except ValueError:
        sid = song_id
    try:
        return {"ok": True, "data": await svc.show_song(sid)}
    except HolyricsConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except HolyricsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")


@router.get("/{song_id}/slides")
async def slides(song_id: str):
    """Retorna a musica completa quebrada em slides."""
    sid: int | str
    try:
        sid = int(song_id)
    except ValueError:
        sid = song_id
    try:
        return {"ok": True, "data": await svc.get_song_slides(sid)}
    except HolyricsConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except HolyricsError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")
