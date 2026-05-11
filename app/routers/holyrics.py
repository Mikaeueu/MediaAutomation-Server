import json
import unicodedata
import time

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
_DEBUG_LOG_PATH = "debug-470fcb.log"


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    try:
        payload = {
            "sessionId": "470fcb",
            "runId": "initial",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception:
        pass

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
    # #region agent log
    _debug_log(
        "H2",
        "app/routers/holyrics.py:read_config",
        "router read config",
        {
            "hasCfg": bool(cfg),
            "host": (cfg or {}).get("host"),
            "port": (cfg or {}).get("port"),
            "tokenLen": len((cfg or {}).get("token", "")),
        },
    )
    # #endregion
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
    # #region agent log
    _debug_log(
        "H2",
        "app/routers/holyrics.py:update_config",
        "router update config payload",
        {
            "host": payload.host,
            "port": payload.port,
            "tokenLen": len(payload.token or ""),
        },
    )
    # #endregion
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
        result = await service.get_status()
        # #region agent log
        _debug_log(
            "H5",
            "app/routers/holyrics.py:status",
            "router status response",
            {
                "ok": bool(result.get("ok")),
                "topKeys": list(result.keys()),
                "dataKeys": list((result.get("data") or {}).keys())
                if isinstance(result.get("data"), dict)
                else [],
                "nestedStatus": ((result.get("data") or {}).get("status"))
                if isinstance(result.get("data"), dict)
                else None,
            },
        )
        # #endregion
        return result
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
        # #region agent log
        _debug_log(
            "H6",
            "app/routers/holyrics.py:show_verse",
            "router show_verse payload received",
            {
                "version": payload.version,
                "book": payload.book,
                "chapter": payload.chapter,
                "verse": payload.verse,
            },
        )
        # #endregion
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
        version = (payload.version or "").strip()
        book_number = str(BIBLE_META.index(book_meta) + 1).zfill(2)
        chapter_number = str(int(payload.chapter)).zfill(3)
        verse_number = str(int(payload.verse)).zfill(3)
        verse_id = f"{book_number}{chapter_number}{verse_number}"
        # #region agent log
        _debug_log(
            "H6",
            "app/routers/holyrics.py:show_verse",
            "router show_verse normalized reference",
            {
                "reference": reference,
                "version": version,
                "verseId": verse_id,
            },
        )
        # #endregion

        # Envia pro Holyrics
        await service.show_verse(reference, version, verse_id)

        # ✅ Salva no histórico (era o bug: isso faltava antes)
        _add_recent(version, payload.book, payload.chapter, payload.verse)

        return {
            "ok": True,
            "message": "Versículo exibido",
            "data": {"reference": reference, "version": version},
        }

    except Exception as e:
        # #region agent log
        _debug_log(
            "H6",
            "app/routers/holyrics.py:show_verse",
            "router show_verse exception",
            {"error": str(e)},
        )
        # #endregion
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


@router.post("/action/next", response_model=DefaultResponse)
async def action_next():
    """Avanca pro proximo slide (comando leve, nao reprojeta nada)."""
    try:
        service = HolyricsService()
        await service.action_next()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.post("/action/previous", response_model=DefaultResponse)
async def action_previous():
    """Volta pro slide anterior (comando leve, nao reprojeta nada)."""
    try:
        service = HolyricsService()
        await service.action_previous()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.post("/action/goto", response_model=DefaultResponse)
async def action_goto(index: int):
    """Pula pra slide especifico por indice (comando leve)."""
    try:
        service = HolyricsService()
        await service.action_go_to_index(index)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.get("/chapter", response_model=DefaultResponse)
async def get_chapter(version: str, book: str, chapter: int):
    """Lista versiculos de um capitulo (texto se a API retornar).

    Sempre retorna a estrutura completa baseado em BIBLE_META, mesmo
    que a API nao devolva texto — preenche com strings vazias e a UI
    mostra so o numero.
    """
    book_meta = find_book_meta(book)
    if not book_meta:
        return {"ok": False, "message": f"Livro '{book}' nao encontrado."}
    chapter_meta = next(
        (c for c in book_meta["chapters"] if str(c["chapter"]) == str(chapter)),
        None,
    )
    if not chapter_meta:
        return {"ok": False, "message": f"Capitulo {chapter} invalido."}
    max_verse = int(chapter_meta["verses"])

    # Tenta buscar texto via API. Se falhar, retorna so numeros.
    try:
        service = HolyricsService()
        api_verses = await service.get_chapter_verses(version, book, int(chapter))
    except Exception:
        api_verses = []

    text_by_verse = {v["verse"]: v["text"] for v in api_verses}
    verses = [
        {"verse": n, "text": text_by_verse.get(n, "")}
        for n in range(1, max_verse + 1)
    ]
    return {
        "ok": True,
        "data": {"book": book, "chapter": int(chapter), "verses": verses},
    }


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
