"""Endpoints CRUD de agendamentos de desligamento/suspensao."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.schemas.shutdown_schedule import (
    ShutdownScheduleCreate,
    ShutdownScheduleRead,
)
from app.services.shutdown_service import ShutdownService


router = APIRouter(
    prefix="/api/shutdown",
    tags=["shutdown"],
    dependencies=[Depends(get_current_user)],
)


def get_service() -> ShutdownService:
    """FastAPI dependency que provem um ``ShutdownService``.

    Returns:
        Instancia do servico (singleton-friendly via SchedulerService).
    """
    return ShutdownService()


@router.get("", response_model=list[ShutdownScheduleRead])
def list_schedules(
    service: ShutdownService = Depends(get_service),
) -> list[dict]:
    """Lista todos os agendamentos (mais recentes primeiro)."""
    return [item.to_dict() for item in service.list_schedules()]


@router.post(
    "",
    response_model=ShutdownScheduleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    payload: ShutdownScheduleCreate,
    service: ShutdownService = Depends(get_service),
) -> dict:
    """Cria um novo agendamento de desligamento ou suspensao.

    Raises:
        HTTPException: 400 se a validacao falhar.
    """
    try:
        saved = service.schedule(
            scheduled_for=payload.scheduled_for,
            action=payload.action,
        )
        return saved.to_dict()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{schedule_id}/postpone", response_model=ShutdownScheduleRead)
def postpone_schedule(
    schedule_id: int,
    minutes: int = 30,
    service: ShutdownService = Depends(get_service),
) -> dict:
    """Adia um agendamento em N minutos (default 30).

    Args:
        schedule_id: Id do agendamento a adiar.
        minutes: Quantos minutos somar a "agora" (query param).

    Raises:
        HTTPException: 400 em parametro invalido, 404 se nao encontrar.
    """
    try:
        new_schedule = service.postpone(schedule_id, minutes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    if not new_schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento nao encontrado.",
        )
    return new_schedule.to_dict()


@router.post("/{schedule_id}/cancel", response_model=ShutdownScheduleRead)
def cancel_schedule(
    schedule_id: int,
    service: ShutdownService = Depends(get_service),
) -> dict:
    """Cancela um agendamento (mantem o registro com status 'cancelled').

    Raises:
        HTTPException: 404 se o agendamento nao existir.
    """
    cancelled = service.cancel(schedule_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento nao encontrado.",
        )
    return cancelled.to_dict()


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: int,
    service: ShutdownService = Depends(get_service),
) -> None:
    """Remove permanentemente um agendamento (cancela o job se houver).

    Raises:
        HTTPException: 404 se o id nao existir.
    """
    if not service.delete(schedule_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento nao encontrado.",
        )
