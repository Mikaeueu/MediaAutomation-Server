import json
import unicodedata

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.holyrics_store import load_config, save_config
from app.schemas.holyrics_config import (
    DefaultResponse,
    HolyricsConfigResponse,
    HolyricsConfigUpdate,
    SetVerseRequest,
)
from app.services.holyrics_service import HolyricsService

# ============================================================
# 📖 Bíblia metadata
# ============================================================

with open("app/data/bible_meta.json", "r", encoding="utf-8") as f:
    BIBLE_META = json.load(f)

# ============================================================
# 🕘 Histórico em memória
# ============================================================

# Lista de dicts: {version, book, chapter, verse, label}
RECENT: list[dict] = []
_RECENT_MAX = 20

# ============================================================
# 🧠 Helpers
# ============================================================


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()


def find_book_meta(book_input: str):
    normalized_input = normalize_text(book_input)
    for b in BIBLE_META:
        if (
            normalized_input == normalize_text(b.get("abbr", ""))
            or normalized_input == normalize_text(b.get("book", ""))
        ):
            return b
    return None


def _add_recent(version: str, book: str, chapter: int, verse: int) -> None:
    """Insere no topo do histórico e mantém o limite."""
    label = f"{book} {chapter}:{verse} ({version})"
    entry = {
        "version": version,
        "book": book,
        "chapter": chapter,
        "verse": verse,
        "label": label,
    }
    RECENT.append(entry)
    # Mantém só os últimos _RECENT_MAX itens
    if len(RECENT) > _RECENT_MAX:
        del RECENT[: len(RECENT) - _RECENT_MAX]


# ============================================================
# 🚀 Router
# ============================================================

router = APIRouter(
    prefix="/api/holyrics",
    tags=["holyrics"],
    dependencies=[Depends(get_current_user)],
)

# ============================================================
# ⚙️ CONFIG
# ============================================================


@router.get("/config", response_model=HolyricsConfigResponse)
def read_config():
    cfg = load_config()
    if not cfg:
        return {
            "ok": True,
            "data": {
                "host": "localhost",
                "port": 8091,
                "token": "",
                "is_configured": False,
            },
        }
    return {
        "ok": True,
        "data": {
            "host": cfg["host"],
            "port": cfg["port"],
            "token": cfg.get("token", ""),
            "is_configured": bool(cfg.get("token")),
        },
    }


@router.put("/config", response_model=HolyricsConfigResponse)
def update_config(payload: HolyricsConfigUpdate):
    save_config(payload.dict())
    return {
        "ok": True,
        "message": "Configuração salva com sucesso",
        "data": {
            "host": payload.host,
            "port": payload.port,
            "token": payload.token,
            "is_configured": bool(payload.token),
        },
    }


# ============================================================
# 🔌 TESTE
# ============================================================


@router.post("/test", response_model=DefaultResponse)
async def test_connection(payload: HolyricsConfigUpdate):
    return await HolyricsService.test_connection(
        host=payload.host,
        port=payload.port,
        token=payload.token,
    )


# ============================================================
# 📡 STATUS
# ============================================================


@router.get("/status", response_model=DefaultResponse)
async def status():
    try:
        service = HolyricsService()
        return await service.get_status()
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ============================================================
# 📖 META / VERSÕES
# ============================================================


@router.get("/meta", response_model=DefaultResponse)
def get_bible_meta():
    return {"ok": True, "data": BIBLE_META}


@router.get("/versions", response_model=DefaultResponse)
async def list_versions():
    try:
        service = HolyricsService()
        versions = await service.get_versions()
        return {"ok": True, "data": {"versions": versions}}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ============================================================
# 📜 VERSÍCULO
# ============================================================


@router.post("/verse", response_model=DefaultResponse)
async def show_verse(payload: SetVerseRequest):
    try:
        service = HolyricsService()

        # Valida livro
        book_meta = find_book_meta(payload.book)
        if not book_meta:
            return {"ok": False, "message": f"Livro '{payload.book}' não encontrado."}

        # Valida capítulo
        chapter_meta = next(
            (c for c in book_meta["chapters"]
             if str(c["chapter"]) == str(payload.chapter)),
            None,
        )
        if not chapter_meta:
            return {"ok": False, "message": f"Capítulo {payload.chapter} inválido."}

        max_verse = int(chapter_meta["verses"])
        if payload.verse < 1 or payload.verse > max_verse:
            return {
                "ok": False,
                "message": (
                    f"{payload.book} {payload.chapter} tem {max_verse} versículo(s). "
                    f"Versículo {payload.verse} não existe."
                ),
            }

        reference = f"{payload.book} {payload.chapter}:{payload.verse}"
        version = payload.version.upper().strip()

        # Envia pro Holyrics
        await service.show_verse(reference, version)

        # ✅ Salva no histórico (era o bug: isso faltava antes)
        _add_recent(version, payload.book, payload.chapter, payload.verse)

        return {
            "ok": True,
            "message": "Versículo exibido",
            "data": {"reference": reference, "version": version},
        }

    except Exception as e:
        return {"ok": False, "message": str(e)}


# ============================================================
# ❌ FECHAR
# ============================================================


@router.post("/close", response_model=DefaultResponse)
async def close_verse():
    try:
        service = HolyricsService()
        await service.close()
        return {"ok": True, "message": "Projeção fechada"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


# ============================================================
# 🕘 HISTÓRICO
# ============================================================


@router.get("/recent", response_model=DefaultResponse)
def list_recent():
    # Retorna os últimos 10 em ordem decrescente (mais recente primeiro)
    # data é uma lista direta — o frontend lê json.data (não json.data.items)
    return {
        "ok": True,
        "data": list(reversed(RECENT[-10:])),
    }


@router.delete("/recent", response_model=DefaultResponse)
def clear_recent():
    RECENT.clear()
    return {"ok": True, "message": "Histórico limpo"}
