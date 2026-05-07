"""Schemas Pydantic para os endpoints de autenticacao."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload do formulario de login."""

    username: str = Field(..., min_length=1, description="Usuario de acesso.")
    password: str = Field(..., min_length=1, description="Senha de acesso.")


class LoginResponse(BaseModel):
    """Resposta retornada apos login bem-sucedido."""

    username: str
    message: str = "Login realizado com sucesso."
