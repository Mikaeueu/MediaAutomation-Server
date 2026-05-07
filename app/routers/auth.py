"""Rotas de autenticacao (login e logout)."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service() -> AuthService:
    """FastAPI dependency que provem uma instancia de ``AuthService``.

    Returns:
        Instancia recem-criada de ``AuthService``.
    """
    return AuthService()


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Valida credenciais e seta um cookie HTTP-only com o JWT.

    Args:
        payload: Corpo da requisicao com username e senha.
        response: Resposta FastAPI (mutada para escrever o cookie).
        service: Servico de autenticacao injetado.

    Raises:
        HTTPException: 401 quando as credenciais sao invalidas.

    Returns:
        Dados do login bem-sucedido.
    """
    user = service.authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha invalidos.",
        )
    token = create_access_token(subject=user.username)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return LoginResponse(username=user.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    """Encerra a sessao removendo o cookie.

    Args:
        response: Resposta FastAPI (mutada para apagar o cookie).
    """
    response.delete_cookie("access_token")
