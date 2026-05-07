"""Schemas Pydantic para os endpoints de ``ShutdownSchedule``."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ActionLiteral = Literal["shutdown", "suspend"]
StatusLiteral = Literal["scheduled", "executed", "cancelled"]


class ShutdownScheduleCreate(BaseModel):
    """Payload para criar um novo agendamento."""

    scheduled_for: datetime = Field(
        ...,
        description="Data e hora local em que a acao deve ser executada.",
    )
    action: ActionLiteral = Field(
        default="shutdown",
        description="'shutdown' para desligar; 'suspend' para suspender.",
    )


class ShutdownScheduleRead(BaseModel):
    """Agendamento retornado ao cliente."""

    id: int
    scheduled_for: datetime
    action: ActionLiteral
    status: StatusLiteral
    created_at: datetime | None = None
