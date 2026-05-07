"""CRUD da tabela ``obs_config`` (singleton id=1)."""

from datetime import datetime
from sqlite3 import Row

from app.database import get_connection
from app.models.obs_config import ObsConfig


class ObsConfigRepository:
    """Repositorio singleton para ``ObsConfig`` (sempre uma linha so)."""

    def get(self) -> ObsConfig:
        """Retorna a configuracao atual, criando default se nao existir.

        Returns:
            ``ObsConfig`` persistido.
        """
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM obs_config WHERE id = 1"
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO obs_config (id, host, port, password, auto_connect) "
                    "VALUES (1, 'localhost', 4455, '', 1)"
                )
                row = conn.execute(
                    "SELECT * FROM obs_config WHERE id = 1"
                ).fetchone()
        return self._row_to_model(row)

    def save(self, config: ObsConfig) -> ObsConfig:
        """Atualiza (ou insere) a config singleton.

        Args:
            config: Modelo a persistir.

        Returns:
            Modelo persistido com ``updated_at`` atualizado.
        """
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO obs_config (id, host, port, password, auto_connect, updated_at)
                VALUES (1, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    host = excluded.host,
                    port = excluded.port,
                    password = excluded.password,
                    auto_connect = excluded.auto_connect,
                    updated_at = datetime('now')
                """,
                (
                    config.host,
                    config.port,
                    config.password,
                    1 if config.auto_connect else 0,
                ),
            )
        return self.get()

    @staticmethod
    def _row_to_model(row: Row) -> ObsConfig:
        """Converte sqlite3.Row em ``ObsConfig``."""
        updated = row["updated_at"]
        return ObsConfig(
            id=row["id"],
            host=row["host"],
            port=row["port"],
            password=row["password"] or "",
            auto_connect=bool(row["auto_connect"]),
            updated_at=datetime.fromisoformat(updated) if updated else None,
        )
