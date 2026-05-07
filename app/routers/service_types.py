"""Endpoints CRUD de tipos de culto.

Todas as rotas exigem sessao valida (``get_current_user``).
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.service_type import ServiceType
from app.repositories.service_type_repository import ServiceTypeRepository
from app.schemas.service_type import (
    ServiceTypeCreate,
    ServiceTypeRead,
    ServiceTypeUpdate,
)


router = APIRouter(
    prefix="/api/service-types",
    tags=["service-types"],
    dependencies=[Depends(get_current_user)],
)


def get_repository() -> ServiceTypeRepository:
    """FastAPI dependency que provem um ``ServiceTypeRepository``.

    Returns:
        Instancia recem-criada do repositorio.
    """
    return ServiceTypeRepository()


@router.get("", response_model=list[ServiceTypeRead])
def list_service_types(
    repo: ServiceTypeRepository = Depends(get_repository),
) -> list[dict]:
    """Lista todos os tipos de culto cadastrados."""
    return [item.to_dict() for item in repo.list_all()]


@router.get("/{service_type_id}", response_model=ServiceTypeRead)
def get_service_type(
    service_type_id: int,
    repo: ServiceTypeRepository = Depends(get_repository),
) -> dict:
    """Retorna um tipo de culto especifico pelo id.

    Raises:
        HTTPException: 404 se nao encontrado.
    """
    item = repo.get_by_id(service_type_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de culto nao encontrado.",
        )
    return item.to_dict()


@router.post(
    "",
    response_model=ServiceTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_service_type(
    payload: ServiceTypeCreate,
    repo: ServiceTypeRepository = Depends(get_repository),
) -> dict:
    """Cria um novo tipo de culto.

    Raises:
        HTTPException: 400 se a validacao do dominio falhar.
    """
    try:
        model = ServiceType(**payload.model_dump())
        return repo.create(model).to_dict()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put("/{service_type_id}", response_model=ServiceTypeRead)
def update_service_type(
    service_type_id: int,
    payload: ServiceTypeUpdate,
    repo: ServiceTypeRepository = Depends(get_repository),
) -> dict:
    """Atualiza um tipo de culto existente.

    Raises:
        HTTPException: 400 em validacao de dominio, 404 se nao existir.
    """
    try:
        model = ServiceType(**payload.model_dump())
        updated = repo.update(service_type_id, model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de culto nao encontrado.",
        )
    return updated.to_dict()


@router.delete("/{service_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_type(
    service_type_id: int,
    repo: ServiceTypeRepository = Depends(get_repository),
) -> None:
    """Remove um tipo de culto pelo id.

    Raises:
        HTTPException: 404 se nao existir.
    """
    if not repo.delete(service_type_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de culto nao encontrado.",
        )
