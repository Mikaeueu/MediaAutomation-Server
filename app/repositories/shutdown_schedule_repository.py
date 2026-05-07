"""CRUD da tabela ``shutdown_schedules``."""

from datetime import datetime
from sqlite3 import Row

from app.database import get_connection
from app.models.shutdown_schedule import ShutdownSchedule
from app.repositories.base import BaseRepository


class ShutdownScheduleRepository(BaseRepository[ShutdownSchedule]):
    """Repositorio responsavel pela persistencia de ``ShutdownSchedule``."""

    def list_all(self) -> list[ShutdownSchedule]:
        """Retorna todos os agendamentos, mais recentes primeiro."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM shutdown_schedules ORDER BY scheduled_for DESC"
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def list_active(self) -> list[ShutdownSchedule]:
        """Retorna apenas os agendamentos com status 'scheduled'."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM shutdown_schedules "
                "WHERE status = 'scheduled' ORDER BY scheduled_for ASC"
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_by_id(self, record_id: int) -> ShutdownSchedule | None:
        """Retorna um agendamento pelo id."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM shutdown_schedules WHERE id = ?", (record_id,)
            ).fetchone()
        return self._row_to_model(row) if row else None

    def create(self, model: ShutdownSchedule) -> ShutdownSchedule:
        """Persiste um novo agendamento e popula ``model.id``."""
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO shutdown_schedules (scheduled_for, action, status)
                VALUES (?, ?, ?)
                """,
                (
                    model.scheduled_for.isoformat(timespec="seconds"),
                    model.action,
                    model.status,
                ),
            )
            model.id = cursor.lastrowid
        return self.get_by_id(model.id) or model

    def update(
        self, record_id: int, model: ShutdownSchedule
    ) -> ShutdownSchedule | None:
        """Atualiza scheduled_for, action e status de um agendamento."""
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE shutdown_schedules
                   SET scheduled_for = ?,
                       action        = ?,
                       status        = ?
                 WHERE id = ?
                """,
                (
                    model.scheduled_for.isoformat(timespec="seconds"),
                    model.action,
                    model.status,
                    record_id,
                ),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_by_id(record_id)

    def update_status(self, record_id: int, status: str) -> bool:
        """Atualiza apenas o ``status`` de um agendamento (helper).

        Args:
            record_id: id do agendamento.
            status: Novo status (scheduled|executed|cancelled).

        Returns:
            True se atualizou; False se o id nao existir.
        """
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE shutdown_schedules SET status = ? WHERE id = ?",
                (status, record_id),
            )
            return cursor.rowcount > 0

    def delete(self, record_id: int) -> bool:
        """Remove um agendamento pelo id."""
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM shutdown_schedules WHERE id = ?", (record_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row: Row) -> ShutdownSchedule:
        """Converte uma ``sqlite3.Row`` em ``ShutdownSchedule``."""
        created = row["created_at"]
        return ShutdownSchedule(
            id=row["id"],
            scheduled_for=datetime.fromisoformat(row["scheduled_for"]),
            action=row["action"] or "shutdown",
            status=row["status"] or "scheduled",
            created_at=datetime.fromisoformat(created) if created else None,
        )
