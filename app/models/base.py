"""Classe base para os modelos de dominio.

Todos os modelos herdam ``BaseModel`` e devem ser decorados com ``@dataclass``.
A classe oferece um ``to_dict`` uniforme que normaliza ``datetime``/``date``
para strings ISO 8601, evitando problemas ao serializar para JSON.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class BaseModel:
    """Base abstrata para entidades de dominio.

    Subclasses devem ser declaradas como ``@dataclass`` e podem implementar
    ``__post_init__`` para validacao apos o ``__init__`` gerado.
    """

    def to_dict(self) -> dict[str, Any]:
        """Serializa a dataclass como um dicionario JSON-friendly.

        Datas e datetimes sao convertidos para strings ISO 8601.

        Returns:
            Dicionario representando a instancia.
        """
        return _normalize(asdict(self))


def _normalize(value: Any) -> Any:
    """Converte recursivamente ``datetime``/``date`` em strings ISO.

    Args:
        value: Valor a normalizar (pode ser dict, list, datetime ou primitivo).

    Returns:
        Estrutura equivalente, com datetimes convertidos.
    """
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
