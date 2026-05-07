"""Configuracao da aplicacao via Pydantic Settings.

Centraliza todas as variaveis de ambiente em um unico ponto, com tipos
explicitos e valores padrao seguros para desenvolvimento. Em producao,
sobrescreva via ``.env`` ou variaveis de ambiente reais.
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _frozen_db_path() -> Path:
    """Em frozen mode, redireciona o SQLite pra %LOCALAPPDATA%.

    A pasta ``_MEIPASS`` do PyInstaller e apagada quando o exe fecha,
    entao gravar o banco la perderia dados a cada execucao.
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(base) / "MediaAutomationServer" / "data" / "app.db"


class Settings(BaseSettings):
    """Configuracoes carregadas de variaveis de ambiente e do arquivo .env.

    Adicione novas configuracoes aqui e elas estarao disponiveis em todo o
    projeto via ``get_settings()``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------- Servidor HTTP -------
    app_name: str = "MediaAutomationServer"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # ------- Seguranca -------
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 720
    algorithm: str = "HS256"

    # ------- Banco de dados -------
    database_path: str = "./data/app.db"

    # ------- Usuario padrao (criado se a tabela estiver vazia) -------
    default_user: str = "midiadm"
    default_password: str = "123321"

    # ------- OBS WebSocket (configurado em fases futuras) -------
    obs_host: str = "localhost"
    obs_port: int = 4455
    obs_password: str = ""

    # ------- Supabase (auto-update do launcher) -------
    # URL do projeto, sem barra no fim. Ex: https://xxxxx.supabase.co
    supabase_url: str = ""
    # Chave "anon public" do projeto (e segura distribuir junto do exe).
    supabase_anon_key: str = ""

    @property
    def database_file(self) -> Path:
        """Caminho absoluto do SQLite, com fallback p/ %LOCALAPPDATA% em frozen.

        Em modo dev usa o ``database_path`` (default ``./data/app.db``).
        Em modo frozen (PyInstaller exe) e ``database_path`` nao foi
        sobrescrito via env, redireciona pra ``%LOCALAPPDATA%`` pra
        nao perder dados (``_MEIPASS`` e apagado ao fechar o exe).
        """
        if getattr(sys, "frozen", False) and self.database_path == "./data/app.db":
            path = _frozen_db_path()
        else:
            path = Path(self.database_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retorna uma instancia unica e cacheada de ``Settings``.

    O ``lru_cache`` garante que o arquivo .env seja lido apenas uma vez por
    processo, evitando IO redundante em cada dependencia injetada.

    Returns:
        Instancia singleton de Settings.
    """
    return Settings()
