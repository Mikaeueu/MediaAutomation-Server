"""Servico de geracao de titulos e descricoes a partir de templates.

Renderiza placeholders como ``{data}``, ``{dia_semana}`` etc. usando a data
atual (ou injetada, util para testes).
"""

from datetime import datetime
from typing import Any

from app.models.service_type import ServiceType
from app.repositories.service_type_repository import ServiceTypeRepository


WEEKDAYS_PT: tuple[str, ...] = (
    "segunda-feira",
    "terca-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sabado",
    "domingo",
)


MONTHS_PT: tuple[str, ...] = (
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


class TitleGeneratorService:
    """Constroi titulo e descricao a partir de um ``ServiceType``."""

    def __init__(self, repository: ServiceTypeRepository | None = None) -> None:
        """Inicializa o servico com um repositorio opcional.

        Args:
            repository: Repositorio injetado (default: novo ``ServiceTypeRepository``).
        """
        self._repo = repository or ServiceTypeRepository()

    def suggest_for_today(self) -> ServiceType | None:
        """Retorna o tipo de culto sugerido para o dia atual da semana.

        Returns:
            Tipo sugerido ou ``None`` se nao houver mapeamento configurado.
        """
        weekday = datetime.now().weekday()
        return self._repo.get_suggested_for_weekday(weekday)

    def generate(
        self,
        service_type_id: int,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Renderiza titulo e descricao para um tipo de culto.

        Args:
            service_type_id: Chave primaria do tipo de culto.
            now: Datetime opcional para usar como "agora" (util em testes).

        Returns:
            Dicionario com chaves ``title``, ``description``, ``service_type``
            e ``generated_at``.

        Raises:
            ValueError: Se o tipo de culto nao existir.
        """
        service = self._repo.get_by_id(service_type_id)
        if not service:
            raise ValueError(f"Tipo de culto {service_type_id} nao encontrado.")
        moment = now or datetime.now()
        context = self._build_context(moment)
        return {
            "title": service.title_template.format(**context),
            "description": service.description_template.format(**context),
            "service_type": service.to_dict(),
            "generated_at": moment.isoformat(),
        }

    @staticmethod
    def _build_context(moment: datetime) -> dict[str, Any]:
        """Monta o dicionario de variaveis disponiveis para os templates.

        Args:
            moment: Datetime base para os calculos.

        Returns:
            Dicionario com placeholders disponiveis no ``str.format``.
        """
        return {
            "data": moment.strftime("%d/%m/%Y"),
            "data_extenso": f"{moment.day} de {MONTHS_PT[moment.month - 1]} de {moment.year}",
            "hora": moment.strftime("%H:%M"),
            "dia_semana": WEEKDAYS_PT[moment.weekday()],
            "ano": moment.year,
            "mes": moment.month,
            "dia": moment.day,
        }
