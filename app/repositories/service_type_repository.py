"""CRUD da tabela ``service_types``."""

from datetime import datetime
from sqlite3 import Row

from app.database import get_connection
from app.models.service_type import ServiceType
from app.repositories.base import BaseRepository


class ServiceTypeRepository(BaseRepository[ServiceType]):
    """Repositorio responsavel pela persistencia de ``ServiceType``."""

    def list_all(self) -> list[ServiceType]:
        """Retorna todos os tipos de culto ordenados por nome."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM service_types ORDER BY name"
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_by_id(self, record_id: int) -> ServiceType | None:
        """Retorna um tipo de culto pelo id."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM service_types WHERE id = ?", (record_id,)
            ).fetchone()
        return self._row_to_model(row) if row else None

    def get_suggested_for_weekday(self, weekday: int) -> ServiceType | None:
        """Retorna o tipo de culto sugerido para um dia da semana.

        Args:
            weekday: Dia da semana (0=segunda..6=domingo).

        Returns:
            Tipo de culto sugerido, ou ``None`` se nao houver.
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM service_types WHERE suggested_weekday = ? LIMIT 1",
                (weekday,),
            ).fetchone()
        return self._row_to_model(row) if row else None

    def create(self, model: ServiceType) -> ServiceType:
        """Persiste um novo tipo de culto e popula ``model.id``."""
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO service_types
                    (name, title_template, description_template, suggested_weekday)
                VALUES (?, ?, ?, ?)
                """,
                (
                    model.name,
                    model.title_template,
                    model.description_template,
                    model.suggested_weekday,
                ),
            )
            model.id = cursor.lastrowid
        return model

    def update(self, record_id: int, model: ServiceType) -> ServiceType | None:
        """Atualiza um tipo de culto existente. Retorna o estado novo ou ``None``."""
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE service_types
                   SET name                 = ?,
                       title_template       = ?,
                       description_template = ?,
                       suggested_weekday    = ?,
                       updated_at           = datetime('now')
                 WHERE id = ?
                """,
                (
                    model.name,
                    model.title_template,
                    model.description_template,
                    model.suggested_weekday,
                    record_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_by_id(record_id)

    def delete(self, record_id: int) -> bool:
        """Remove um tipo de culto pelo id."""
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM service_types WHERE id = ?", (record_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row: Row) -> ServiceType:
        """Converte uma ``sqlite3.Row`` em uma instancia de ``ServiceType``."""
        created = row["created_at"]
        updated = row["updated_at"]
        return ServiceType(
            id=row["id"],
            name=row["name"],
            title_template=row["title_template"],
            description_template=row["description_template"] or "",
            suggested_weekday=row["suggested_weekday"],
            created_at=datetime.fromisoformat(created) if created else None,
            updated_at=datetime.fromisoformat(updated) if updated else None,
        )
