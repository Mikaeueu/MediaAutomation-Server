"""CRUD da tabela ``users``."""

from datetime import datetime
from sqlite3 import Row

from app.database import get_connection
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repositorio responsavel pela persistencia de ``User``."""

    def list_all(self) -> list[User]:
        """Retorna todos os usuarios cadastrados."""
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
        return [self._row_to_model(row) for row in rows]

    def get_by_id(self, record_id: int) -> User | None:
        """Retorna um usuario pelo id."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE id = ?", (record_id,)
            ).fetchone()
        return self._row_to_model(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        """Retorna um usuario pelo username (case-insensitive).

        Args:
            username: Nome de usuario procurado.

        Returns:
            ``User`` se encontrado, ``None`` caso contrario.
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username.strip().lower(),),
            ).fetchone()
        return self._row_to_model(row) if row else None

    def create(self, model: User) -> User:
        """Persiste um novo usuario e popula ``model.id``."""
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (model.username, model.password_hash),
            )
            model.id = cursor.lastrowid
        return model

    def update(self, record_id: int, model: User) -> User | None:
        """Atualiza o ``password_hash`` de um usuario existente."""
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (model.password_hash, record_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_by_id(record_id)

    def delete(self, record_id: int) -> bool:
        """Remove um usuario pelo id."""
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_model(row: Row) -> User:
        """Converte uma ``sqlite3.Row`` em uma instancia de ``User``."""
        created = row["created_at"]
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            created_at=datetime.fromisoformat(created) if created else None,
        )
