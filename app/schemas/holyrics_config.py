"""Schemas Pydantic para os endpoints de Holyrics."""

from datetime import datetime
from typing import Any, Optional, List

from pydantic import BaseModel, Field


# ============================================================
# 🔹 PADRÃO GLOBAL DE RESPOSTA
# ============================================================

class DefaultResponse(BaseModel):
    """
    Resposta padrão da API.

    Sempre usar:
    {
        "ok": bool,
        "message": str | None,
        "data": any | None
    }
    """

    ok: bool
    message: Optional[str] = None
    data: Optional[Any] = None


# ============================================================
# 🔹 CONFIGURAÇÃO
# ============================================================

class HolyricsConfigUpdate(BaseModel):
    """Payload para atualizar a configuração do Holyrics."""

    host: str = Field(..., min_length=1, max_length=120)
    port: int = Field(..., ge=1, le=65535)
    token: str = ""


class HolyricsConfigRead(BaseModel):
    """Dados da configuração retornados ao frontend."""

    host: str
    port: int
    token: str
    is_configured: bool


class HolyricsConfigResponse(DefaultResponse):
    """Resposta padrão contendo configuração."""
    data: Optional[HolyricsConfigRead] = None


# ============================================================
# 🔹 TESTE DE CONEXÃO
# ============================================================

class HolyricsTestResponse(DefaultResponse):
    """Resposta do teste de conexão."""
    pass


# ============================================================
# 🔹 STATUS
# ============================================================

class HolyricsStatusResponse(DefaultResponse):
    """Status da conexão com o Holyrics."""
    data: Optional[dict] = None


# ============================================================
# 🔹 VERSÍCULOS
# ============================================================

class SetVerseRequest(BaseModel):
    """Payload para exibir um versículo no Holyrics."""

    version: str = Field(
        ...,
        min_length=1,
        description="Abreviação da versão (ex: 'ARC', 'NVI')."
    )

    book: str = Field(
        ...,
        min_length=1,
        description="Nome ou abreviação do livro (ex: 'João', 'Mateus', 'Gn')."
    )

    chapter: int = Field(..., ge=1)
    verse: int = Field(..., ge=1)


class VerseResponse(DefaultResponse):
    """Resposta ao exibir versículo."""
    pass


# ============================================================
# 🔹 HISTÓRICO
# ============================================================

class RecentVerseRead(BaseModel):
    """Item do histórico de versículos exibidos."""

    id: int
    version: str
    book: str
    chapter: int
    verse: int
    label: str
    used_at: datetime


class RecentListResponse(DefaultResponse):
    """Lista de histórico."""
    data: Optional[List[RecentVerseRead]] = None