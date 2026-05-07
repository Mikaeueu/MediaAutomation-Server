"""Modelo de dominio ``User``."""

from dataclasses import dataclass
from datetime import datetime

from app.models.base import BaseModel


@dataclass
class User(BaseModel):
    """Representa um usuario da aplicacao.

    Attributes:
        username: Nome de usuario unico (lowercased).
        password_hash: Hash bcrypt da senha.
        id: Chave primaria (None ate ser persistido).
        created_at: Momento de criacao (preenchido pelo banco).
    """

    username: str
    password_hash: str
    id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida e normaliza os campos apos a inicializacao da dataclass."""
        if not self.username or not self.username.strip():
            raise ValueError("username nao pode ser vazio.")
        if not self.password_hash:
            raise ValueError("password_hash e obrigatorio.")
        self.username = self.username.strip().lower()
