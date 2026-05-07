"""Conexao SQLite, schema inicial e migracoes simples.

Mantemos o banco propositalmente simples (stdlib ``sqlite3``) porque o app
roda em uma unica maquina, com baixissima concorrencia. Usar SQLAlchemy aqui
seria over-engineering. As DDLs ficam todas explicitas em ``SCHEMA_STATEMENTS``
e a funcao ``init_database`` e idempotente.

Pequenas alteracoes de schema sao tratadas em ``MIGRATIONS`` como ALTER TABLE
encapsulados em try/except — suficiente para a escala deste projeto.
"""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT    NOT NULL UNIQUE,
        password_hash   TEXT    NOT NULL,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS service_types (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        name                 TEXT    NOT NULL UNIQUE,
        title_template       TEXT    NOT NULL,
        description_template TEXT    NOT NULL DEFAULT '',
        suggested_weekday    INTEGER,
        created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
        updated_at           TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shutdown_schedules (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        scheduled_for TEXT    NOT NULL,
        action        TEXT    NOT NULL DEFAULT 'shutdown',
        status        TEXT    NOT NULL DEFAULT 'scheduled',
        created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obs_config (
        id           INTEGER PRIMARY KEY CHECK (id = 1),
        host         TEXT    NOT NULL DEFAULT 'localhost',
        port         INTEGER NOT NULL DEFAULT 4455,
        password     TEXT    NOT NULL DEFAULT '',
        auto_connect INTEGER NOT NULL DEFAULT 1,
        updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS obs_hidden_scenes (
        scene_name TEXT    PRIMARY KEY,
        hidden_at  TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS holyrics_config (
        id         INTEGER PRIMARY KEY CHECK (id = 1),
        host       TEXT    NOT NULL DEFAULT 'localhost',
        port       INTEGER NOT NULL DEFAULT 8091,
        token      TEXT    NOT NULL DEFAULT '',
        updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS holyrics_recent_verses (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        version    TEXT    NOT NULL,
        book       INTEGER NOT NULL,
        chapter    INTEGER NOT NULL,
        verse      INTEGER NOT NULL,
        label      TEXT    NOT NULL,
        used_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    )
    """,
)


# Migracoes simples idempotentes: cada entry e um ALTER TABLE que pode falhar
# silenciosamente caso a coluna ja exista. Adequado para a escala do projeto.
MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE shutdown_schedules ADD COLUMN action TEXT NOT NULL DEFAULT 'shutdown'",
    "ALTER TABLE shutdown_schedules ADD COLUMN status TEXT NOT NULL DEFAULT 'scheduled'",
)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield uma conexao SQLite com transacao gerenciada.

    Comita ao sair sem erros, faz rollback em excecao e fecha sempre.
    O ``row_factory`` e setado para ``sqlite3.Row``, permitindo acesso por
    nome (``row['campo']``).

    Yields:
        Conexao SQLite ativa.

    Example:
        >>> with get_connection() as conn:
        ...     row = conn.execute("SELECT 1 AS x").fetchone()
        ...     print(row['x'])
    """
    settings = get_settings()
    conn = sqlite3.connect(settings.database_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database() -> None:
    """Cria as tabelas do schema e aplica migracoes pendentes.

    Funcao idempotente: pode ser chamada em todo startup sem efeitos colaterais.
    """
    with get_connection() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                # Coluna ja existe ou alteracao ja aplicada: ignorar.
                pass
