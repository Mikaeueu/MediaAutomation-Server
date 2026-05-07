"""Servico de alto nivel para agendar/cancelar desligamentos e suspensoes.

Orquestra:
  * o ``ShutdownScheduleRepository`` (persistencia);
  * o ``SchedulerService`` (gatilho temporal via APScheduler);
  * o ``SystemService`` (executor da acao).
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from app.models.shutdown_schedule import ShutdownSchedule
from app.repositories.shutdown_schedule_repository import (
    ShutdownScheduleRepository,
)
from app.services.scheduler_service import SchedulerService
from app.services.system_service import SystemService

if TYPE_CHECKING:
    pass


_JOB_PREFIX = "shutdown_"


class ShutdownService:
    """Regras de negocio para agendamentos de desligamento/suspensao."""

    def __init__(
        self,
        repository: ShutdownScheduleRepository | None = None,
        scheduler: SchedulerService | None = None,
        system: SystemService | None = None,
    ) -> None:
        """Inicializa o servico com dependencias injetaveis.

        Args:
            repository: CRUD de ``ShutdownSchedule``.
            scheduler: Wrapper do APScheduler (singleton).
            system: Executor de comandos do SO.
        """
        self._repo = repository or ShutdownScheduleRepository()
        self._scheduler = scheduler or SchedulerService()
        self._system = system or SystemService()

    # ---------------------- API publica ----------------------

    def list_schedules(self) -> list[ShutdownSchedule]:
        """Retorna todos os agendamentos (mais recentes primeiro)."""
        return self._repo.list_all()

    def schedule(
        self, scheduled_for: datetime, action: str = "shutdown"
    ) -> ShutdownSchedule:
        """Cria e ativa um novo agendamento.

        Args:
            scheduled_for: Quando disparar.
            action: ``"shutdown"`` ou ``"suspend"``.

        Returns:
            ``ShutdownSchedule`` persistido.

        Raises:
            ValueError: Se a data ja passou ou parametros invalidos.
        """
        if scheduled_for <= datetime.now():
            raise ValueError("A data agendada deve estar no futuro.")
        model = ShutdownSchedule(
            scheduled_for=scheduled_for,
            action=action,
            status="scheduled",
        )
        saved = self._repo.create(model)
        self._register_job(saved)
        return saved

    def postpone(self, schedule_id: int, minutes: int) -> ShutdownSchedule | None:
        """Adia um agendamento ativo em ``minutes`` minutos a partir de agora.

        Estrategia: cancela o agendamento atual e cria um novo com a mesma
        acao, com ``scheduled_for = now + minutes``. Mais simples e seguro
        que reescrever o registro existente (evita estados intermediarios).

        Args:
            schedule_id: Id do agendamento a adiar.
            minutes: Quantos minutos a partir de agora.

        Returns:
            O novo ``ShutdownSchedule`` criado, ou ``None`` se nao existir.

        Raises:
            ValueError: Se ``minutes <= 0``.
        """
        if minutes <= 0:
            raise ValueError("minutes deve ser maior que zero.")

        original = self._repo.get_by_id(schedule_id)
        if not original:
            return None

        # Cancela o atual (mantem historico com status 'cancelled').
        self._scheduler.cancel(self._job_id(schedule_id))
        self._repo.update_status(schedule_id, "cancelled")

        # Cria um novo agendamento adiado.
        new_when = datetime.now() + timedelta(minutes=minutes)
        return self.schedule(scheduled_for=new_when, action=original.action)

    def cancel(self, schedule_id: int) -> ShutdownSchedule | None:
        """Cancela um agendamento ativo.

        Args:
            schedule_id: Id do agendamento.

        Returns:
            O ``ShutdownSchedule`` atualizado, ou ``None`` se nao existir.
        """
        schedule = self._repo.get_by_id(schedule_id)
        if not schedule:
            return None
        self._scheduler.cancel(self._job_id(schedule_id))
        self._repo.update_status(schedule_id, "cancelled")
        return self._repo.get_by_id(schedule_id)

    def delete(self, schedule_id: int) -> bool:
        """Remove definitivamente um agendamento e seu job, se houver."""
        self._scheduler.cancel(self._job_id(schedule_id))
        return self._repo.delete(schedule_id)

    def rehydrate_pending(self) -> int:
        """Re-registra no scheduler todos os agendamentos ainda ativos.

        Chamado no startup da app para sobreviver a reinicios. Agendamentos
        cuja hora ja passou sao marcados como ``cancelled`` (perderam a janela).

        Returns:
            Numero de agendamentos efetivamente re-registrados.
        """
        count = 0
        now = datetime.now()
        for schedule in self._repo.list_active():
            if schedule.scheduled_for <= now:
                self._repo.update_status(schedule.id, "cancelled")
                continue
            self._register_job(schedule)
            count += 1
        return count

    # ---------------------- Helpers internos ----------------------

    @staticmethod
    def _job_id(schedule_id: int) -> str:
        """Gera o identificador do job no APScheduler."""
        return f"{_JOB_PREFIX}{schedule_id}"

    def _register_job(self, schedule: ShutdownSchedule) -> None:
        """Registra o callback no scheduler para o ``schedule`` informado."""
        if schedule.id is None:
            raise ValueError("schedule.id deve estar definido para registrar.")
        schedule_id = schedule.id  # captura por valor
        action = schedule.action

        def _run() -> None:
            """Callback executado no horario agendado.

            Marca o registro como ``executed`` e dispara a acao do SO.
            """
            try:
                self._repo.update_status(schedule_id, "executed")
            finally:
                self._system.execute(action)

        self._scheduler.schedule_at(
            job_id=self._job_id(schedule.id),
            run_at=schedule.scheduled_for,
            callback=_run,
        )
