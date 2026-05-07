"""Endpoints de geracao de titulo/descricao para a live."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.services.title_generator_service import TitleGeneratorService


router = APIRouter(
    prefix="/api/live",
    tags=["live"],
    dependencies=[Depends(get_current_user)],
)


def get_service() -> TitleGeneratorService:
    """FastAPI dependency para o ``TitleGeneratorService``.

    Returns:
        Instancia recem-criada do servico.
    """
    return TitleGeneratorService()


@router.get("/suggestion")
def todays_suggestion(
    service: TitleGeneratorService = Depends(get_service),
) -> dict:
    """Retorna o tipo de culto sugerido para o dia da semana atual.

    Returns:
        Dicionario com a chave ``suggestion`` (pode ser ``None``).
    """
    suggestion = service.suggest_for_today()
    return {"suggestion": suggestion.to_dict() if suggestion else None}


@router.post("/generate/{service_type_id}")
def generate_live(
    service_type_id: int,
    service: TitleGeneratorService = Depends(get_service),
) -> dict:
    """Gera titulo e descricao da live para um tipo de culto.

    Raises:
        HTTPException: 404 se o tipo nao existir.
    """
    try:
        return service.generate(service_type_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
