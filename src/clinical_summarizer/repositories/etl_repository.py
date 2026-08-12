"""
Repositório para acesso aos logs de ETL.

Fornece métodos para consultar a tabela etl_logs.
"""

import logging
from datetime import datetime
from uuid import UUID

from clinical_summarizer.models.etl_log import ETLLog
from clinical_summarizer.repositories.base import get_connection

logger = logging.getLogger(__name__)


class ETLRepository:
    """Repositório para operações com logs de ETL."""

    def get_latest_completed(self, since: datetime) -> ETLLog | None:
        """
        Busca o log mais recente completado após uma data/hora.

        Args:
            since: Buscar logs completados após este timestamp.

        Returns:
            ETLLog se encontrado, None caso contrário.
        """
        query = """
            SELECT
                id, execution_id, pipeline_name, status,
                filter_start_date, filter_end_date, filter_patient_id,
                records_extracted, records_transformed,
                records_loaded_patients, records_loaded_visits,
                started_at, completed_at, duration_seconds,
                error_message, error_step
            FROM etl_logs
            WHERE completed_at >= %s
            ORDER BY completed_at DESC
            LIMIT 1
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (since,))
                row = cur.fetchone()

                if not row:
                    return None

                return ETLLog(
                    id=row[0],
                    execution_id=row[1],
                    pipeline_name=row[2],
                    status=row[3],
                    filter_start_date=row[4],
                    filter_end_date=row[5],
                    filter_patient_id=row[6],
                    records_extracted=row[7] or 0,
                    records_transformed=row[8] or 0,
                    records_loaded_patients=row[9] or 0,
                    records_loaded_visits=row[10] or 0,
                    started_at=row[11],
                    completed_at=row[12],
                    duration_seconds=row[13],
                    error_message=row[14],
                    error_step=row[15],
                )

    def get_by_execution_id(self, execution_id: UUID) -> ETLLog | None:
        """
        Busca um log pelo execution_id.

        Args:
            execution_id: UUID da execução.

        Returns:
            ETLLog se encontrado, None caso contrário.
        """
        query = """
            SELECT
                id, execution_id, pipeline_name, status,
                filter_start_date, filter_end_date, filter_patient_id,
                records_extracted, records_transformed,
                records_loaded_patients, records_loaded_visits,
                started_at, completed_at, duration_seconds,
                error_message, error_step
            FROM etl_logs
            WHERE execution_id = %s
        """

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (execution_id,))
                row = cur.fetchone()

                if not row:
                    return None

                return ETLLog(
                    id=row[0],
                    execution_id=row[1],
                    pipeline_name=row[2],
                    status=row[3],
                    filter_start_date=row[4],
                    filter_end_date=row[5],
                    filter_patient_id=row[6],
                    records_extracted=row[7] or 0,
                    records_transformed=row[8] or 0,
                    records_loaded_patients=row[9] or 0,
                    records_loaded_visits=row[10] or 0,
                    started_at=row[11],
                    completed_at=row[12],
                    duration_seconds=row[13],
                    error_message=row[14],
                    error_step=row[15],
                )


_repository: ETLRepository | None = None


def get_etl_repository() -> ETLRepository:
    """Factory function para obter instância do repositório."""
    global _repository
    if _repository is None:
        _repository = ETLRepository()
    return _repository
