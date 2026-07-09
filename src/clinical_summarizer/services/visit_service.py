"""
Serviço de Visitas - camada de orquestração.

Coordena chamadas aos repositórios e aplica regras de negócio.
Não conhece HTTP nem detalhes de banco - usa abstrações das outras camadas.
"""

import logging
from datetime import date

from clinical_summarizer.exceptions import InvalidDateRangeError, PatientNotFoundError
from clinical_summarizer.models import Visit
from clinical_summarizer.utils import hash_id
from clinical_summarizer.repositories import (
    PatientRepository,
    VisitRepository,
    get_patient_repository,
    get_visit_repository,
)

logger = logging.getLogger(__name__)


class VisitService:
    """
    Serviço para operações relacionadas a visitas clínicas.

    Responsabilidades:
    - Validar regras de negócio
    - Orquestrar chamadas aos repositórios
    - Aplicar transformações nos dados (futuro: limpeza de encoding)
    """

    def __init__(
        self,
        visit_repository: VisitRepository | None = None,
        patient_repository: PatientRepository | None = None,
    ):
        """
        Inicializa o serviço com dependências injetadas.

        Args:
            visit_repository: Repositório de visitas. Se None, usa default.
            patient_repository: Repositório de pacientes. Se None, usa default.

        A injeção de dependências permite:
        1. Testar com mocks sem acessar banco real
        2. Substituir implementações facilmente
        """
        self._visit_repo = visit_repository or get_visit_repository()
        self._patient_repo = patient_repository or get_patient_repository()

    def get_patient_visits(
        self,
        patient_id: str,
        start_date: date,
        end_date: date,
    ) -> list[Visit]:
        """
        Busca visitas de um paciente em um período.

        Valida:
        - Se o paciente existe (lança PatientNotFoundError se não)
        - Se o intervalo de datas é válido (end >= start)

        Args:
            patient_id: ID original do paciente (será convertido para hash SHA-256).
            start_date: Data inicial do período.
            end_date: Data final do período.

        Returns:
            Lista de visitas no período, ordenadas por data decrescente.

        Raises:
            PatientNotFoundError: Se o paciente não existir.
            InvalidDateRangeError: Se start_date > end_date.
        """
        # Validação de regra de negócio: intervalo de datas
        if start_date > end_date:
            logger.warning(
                "Intervalo inválido: start=%s > end=%s",
                start_date,
                end_date,
            )
            raise InvalidDateRangeError(
                f"Data inicial ({start_date}) não pode ser posterior "
                f"à data final ({end_date})"
            )

        # Converte ID original para hash SHA-256 (mesmo formato do ETL)
        patient_id_hash = hash_id(patient_id)

        # Verifica se paciente existe antes de buscar visitas
        if not self._patient_repo.exists(patient_id_hash):
            raise PatientNotFoundError(patient_id)

        visits = self._visit_repo.get_by_patient_and_date_range(
            patient_id=patient_id_hash,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(
            "Retornando %d visitas para paciente %s",
            len(visits),
            patient_id_hash[:8],  # Log apenas início do hash por segurança
        )

        return visits

    def get_visit_details(self, visit_id: str) -> Visit:
        """
        Busca detalhes completos de uma visita.

        Args:
            visit_id: ID original da visita (será convertido para hash SHA-256).

        Returns:
            Objeto Visit com todos os dados.

        Raises:
            VisitNotFoundError: Se a visita não existir.
        """
        # Converte ID original para hash SHA-256 (mesmo formato do ETL)
        visit_id_hash = hash_id(visit_id)
        return self._visit_repo.get_by_id(visit_id_hash)


def get_visit_service() -> VisitService:
    """
    Factory function para obter instância do serviço.

    Usada para dependency injection no FastAPI.
    """
    return VisitService()
