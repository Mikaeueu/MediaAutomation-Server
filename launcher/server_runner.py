"""Gerencia o subprocess do servidor uvicorn.

Encapsula start/stop do uvicorn pra que o launcher trate o servidor como
um servico controlavel sem precisar lidar com subprocess no GUI thread.
"""

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path


class ServerRunner:
    """Controla o ciclo de vida do servidor uvicorn como subprocess.

    Use ``start()`` e ``stop()`` para gerenciar. Eventos ``on_log`` e
    ``on_state_change`` permitem o GUI reagir em tempo real.
    """

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
        self._process: subprocess.Popen | None = None
        self._reader_thread: threading.Thread | None = None
        self._state = self.STATE_STOPPED
        self._on_log: Callable[[str], None] | None = None
        self._on_state_change: Callable[[str], None] | None = None

    # ---------------------- Eventos ----------------------

    def set_log_handler(self, handler: Callable[[str], None]) -> None:
        """Registra um callback que recebe cada linha de log do uvicorn."""
        self._on_log = handler

    def set_state_handler(self, handler: Callable[[str], None]) -> None:
        """Registra um callback chamado a cada mudanca de estado."""
        self._on_state_change = handler

    # ---------------------- API publica ----------------------

    @property
    def state(self) -> str:
        """Estado atual do servidor (stopped/starting/running/stopping/error)."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Indica se ha um processo ativo."""
        return self._process is not None and self._process.poll() is None

    @property
    def host(self) -> str:
        """Host configurado."""
        return self._host

    @property
    def port(self) -> int:
        """Porta configurada."""
        return self._port

    def start(self) -> None:
        """Inicia o servidor uvicorn em subprocess."""
        if self.is_running:
            return
        self._set_state(self.STATE_STARTING)

        cmd = self._build_command()
        env = os.environ.copy()
        # Desabilita buffering pra logs aparecerem em tempo real.
        env["PYTHONUNBUFFERED"] = "1"

        creationflags = 0
        if sys.platform.startswith("win"):
            # Esconde a janela do console no Windows.
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=str(self._project_root),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                bufsize=1,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            self._emit_log(f"[erro] {exc}")
            self._set_state(self.STATE_ERROR)
            return

        # Lê stdout em thread pra nao bloquear o GUI.
        self._reader_thread = threading.Thread(
            target=self._read_output, daemon=True, name="server-log-reader"
        )
        self._reader_thread.start()

        # Aguarda alguns instantes em outra thread pra confirmar startup.
        threading.Thread(target=self._wait_running, daemon=True).start()

    def stop(self, timeout: float = 5.0) -> None:
        """Para o servidor de forma graciosa, com fallback para kill."""
        if not self.is_running:
            return
        self._set_state(self.STATE_STOPPING)

        try:
            if sys.platform.startswith("win"):
                # CTRL+BREAK seria ideal, mas como criamos sem console,
                # vamos direto pro terminate.
                self._process.terminate()
            else:
                self._process.send_signal(signal.SIGTERM)
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._emit_log("[warn] timeout ao parar, forcando kill...")
            self._process.kill()
            self._process.wait()
        finally:
            self._process = None
            self._set_state(self.STATE_STOPPED)

    # ---------------------- Helpers internos ----------------------

    def _build_command(self) -> list[str]:
        """Monta o comando do subprocess de acordo com o ambiente.

        Em modo **frozen** (empacotado pelo PyInstaller), ``sys.executable``
        aponta pro proprio launcher .exe. Chamar ele com ``-m uvicorn``
        nao funciona (PyInstaller nao expoe modulos via -m). Em vez disso,
        chamamos o proprio exe com a flag ``--server-mode``, que faz o
        ``launcher.main`` iniciar apenas o uvicorn (sem GUI).

        Em modo dev (rodando via ``python -m launcher.main``), usamos o
        Python do .venv com ``-m uvicorn`` direto.

        Returns:
            Lista de argumentos pro ``subprocess.Popen``.
        """
        if getattr(sys, "frozen", False):
            # Mesmo exe, modo server: re-executa em --server-mode.
            return [
                sys.executable,
                "--server-mode",
                "--host", self._host,
                "--port", str(self._port),
            ]

        venv = self._project_root / ".venv" / "Scripts" / "python.exe"
        python = str(venv) if venv.exists() else sys.executable
        return [
            python,
            "-m", "uvicorn",
            "app.main:app",
            "--host", self._host,
            "--port", str(self._port),
        ]

    def _read_output(self) -> None:
        """Le stdout do subprocess linha a linha e emite via callback."""
        if self._process is None or self._process.stdout is None:
            return
        for line in self._process.stdout:
            self._emit_log(line.rstrip())
        # Quando o stream fecha, o processo encerrou.
        if self._state in (self.STATE_RUNNING, self.STATE_STARTING):
            self._set_state(self.STATE_STOPPED)
            self._process = None

    def _wait_running(self) -> None:
        """Confirma que o servidor subiu (heuristica: 2.5s sem cair)."""
        import time

        time.sleep(2.5)
        if self.is_running and self._state == self.STATE_STARTING:
            self._set_state(self.STATE_RUNNING)

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
