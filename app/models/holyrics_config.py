"""Modelo de dominio ``HolyricsConfig`` (configuracao da API do Holyrics)."""

from dataclasses import dataclass
from datetime import datetime

from app.models.base import BaseModel


@dataclass
class HolyricsConfig(BaseModel):
    """Configuracao da API local do Holyrics.

    Singleton: sempre persistido com ``id=1``.

    Attributes:
        host: Host do Holyrics (default ``localhost``).
        port: Porta da API (default 8091).
        token: Token de autenticacao gerado em Holyrics > Configuracoes > API Server.
        id: Sempre ``1`` (singleton).
        updated_at: Quando foi atualizado por ultimo.
    """

    host: str = "localhost"
    port: int = 8091
    token: str = ""
    id: int = 1
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida e normaliza os campos."""
        if not self.host or not self.host.strip():
            raise ValueError("host nao pode ser vazio.")
        if not 1 <= self.port <= 65535:
            raise ValueError("port deve estar entre 1 e 65535.")
        self.host = self.host.strip()
        self.token = (self.token or "").strip()

    @property
    def base_url(self) -> str:
        """Retorna a URL base da API (ex: http://localhost:8091)."""
        return f"http://{self.host}:{self.port}"

    @property
    def is_configured(self) -> bool:
        """Indica se ha token configurado (minimo pra funcionar)."""
        return bool(self.token)
