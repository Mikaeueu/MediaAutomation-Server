"""Gerencia o servidor uvicorn rodando IN-PROCESS via thread.

Antes usavamos ``subprocess.Popen`` que re-executava o proprio exe em
``--server-mode``. Mas isso quebrava no PyInstaller frozen mode (subprocess
crashava antes de qualquer print), sem dar pra debugar.

Agora rodamos ``uvicorn.Server`` direto numa thread daemon, no mesmo
processo do launcher Qt. Vantagens:
  * sem subprocess - sem chance de quebrar em sys.executable;
  * logs vao direto pro stderr do launcher (visiveis no log);
  * shutdown gracioso via ``server.should_exit = True``;
  * tracebacks aparecem completos.
"""

from __future__ import annotations

import os
import threading
import traceback
from collections.abc import Callable
from pathlib import Path


class ServerRunner:
    """Controla o ciclo de vida do uvicorn rodando in-process."""

    STATE_STOPPED = "stopped"
    STATE_STARTING = "starting"
    STATE_RUNNING = "running"
    STATE_STOPPING = "stopping"
    STATE_ERROR = "error"

    def __init__(
        self,
        project_root: Path,
        host: str = "0.0.0.0",
        port: int = 8000,
    ) -> None:
        """Inicializa o runner.

        Args:
            project_root: Pasta raiz do projeto (onde fica ``app/``).
            host: Host do uvicorn.
            port: Porta do uvicorn.
        """
        self._project_root = Path(project_root).resolve()
        self._host = host
        self._port = port
        self._server = None  # uvicorn.Server lazy
        self._thread: threading.Thread | None = None
        self._state = self.STATE_STOPPED
        self._on_log: Callable[[str], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None
        self._chdir_done = False

    # ---------------------- Eventos ----------------------

    def set_log_handler(self, handler: Callable[[str], None]) -> None:
        """Registra um callback que recebe cada linha de log."""
        self._on_log = handler

    def set_state_handler(self, handler: Callable[[str], None]) -> None:
        """Registra um callback chamado a cada mudanca de estado."""
        self._on_state_change = handler

    # ---------------------- API publica ----------------------

    @property
    def state(self) -> str:
        """Estado atual (stopped/starting/running/stopping/error)."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Indica se a thread do uvicorn esta ativa."""
        return self._thread is not None and self._thread.is_alive()

    @property
    def host(self) -> str:
        """Host configurado."""
        return self._host

    @property
    def port(self) -> int:
        """Porta configurada."""
        return self._port

    def start(self) -> None:
        """Inicia o uvicorn em uma thread daemon."""
        if self.is_running:
            return
        self._set_state(self.STATE_STARTING)
        self._emit_log(f"[runner] iniciando uvicorn em {self._host}:{self._port}")

        # chdir uma vez, pra Jinja2Templates(directory='app/templates') achar.
        if not self._chdir_done:
            try:
                os.chdir(self._project_root)
                self._chdir_done = True
                self._emit_log(f"[runner] cwd = {os.getcwd()}")
            except Exception as exc:  # noqa: BLE001
                self._emit_log(f"[runner] aviso: chdir falhou: {exc}")

        self._thread = threading.Thread(
            target=self._run_uvicorn,
            name="uvicorn-server",
            daemon=True,
        )
        self._thread.start()

        # Marca como RUNNING apos pequena espera (em outra thread, pra nao
        # bloquear o GUI).
        threading.Thread(target=self._mark_running, daemon=True).start()

    def stop(self, timeout: float = 5.0) -> None:
        """Para o servidor de forma graciosa via ``server.should_exit``."""
        if not self.is_running or self._server is None:
            self._set_state(self.STATE_STOPPED)
            return
        self._set_state(self.STATE_STOPPING)
        self._emit_log("[runner] solicitando shutdown gracioso...")
        try:
            self._server.should_exit = True
        except Exception:  # noqa: BLE001
            pass
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                self._emit_log("[runner] timeout no shutdown - thread daemon morrera com o processo")
        self._thread = None
        self._server = None
        self._set_state(self.STATE_STOPPED)

    # ---------------------- Internos ----------------------

    def _crash_log(self, msg: str) -> None:
        """Grava msg num arquivo persistente (independente da UI thread)."""
        try:
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            p = Path(base) / "MediaAutomationServer"
            p.mkdir(parents=True, exist_ok=True)
            with open(p / "server-crash.log", "a", encoding="utf-8") as fp:
                fp.write(msg + "\n")
        except Exception:
            pass

    def _run_uvicorn(self) -> None:
        """Carrega ``app.main:app`` e roda ``uvicorn.Server.run()`` aqui."""
        # Limpa crash log anterior pra so ter o mais recente.
        try:
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            (Path(base) / "MediaAutomationServer" / "server-crash.log").unlink(
                missing_ok=True
            )
        except Exception:
            pass

        self._crash_log("=== run_uvicorn START ===")
        self._crash_log(f"cwd={os.getcwd()}")

        try:
            self._crash_log("step: import uvicorn")
            import uvicorn  # noqa: PLC0415
            self._crash_log("step: import uvicorn OK")

            self._crash_log("step: from app.main import app")
            from app.main import app  # noqa: PLC0415
            self._crash_log("step: from app.main import app OK")

            self._crash_log("step: uvicorn.Config")
            # log_config=None: uvicorn nao tenta criar handlers de logging
            # que dependem de sys.stdout/stderr (que sao None quando o exe
            # e empacotado com console=False).
            config = uvicorn.Config(
                app,
                host=self._host,
                port=self._port,
                log_level="info",
                access_log=False,
                log_config=None,
            )
            self._crash_log("step: uvicorn.Server")
            self._server = uvicorn.Server(config)
            self._emit_log("[runner] uvicorn.Server.run() iniciando event loop...")
            self._crash_log("step: server.run()")
            self._server.run()
            self._crash_log("step: server.run() retornou")
            self._emit_log("[runner] uvicorn encerrou normalmente")
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            msg = f"[runner] CRASH: {type(exc).__name__}: {exc}\n{tb}"
            self._emit_log(msg)
            self._crash_log(msg)
            self._set_state(self.STATE_ERROR)
            return
        # Quando uvicorn sai sem exception, marca como STOPPED.
        if self._state in (self.STATE_RUNNING, self.STATE_STARTING):
            self._set_state(self.STATE_STOPPED)

    def _mark_running(self) -> None:
        """Marca como RUNNING se a thread sobreviver os primeiros 2s."""
        import time
        time.sleep(2.0)
        if self.is_running and self._state == self.STATE_STARTING:
            self._set_state(self.STATE_RUNNING)
            self._emit_log("[runner] servidor confirmado RUNNING")

    def _emit_log(self, line: str) -> None:
        """Emite uma linha de log pelo callback se houver."""
        if self._on_log:
            try:
                self._on_log(line)
            except Exception:  # noqa: BLE001
                pass

    def _set_state(self, new_state: str) -> None:
        """Troca o estado e dispara o callback."""
        self._state = new_state
        if self._on_state_change:
            try:
                self._on_state_change(new_state)
            except Exception:  # noqa: BLE001
                pass
