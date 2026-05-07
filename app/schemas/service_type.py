"""Schemas Pydantic para os endpoints de ``ServiceType``."""

from pydantic import BaseModel, Field


class ServiceTypeBase(BaseModel):
    """Campos compartilhados entre criacao e atualizacao."""

    name: str = Field(..., min_length=1, max_length=120)
    title_template: str = Field(..., min_length=1)
    description_template: str = ""
    suggested_weekday: int | None = Field(default=None, ge=0, le=6)


class ServiceTypeCreate(ServiceTypeBase):
    """Payload para criar um novo tipo de culto."""


class ServiceTypeUpdate(ServiceTypeBase):
    """Payload para atualizar um tipo de culto existente."""


class ServiceTypeRead(ServiceTypeBase):
    """Tipo de culto retornado ao cliente."""

    id: int
