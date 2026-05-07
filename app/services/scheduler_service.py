"""Scheduler simples baseado em ``threading.Timer`` (stdlib).

Por que nao APScheduler? A versao 3.x tem problemas conhecidos no Python 3.14
(pre-release) e o overhead de uma dependencia externa nao se justifica para
o volume baixissimo de jobs deste app (algumas dezenas por dia, no maximo).

Cada job vira um ``threading.Timer`` independente. Os timers sao daemon
threads, entao morrem junto com o processo. Para sobreviver a reinicios,
``ShutdownService.rehydrate_pending`` re-registra os agendamentos do banco
no startup.
"""

import threading
from datetime import datetime
from typing import Callable


class SchedulerService:
    """Singleton com API minima de scheduling: start/shutdown/schedule/cancel."""

    _instance: "SchedulerService | None" = None

    def __new__(cls) -> "SchedulerService":
        """Garante uma unica instancia por processo (singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._timers: dict[str, threading.Timer] = {}
            cls._instance._lock = threading.RLock()
            cls._instance._running = False
        return cls._instance

    # ---------------------- Ciclo de vida ----------------------

    def start(self) -> None:
        """Marca o scheduler como ativo (no-op para Timer-based)."""
        with self._lock:
            self._running = True

    def shutdown(self) -> None:
        """Cancela todos os timers ativos e marca como parado."""
        with self._lock:
            self._running = False
            for timer in list(self._timers.values()):
                timer.cancel()
            self._timers.clear()

    @property
    def running(self) -> bool:
        """Retorna ``True`` enquanto o scheduler esta ativo."""
        with self._lock:
            return self._running

    # ---------------------- API publica ----------------------

    def schedule_at(
        self,
        job_id: str,
        run_at: datetime,
        callback: Callable[[], None],
    ) -> None:
        """Agenda ``callback`` para executar uma unica vez em ``run_at``.

        Substitui qualquer job existente com o mesmo ``job_id``.

        Args:
            job_id: Identificador unico (use o id do agendamento do banco).
            run_at: Datetime exato (naive, em hora local).
            callback: Funcao sem argumentos a ser executada.
        """
        with self._lock:
            existing = self._timers.pop(job_id, None)
            if existing is not None:
                existing.cancel()

            delay = (run_at - datetime.now()).total_seconds()

            def _wrapped() -> None:
                """Wrapper que tira o job do dict apos rodar."""
                try:
                    callback()
                finally:
                    with self._lock:
                        self._timers.pop(job_id, None)

            if delay <= 0:
                # Janela ja passou: dispara em uma thread separada para nao
                # bloquear o caller.
                threading.Thread(
                    target=_wrapped, name=f"scheduler-{job_id}", daemon=True
                ).start()
                return

            timer = threading.Timer(delay, _wrapped)
            timer.daemon = True
            timer.name = f"scheduler-{job_id}"
            self._timers[job_id] = timer
            timer.start()

    def cancel(self, job_id: str) -> bool:
        """Cancela um job agendado pelo ``job_id``.

        Args:
            job_id: Identificador do job.

        Returns:
            ``True`` se o job foi removido; ``False`` se nao existia.
        """
        with self._lock:
            timer = self._timers.pop(job_id, None)
            if timer is None:
                return False
            timer.cancel()
            return True

    def list_job_ids(self) -> list[str]:
        """Retorna a lista de ``job_id`` atualmente registrados (debug)."""
        with self._lock:
            return list(self._timers.keys())
