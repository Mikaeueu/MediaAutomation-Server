"""Modelo de dominio ``ObsConfig`` (configuracao do OBS WebSocket)."""

from dataclasses import dataclass
from datetime import datetime

from app.models.base import BaseModel


@dataclass
class ObsConfig(BaseModel):
    """Configuracao da conexao com o OBS WebSocket.

    Singleton: sempre persistido com ``id=1``.

    Attributes:
        host: Host do OBS (default ``localhost``).
        port: Porta do WebSocket (default OBS v5 = 4455).
        password: Senha do servidor WebSocket. Vazia = sem auth.
        auto_connect: Se True, conecta automaticamente no startup.
        id: Sempre ``1`` (singleton).
        updated_at: Quando foi atualizado por ultimo.
    """

    host: str = "localhost"
    port: int = 4455
    password: str = ""
    auto_connect: bool = True
    id: int = 1
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida e normaliza os campos."""
        if not self.host or not self.host.strip():
            raise ValueError("host nao pode ser vazio.")
        if not 1 <= self.port <= 65535:
            raise ValueError("port deve estar entre 1 e 65535.")
        self.host = self.host.strip()
        self.password = self.password or ""
