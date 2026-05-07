"""Ponto de entrada da aplicacao FastAPI.

Usa o pattern de application factory (``create_app``) para facilitar testes
isolados e composicao de instancias. O ciclo de vida (startup/shutdown) e
gerenciado por ``lifespan`` (forma moderna recomendada pelo FastAPI).
"""

import traceback
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import init_database
from app.routers import (
    auth,
    holyrics,
    live_generator,
    network,
    obs,
    pages,
    service_types,
    shutdown,
)
from app.services.auth_service import AuthService
from app.services.scheduler_service import SchedulerService
from app.services.shutdown_service import ShutdownService


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Hooks de startup e shutdown da aplicacao.

    No startup:
      * cria o schema do SQLite e aplica migracoes;
      * cria o usuario padrao se necessario;
      * inicia o scheduler em background;
      * re-hidrata os agendamentos pendentes do banco.

    No shutdown: para o scheduler graciosamente.
    """
    init_database()
    AuthService().ensure_default_user()

    # Log informativo sobre o backend de QR code disponivel.
    from app.services.network_service import _QR_BACKEND  # noqa: PLC0415
    if _QR_BACKEND:
        print(f"[startup] QR code backend ativo: {_QR_BACKEND}")
    else:
        print(
            "[startup] AVISO: nenhuma lib de QR code instalada. "
            "Rode 'pip install segno' no .venv para ativar o QR."
        )

    scheduler = SchedulerService()
    scheduler.start()
    ShutdownService(scheduler=scheduler).rehydrate_pending()

    try:
        yield
    finally:
        scheduler.shutdown()


def create_app() -> FastAPI:
    """Constroi e configura a instancia do FastAPI.

    Centralizar a construcao em uma factory facilita:
      * testes (criar instancias frescas por teste);
      * extensao (basta adicionar uma chamada ``include_router`` abaixo);
      * leitura (todo o setup do app fica em um unico lugar).

    Returns:
        Instancia configurada de FastAPI.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        description="Servidor de automacao para transmissoes ao vivo.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Arquivos estaticos (JS, CSS, imagens) servidos pelo proprio FastAPI.
    application.mount("/static", StaticFiles(directory="app/static"), name="static")

    # Handler global: captura QUALQUER exception nao tratada, printa
    # traceback no stdout (capturado pelo launcher log) E devolve no
    # body da response 500 - assim da pra ver o erro real no navegador
    # quando o launcher nao mostra log nenhum.
    @application.exception_handler(Exception)
    async def _global_exc_handler(request: Request, exc: Exception) -> PlainTextResponse:
        """Captura qualquer exception nao tratada e expoe pra debug."""
        tb = traceback.format_exc()
        msg = (
            f"[ERRO] {request.method} {request.url.path}\n"
            f"{type(exc).__name__}: {exc}\n\n{tb}"
        )
        print(msg, flush=True)
        return PlainTextResponse(msg, status_code=500)

    # Cada router e um "blueprint" tematico.
    application.include_router(pages.router)
    application.include_router(auth.router)
    application.include_router(service_types.router)
    application.include_router(live_generator.router)
    application.include_router(network.router)
    application.include_router(shutdown.router)
    application.include_router(obs.router)
    application.include_router(holyrics.router)

    return application


app = create_app()
