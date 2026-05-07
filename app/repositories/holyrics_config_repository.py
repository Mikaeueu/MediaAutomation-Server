from datetime import datetime
from sqlite3 import Row

from app.database import get_connection
from app.models.holyrics_config import HolyricsConfig


class HolyricsConfigRepository:
    """Persistencia singleton da config Holyrics."""

    def get(self) -> HolyricsConfig:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM holyrics_config WHERE id = 1"
            ).fetchone()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO holyrics_config
                        (id, host, port, token, updated_at)
                    VALUES
                        (1, 'localhost', 8091, '', datetime('now'))
                    """
                )
                conn.commit()  # 🔥 GARANTE persistência

                row = conn.execute(
                    "SELECT * FROM holyrics_config WHERE id = 1"
                ).fetchone()

        return self._row_to_model(row)

    def save(self, config: HolyricsConfig) -> HolyricsConfig:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO holyrics_config (id, host, port, token, updated_at)
                VALUES (1, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    host = excluded.host,
                    port = excluded.port,
                    token = excluded.token,
                    updated_at = datetime('now')
                """,
                (config.host, config.port, config.token),
            )

            conn.commit()  # 🔥 ESSA LINHA É O SEGREDO

        return self.get()

    @staticmethod
    def _row_to_model(row: Row) -> HolyricsConfig:
        updated = row["updated_at"]

        return HolyricsConfig(
            id=row["id"],
            host=row["host"],
            port=row["port"],
            token=row["token"] or "",
            updated_at=datetime.fromisoformat(updated) if updated else None,
        )


class RecentVersesRepository:
    MAX_KEEP = 20

    def list_recent(self, limit: int = 10) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM holyrics_recent_verses ORDER BY used_at DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "version": row["version"],
                "book": row["book"],
                "chapter": row["chapter"],
                "verse": row["verse"],
                "label": row["label"],
                "used_at": row["used_at"],
            }
            for row in rows
        ]

    def add(self, version: str, book: str, chapter: int, verse: int, label: str) -> None:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO holyrics_recent_verses
                    (version, book, chapter, verse, label)
                VALUES (?, ?, ?, ?, ?)
                """,
                (version, book, chapter, verse, label),
            )

            conn.execute(
                """
                DELETE FROM holyrics_recent_verses
                 WHERE id NOT IN (
                    SELECT id FROM holyrics_recent_verses
                    ORDER BY used_at DESC LIMIT ?
                 )
                """,
                (self.MAX_KEEP,),
            )

            conn.commit()  # 🔥 garante histórico também

    def clear(self) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM holyrics_recent_verses")
            conn.commit()