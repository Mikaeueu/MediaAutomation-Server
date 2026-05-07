import json
import unicodedata

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.holyrics_store import load_config, save_config
from app.schemas.holyrics_config import (
    DefaultResponse,
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


@router.get("/config", response_model=DefaultResponse)
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
            "is_configured": True,
        },
    }


@router.put("/config", response_model=DefaultResponse)
def update_config(payload: HolyricsConfigUpdate):
    save_config(payload.dict())

    return {
        "ok": True,
        "message": "Configuração salva com sucesso",
        "data": {
            "host": payload.host,
            "port": payload.port,
            "token": payload.token,
            "is_configured": True,
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
        result = await service.get_status()

        return result

    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
        }


# ============================================================
# 📖 META / VERSÕES
# ============================================================


@router.get("/meta", response_model=DefaultResponse)
def get_bible_meta():
    return {
        "ok": True,
        "data": BIBLE_META,
    }


@router.get("/versions", response_model=DefaultResponse)
async def list_versions():
    try:
        service = HolyricsService()
        versions = await service.get_versions()

        return {
            "ok": True,
            "data": versions,
        }

    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
        }


# ============================================================
# 📜 VERSÍCULO
# ============================================================


@router.post("/verse", response_model=DefaultResponse)
async def show_verse(payload: SetVerseRequest):
    try:
        service = HolyricsService()

        # ==============================
        # 📚 Validação livro
        # ==============================
        book_meta = find_book_meta(payload.book)

        if not book_meta:
            return {"ok": False, "message": "Livro inválido."}

        # ==============================
        # 📖 Capítulo
        # ==============================
        chapter_meta = next(
            (c for c in book_meta["chapters"]
             if str(c["chapter"]) == str(payload.chapter)),
            None,
        )

        if not chapter_meta:
            return {"ok": False, "message": "Capítulo inválido."}

        max_verse = int(chapter_meta["verses"])

        # ==============================
        # 🔢 Versículo
        # ==============================
        if payload.verse < 1 or payload.verse > max_verse:
            return {
                "ok": False,
                "message": f"{payload.book} {payload.chapter} tem {max_verse} versículos.",
            }

        reference = f"{payload.book} {payload.chapter}:{payload.verse}"
        version = payload.version.upper().strip()

        # ==============================
        # 🚀 Enviar pro Holyrics
        # ==============================
        await service.show_verse(reference, version)

        return {
            "ok": True,
            "message": "Versículo exibido",
            "data": {
                "reference": reference,
                "version": version,
            },
        }

    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
        }


# ============================================================
# ❌ FECHAR
# ============================================================


@router.post("/close", response_model=DefaultResponse)
async def close_verse():
    try:
        service = HolyricsService()
        await service.close()

        return {
            "ok": True,
            "message": "Projeção fechada",
        }

    except Exception as e:
        return {
            "ok": False,
            "message": str(e),
        }


# ============================================================
# 🕘 HISTÓRICO (SIMPLES EM MEMÓRIA)
# ============================================================

RECENT = []


@router.get("/recent", response_model=DefaultResponse)
def list_recent():
    return {
        "ok": True,
        "data": RECENT[-10:][::-1],
    }


@router.delete("/recent", response_model=DefaultResponse)
def clear_recent():
    RECENT.clear()

    return {
        "ok": True,
        "message": "Histórico limpo",
    }