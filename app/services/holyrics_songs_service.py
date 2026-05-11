"""Servico de musicas/letras do Holyrics via API HTTP oficial.

PIVOT v0.7.5: antes ele tentava ler o banco SQLite direto do disco
(``C:\\Holyrics\\Holyrics\\files``), mas o Holyrics usa formato
proprietario binario (``Music.dat``, etc.) — nao SQLite. Pivotamos pra
API HTTP oficial, que ja temos token configurado e funcionando pra
Biblia.

Endpoints usados (todos POST pra ``/api/<acao>?token=<TOKEN>``):
  * ``GetSongs``        — lista resumida de todas as musicas;
  * ``SearchSong``      — busca por nome (fallback: filtra local);
  * ``GetSong``         — detalhe completo de uma musica (id, titulo,
                          autor, slides[]);
  * ``GetSongInformation`` — fallback de nome alternativo.

A API do Holyrics retorna slides ja pre-quebrados, na ordem que o
operador organizou na hora do cadastro. Cada slide costuma ser dict
``{text|lyrics, ...}`` ou string. Tratamos os dois formatos.

Permissoes necessarias no token (Holyrics > Configuracoes > API Server >
Permissoes): ``GetSongs``, ``SearchSong``, ``GetSong``.
"""

from __future__ import annotations

import unicodedata

from app.services.holyrics_service import (
    HolyricsConnectionError,
    HolyricsError,
    HolyricsService,
)


# ============================================================
# Helpers
# ============================================================

def _normalize(s: str) -> str:
    """Tira acentos e baixa caixa pra busca tolerante."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _slide_text(slide) -> str:
    """Extrai o texto de um slide vindo da API (formato pode variar).

    Pode ser string crua, ou dict com chaves ``text``, ``lyrics``,
    ``content``. Tentamos todas as variacoes conhecidas.
    """
    if slide is None:
        return ""
    if isinstance(slide, str):
        return slide
    if isinstance(slide, dict):
        for key in ("text", "lyrics", "content", "styled_text"):
            if key in slide and slide[key]:
                v = slide[key]
                return v if isinstance(v, str) else str(v)
    return str(slide)


def _extract_song_summary(item: dict) -> dict:
    """Normaliza um item da lista de musicas em ``{id, title, author}``."""
    return {
        "id": item.get("id") or item.get("Id") or item.get("song_id"),
        "title": item.get("title") or item.get("name") or "(sem titulo)",
        "author": item.get("author") or item.get("artist") or item.get("composer"),
    }


# ============================================================
# Operacoes publicas
# ============================================================

async def search_songs(query: str, limit: int = 50) -> list[dict]:
    """Busca musicas por nome, descricao e LETRA.

    Tenta o endpoint nativo ``SearchSong`` com payload que ativa busca
    em letra/descricao (parametros ``text=true`` e ``title=true`` que
    algumas versoes do Holyrics aceitam). Se a chamada nativa falhar
    OU vier vazia com query nao trivial, faz fallback pra ``GetSongs``
    + filtro client-side em titulo, autor, letra e descricao.
    """
    service = HolyricsService()  # carrega config do banco

    # Tentativa 1: SearchLyrics da API moderna.
    # Formato oficial: { text: <query>, lyrics: true } -> { data: [{id,title,...}] }
    # A flag "lyrics: true" faz buscar dentro da LETRA, nao so no titulo.
    native_results: list[dict] = []
    for method, payloads in (
        ("SearchLyrics", [
            {"text": query, "lyrics": True, "title": True, "artist": True},
            {"text": query, "lyrics": True},
            {"text": query},
        ]),
        ("SearchSong", [  # fallback p/ versoes antigas
            {"input": query},
        ]),
    ):
        for payload in payloads:
            try:
                data = await service._post(method, payload)
                raw = data.get("data") or data.get("songs") or data.get("lyrics") or []
                if isinstance(raw, list):
                    native_results = [
                        _extract_song_summary(s) for s in raw if isinstance(s, dict)
                    ]
                    if native_results or not query:
                        return native_results[:limit]
            except HolyricsError:
                continue
        if native_results:
            return native_results[:limit]

    # Tentativa 2: GetLyrics (lista) + filtro client-side em todos os campos
    data = None
    for method in ("GetLyricsPlaylist", "GetSongs"):
        try:
            data = await service._post(method)
            break
        except HolyricsError:
            continue
    if data is None:
        return []
    raw = data.get("data") or data.get("songs") or data.get("lyrics") or data.get("items") or []
    if not isinstance(raw, list):
        return []

    q = _normalize(query)
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        # Concatena tudo que pode conter texto pesquisavel.
        haystack_parts = [
            item.get("title") or item.get("name") or "",
            item.get("author") or item.get("artist") or "",
            item.get("description") or item.get("note") or "",
            item.get("lyrics") or item.get("text") or "",
        ]
        haystack = _normalize(" ".join(str(p) for p in haystack_parts if p))
        if not q or q in haystack:
            out.append(_extract_song_summary(item))
            if len(out) >= limit:
                break
    out.sort(key=lambda e: _normalize(e["title"]))
    return out


async def get_song_slides(song_id) -> dict:
    """Retorna a musica completa quebrada em slides.

    Tenta ``GetSong`` primeiro; se nao existir, tenta
    ``GetSongInformation`` (nome usado em algumas versoes).
    """
    service = HolyricsService()

    # Tenta os nomes conhecidos do endpoint (novo + legado).
    last_err: Exception | None = None
    for method in ("GetLyrics", "GetSong", "GetSongInformation"):
        try:
            data = await service._post(method, {"id": song_id})
            payload = data.get("data") or data
            return _normalize_song_payload(payload, song_id)
        except HolyricsError as e:
            last_err = e
            # So tenta o proximo nome se for "method not found", senao
            # propaga o erro real (ex.: musica nao existe).
            if "not found" not in str(e).lower() and "unauthorized" not in str(e).lower():
                raise

    # Ambos falharam.
    raise HolyricsError(
        f"Nao foi possivel obter detalhes da musica via API. Ultimo erro: {last_err}"
    )


def _normalize_song_payload(payload: dict, song_id) -> dict:
    """Converte o payload bruto da API em ``{id, title, author, slides}``.

    Estrutura tipica:
        {
          "id": ...,
          "title": "...",
          "author": "...",
          "slides": [
            {"text": "..."},  # ou string direto
            ...
          ]
        }
    """
    if not isinstance(payload, dict):
        raise HolyricsError("Resposta inesperada da API ao buscar musica.")

    raw_slides = (
        payload.get("slides")
        or payload.get("lyrics")
        or payload.get("text")
        or []
    )
    # Se "lyrics" vier como string unica, quebra por linhas em branco.
    if isinstance(raw_slides, str):
        chunks = [c.strip() for c in raw_slides.replace("\r\n", "\n").split("\n\n") if c.strip()]
        slides_text = chunks or [raw_slides.strip()]
    elif isinstance(raw_slides, list):
        slides_text = [_slide_text(s) for s in raw_slides]
        slides_text = [s for s in slides_text if s.strip()]
    else:
        slides_text = []

    return {
        "id": payload.get("id") or song_id,
        "title": payload.get("title") or payload.get("name") or "",
        "author": payload.get("author") or payload.get("artist"),
        "slides": slides_text,
    }


async def show_song(song_id, initial_index: int | None = None) -> dict:
    """Projeta o hino completo no Holyrics.

    Usa ``ShowLyrics`` (nome canonico na API moderna). Quando
    ``initial_index`` e passado, comeca daquele slide especifico — eh
    como o app oficial mobile do Holyrics faz pra trocar de slide.
    """
    service = HolyricsService()
    last_err: Exception | None = None
    base_payload: dict = {"id": song_id}
    if initial_index is not None:
        base_payload["initial_index"] = int(initial_index)
    for method, payload in (
        ("ShowLyrics", base_payload),
        ("ShowSong", base_payload),  # fallback p/ versoes antigas
    ):
        try:
            await service._post(method, payload)
            return {"ok": True, "method": method}
        except HolyricsError as e:
            last_err = e
            msg = str(e).lower()
            if "not found" not in msg and "unauthorized" not in msg:
                raise
            continue
    raise HolyricsError(
        f"Nao foi possivel projetar via API. Ultimo erro: {last_err}"
    )


async def show_slide(song_id, slide_index: int) -> dict:
    """Projeta um slide especifico de uma musica ja existente.

    O Holyrics reserva o indice 0 pra slide de TITULO (que nao mostramos
    na lista do mobile — so exibimos slides de letra). Por isso somamos
    +1 no indice antes de mandar pra API: nosso slide 0 (primeira
    estrofe) corresponde ao indice 1 do Holyrics.
    """
    return await show_song(song_id, initial_index=slide_index + 1)


async def close_presentation() -> dict:
    """Fecha qualquer projecao atual (musica/letra)."""
    service = HolyricsService()
    last_err: Exception | None = None
    for method in ("CloseCurrentPresentation", "CloseTextCPS", "HidePresentation"):
        try:
            await service._post(method)
            return {"ok": True, "method": method}
        except HolyricsError as e:
            last_err = e
            msg = str(e).lower()
            if "not found" not in msg and "unauthorized" not in msg:
                raise
            continue
    raise HolyricsError(f"Nao foi possivel fechar. Ultimo erro: {last_err}")


async def get_status() -> dict:
    """Ping da API do Holyrics (reusa o GetCPInfo)."""
    try:
        service = HolyricsService()
    except HolyricsConnectionError as e:
        return {"ok": False, "message": str(e), "configured": False}
    try:
        await service._post("GetCPInfo")
        return {"ok": True, "configured": True, "host": service.host, "port": service.port}
    except Exception as e:
        return {"ok": False, "message": str(e), "configured": True}
