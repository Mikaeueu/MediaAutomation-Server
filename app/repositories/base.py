"""Interface abstrata definindo o contrato CRUD dos repositorios.

Garante que toda entidade exposta na API tenha um conjunto consistente de
operacoes (list, get, create, update, delete). Isso simplifica a composicao
em rotas e abre espaco para padroes como ``Generic Router`` no futuro.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

ModelT = TypeVar("ModelT")


class BaseRepository(ABC, Generic[ModelT]):
    """Contrato CRUD que repositorios concretos devem implementar.

    Subclasses devem implementar todos os metodos abstratos abaixo.
    """

    @abstractmethod
    def list_all(self) -> list[ModelT]:
        """Retorna todos os registros da tabela."""

    @abstractmethod
    def get_by_id(self, record_id: int) -> ModelT | None:
        """Retorna um registro pelo id, ou ``None`` se nao existir."""

    @abstractmethod
    def create(self, model: ModelT) -> ModelT:
        """Persiste um novo registro e retorna o modelo com o id atribuido."""

    @abstractmethod
    def update(self, record_id: int, model: ModelT) -> ModelT | None:
        """Atualiza um registro existente. Retorna o estado novo ou ``None``."""

    @abstractmethod
    def delete(self, record_id: int) -> bool:
        """Remove um registro pelo id. Retorna ``True`` em caso de sucesso."""
