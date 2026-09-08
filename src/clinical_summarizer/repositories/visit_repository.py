"""
Repositório para acesso a dados de Visitas.

Encapsula todas as queries relacionadas à tabela visits.
Não contém lógica de negócio - apenas acesso a dados.
"""

import logging
from datetime import date

from psycopg.rows import dict_row

from clinical_summarizer.exceptions import VisitNotFoundError
from clinical_summarizer.models import Visit
from clinical_summarizer.repositories.base import get_connection

logger = logging.getLogger(__name__)


class VisitRepository:
    """
    Repositório para operações de leitura na tabela visits.

    Todos os métodos usam connection pool via get_connection().
    Queries usam parâmetros preparados para evitar SQL injection.
    """

    def get_by_id(self, visit_id: str) -> Visit:
        """
        Busca uma visita específica pelo ID.

        Args:
            visit_id: Hash SHA-256 do ID da visita.

        Returns:
            Objeto Visit com todos os dados.

        Raises:
            VisitNotFoundError: Se a visita não existir.
        """
        query = """
            SELECT
                visit_id,
                patient_id,
                visit_date,
                cid_codes,
                cid_names,
                clinical_evolutions,
                sign_symptoms,
                evaluations_raw,
                evaluation_types,
                created_at
            FROM visits
            WHERE visit_id = %s
        """

        with get_connection() as conn:
            # dict_row retorna dicionários em vez de tuplas
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (visit_id,))
                row = cur.fetchone()

        if row is None:
            logger.warning("Visita não encontrada: %s", visit_id)
            raise VisitNotFoundError(visit_id)

        return self._row_to_visit(row)

    def get_by_patient_and_date_range(
        self,
        patient_id: str,
        start_date: date,
        end_date: date,
    ) -> list[Visit]:
        """
        Busca todas as visitas de um paciente em um período.

        Args:
            patient_id: Hash SHA-256 do ID do paciente.
            start_date: Data inicial (inclusiva).
            end_date: Data final (inclusiva).

        Returns:
            Lista de objetos Visit ordenados por data (mais recente primeiro).
            Lista vazia se não houver visitas no período.

        Nota:
            Este método NÃO verifica se o paciente existe.
            Retorna lista vazia tanto para paciente inexistente
            quanto para paciente sem visitas no período.
            A verificação de existência é responsabilidade da camada de serviço.
        """
        query = """
            SELECT
                visit_id,
                patient_id,
                visit_date,
                cid_codes,
                cid_names,
                clinical_evolutions,
                sign_symptoms,
                evaluations_raw,
                evaluation_types,
                created_at
            FROM visits
            WHERE patient_id = %s
              AND visit_date >= %s
              AND visit_date <= %s
            ORDER BY visit_date DESC
        """

        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (patient_id, start_date, end_date))
            rows = cur.fetchall()

        logger.debug(
            "Encontradas %d visitas para paciente %s entre %s e %s",
            len(rows),
            patient_id,
            start_date,
            end_date,
        )

        return [self._row_to_visit(row) for row in rows]

    def _row_to_visit(self, row: dict) -> Visit:
        """
        Converte uma linha do banco para objeto Visit.

        Método interno para centralizar a conversão e evitar duplicação.
        """
        return Visit(
            visit_id=row["visit_id"],
            patient_id=row["patient_id"],
            visit_date=row["visit_date"],
            cid_codes=row["cid_codes"],
            cid_names=row["cid_names"],
            clinical_evolutions=row["clinical_evolutions"],
            sign_symptoms=row["sign_symptoms"],
            evaluations_raw=row["evaluations_raw"],
            evaluation_types=row["evaluation_types"],
            created_at=row["created_at"],
        )


def get_visit_repository() -> VisitRepository:
    """
    Factory function para obter instância do repositório.

    Usada para dependency injection no FastAPI.
    Retorna nova instância a cada chamada (stateless).
    """
    return VisitRepository()
