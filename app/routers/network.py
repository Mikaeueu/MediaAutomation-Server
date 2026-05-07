"""Endpoints com informacoes de rede da maquina (IP, URL mobile etc.)."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.services.network_service import NetworkService


router = APIRouter(
    prefix="/api/network",
    tags=["network"],
    dependencies=[Depends(get_current_user)],
)


def get_service() -> NetworkService:
    """FastAPI dependency que provem um ``NetworkService``.

    Returns:
        Instancia do servico de rede.
    """
    return NetworkService()


@router.get("/info")
def network_info(
    service: NetworkService = Depends(get_service),
) -> dict[str, str | int]:
    """Retorna IP local, hostname e URLs de acesso desktop/mobile.

    Args:
        service: Servico injetado.

    Returns:
        Dicionario com ``ip``, ``hostname``, ``port``, ``desktop_url`` e
        ``mobile_url``.
    """
    return service.get_info()
