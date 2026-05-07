"""Dependencias reutilizaveis do FastAPI para autenticacao.

Padronizamos duas formas de obter o usuario:
    * ``get_current_user_optional`` - retorna o username ou None (uso em paginas).
    * ``get_current_user``           - exige sessao valida (uso em APIs).
"""

from fastapi import Cookie, Depends, HTTPException, status

from app.core.security import decode_access_token


def get_current_user_optional(
    access_token: str | None = Cookie(default=None),
) -> str | None:
    """Retorna o usuario autenticado ou ``None`` se nao houver sessao valida.

    Esta variante NAO levanta excecao: e ideal para paginas que querem
    redirecionar para o login em vez de retornar 401.

    Args:
        access_token: JWT lido do cookie ``access_token``.

    Returns:
        Username, ou None.
    """
    if not access_token:
        return None
    payload = decode_access_token(access_token)
    if not payload:
        return None
    return payload.get("sub")


def get_current_user(
    username: str | None = Depends(get_current_user_optional),
) -> str:
    """Retorna o usuario autenticado ou levanta 401.

    Args:
        username: Username extraido pela dependencia opcional.

    Raises:
        HTTPException: 401 quando nao ha sessao valida.

    Returns:
        Username autenticado.
    """
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessao invalida ou expirada.",
        )
    return username
