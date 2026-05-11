"""Repositorio chave-valor generico em ``app_settings``.

Usado pra guardar pequenas configs persistentes que nao merecem tabela
propria (ex.: caminho da pasta de dados do Holyrics, flags de feature).
"""

from __future__ import annotations

from app.database import get_connection


class AppSettingsRepository:
    """CRUD chave-valor sobre a tabela ``app_settings``."""

    def get(self, key: str) -> str | None:
        """Retorna o valor da chave, ou ``None`` se nao existir."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
            return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        """Cria ou atualiza o valor da chave (upsert)."""
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = datetime('now')
                """,
                (key, value),
            )

    def delete(self, key: str) -> None:
        """Remove uma chave (no-op se nao existir)."""
        with get_connection() as conn:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
