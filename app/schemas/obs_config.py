"""Schemas Pydantic para os endpoints de ``ObsConfig``."""

from pydantic import BaseModel, Field


class ObsConfigUpdate(BaseModel):
    """Payload para atualizar a configuracao do OBS."""

    host: str = Field(..., min_length=1, max_length=120)
    port: int = Field(..., ge=1, le=65535)
    password: str = ""
    auto_connect: bool = True


class ObsConfigRead(BaseModel):
    """Configuracao do OBS retornada ao cliente.

    A senha e exposta para que o painel possa exibir e re-editar (e um
    painel administrativo local, nao publico). Caso queira mascarar, troque
    por ``has_password: bool`` aqui.
    """

    id: int
    host: str
    port: int
    password: str
    auto_connect: bool


class ObsTestRequest(BaseModel):
    """Payload para testar credenciais sem persistir."""

    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    password: str = ""


class ObsTestResponse(BaseModel):
    """Resposta do teste de conexao."""

    ok: bool
    message: str
    obs_version: str | None = None
