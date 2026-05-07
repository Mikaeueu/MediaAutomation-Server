"""Modelo de dominio ``ShutdownSchedule`` (agendamento de desligamento/suspensao)."""

from dataclasses import dataclass
from datetime import datetime

from app.models.base import BaseModel


VALID_ACTIONS: frozenset[str] = frozenset({"shutdown", "suspend"})
VALID_STATUSES: frozenset[str] = frozenset({"scheduled", "executed", "cancelled"})


@dataclass
class ShutdownSchedule(BaseModel):
    """Agendamento para desligar ou suspender o computador.

    Attributes:
        scheduled_for: Momento exato em que a acao deve disparar.
        action: ``"shutdown"`` (desligar) ou ``"suspend"`` (suspender).
        status: ``"scheduled"`` (ativo), ``"executed"`` ou ``"cancelled"``.
        id: Chave primaria.
        created_at: Momento de criacao do agendamento.
    """

    scheduled_for: datetime
    action: str = "shutdown"
    status: str = "scheduled"
    id: int | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida campos apos a inicializacao da dataclass."""
        if not isinstance(self.scheduled_for, datetime):
            raise ValueError("scheduled_for deve ser um datetime.")
        if self.action not in VALID_ACTIONS:
            raise ValueError(
                f"action invalida: {self.action!r}. "
                f"Aceitas: {sorted(VALID_ACTIONS)}."
            )
        if self.status not in VALID_STATUSES:
            raise ValueError(
                f"status invalido: {self.status!r}. "
                f"Aceitos: {sorted(VALID_STATUSES)}."
            )
