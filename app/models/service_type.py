"""Modelo de dominio ``ServiceType`` (tipo de culto)."""

from dataclasses import dataclass
from datetime import datetime

from app.models.base import BaseModel


@dataclass
class ServiceType(BaseModel):
    """Representa um tipo de culto com seus templates de titulo e descricao.

    Os templates aceitam placeholders no formato ``{nome}`` que serao
    substituidos no momento da geracao da live. Variaveis disponiveis:
    ``data``, ``data_extenso``, ``hora``, ``dia_semana``, ``ano``, ``mes``,
    ``dia``.

    Attributes:
        name: Nome humanizado (ex: "Culto Domingo Manha").
        title_template: Template do titulo, com placeholders.
        description_template: Template da descricao (opcional).
        suggested_weekday: Dia da semana (0=segunda..6=domingo) para
            sugerir este tipo automaticamente. ``None`` desabilita sugestao.
        id: Chave primaria.
        created_at: Momento de criacao.
        updated_at: Momento da ultima atualizacao.
    """

    name: str
    title_template: str
    description_template: str = ""
    suggested_weekday: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida e normaliza os campos apos a inicializacao da dataclass."""
        if not self.name or not self.name.strip():
            raise ValueError("Nome do tipo de culto nao pode ser vazio.")
        if not self.title_template or not self.title_template.strip():
            raise ValueError("title_template nao pode ser vazio.")
        if self.suggested_weekday is not None and not 0 <= self.suggested_weekday <= 6:
            raise ValueError("suggested_weekday deve estar entre 0 e 6.")

        self.name = self.name.strip()
        self.title_template = self.title_template.strip()
        self.description_template = (self.description_template or "").strip()
