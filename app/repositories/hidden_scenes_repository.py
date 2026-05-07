"""CRUD da tabela ``obs_hidden_scenes``.

Tabela simples chave-valor onde cada linha e o nome de uma cena que o
operador escolheu ocultar do painel. Cenas ocultas vao pro fim da lista
e nao podem ser ativadas.
"""

from app.database import get_connection


class HiddenScenesRepository:
    """Persistencia das cenas ocultas (singleton de tabela simples)."""

    def list_all(self) -> list[str]:
        """Retorna a lista de nomes de cenas ocultas."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT scene_name FROM obs_hidden_scenes ORDER BY hidden_at"
            ).fetchall()
        return [row["scene_name"] for row in rows]

    def list_set(self) -> set[str]:
        """Retorna o conjunto de cenas ocultas (lookup O(1))."""
        return set(self.list_all())

    def hide(self, name: str) -> bool:
        """Marca uma cena como oculta. Idempotente.

        Args:
            name: Nome exato da cena no OBS.

        Returns:
            True sempre (insercao com OR IGNORE).
        """
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO obs_hidden_scenes (scene_name) VALUES (?)",
                (name,),
            )
        return True

    def unhide(self, name: str) -> bool:
        """Remove uma cena da lista de ocultas.

        Returns:
            True se algo foi removido; False se ja nao estava la.
        """
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM obs_hidden_scenes WHERE scene_name = ?", (name,)
            )
            return cursor.rowcount > 0

    def clear(self) -> None:
        """Remove todas as cenas ocultas."""
        with get_connection() as conn:
            conn.execute("DELETE FROM obs_hidden_scenes")
