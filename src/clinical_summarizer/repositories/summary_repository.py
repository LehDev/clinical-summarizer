"""
Repositório para acesso a dados de Resumos Clínicos.

Encapsula todas as queries relacionadas à tabela summaries.
"""

import logging

from psycopg.rows import dict_row

from clinical_summarizer.models import Summary
from clinical_summarizer.repositories.base import get_connection

logger = logging.getLogger(__name__)


class SummaryRepository:
    """
    Repositório para operações na tabela summaries.

    Todos os métodos usam connection pool via get_connection().
    """

    def create(self, summary: Summary) -> Summary:
        """
        Insere um novo resumo no banco de dados.

        Args:
            summary: Objeto Summary a ser inserido.

        Returns:
            Objeto Summary com id e summary_id preenchidos pelo banco.
        """
        query = """
            INSERT INTO summaries (
                patient_id,
                visit_ids,
                filter_start_date,
                filter_end_date,
                summary_text,
                llm_model,
                llm_prompt_tokens,
                llm_completion_tokens,
                llm_total_tokens,
                llm_temperature,
                generation_duration_ms,
                status,
                error_message
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING
                id,
                summary_id,
                patient_id,
                visit_ids,
                filter_start_date,
                filter_end_date,
                summary_text,
                llm_model,
                llm_prompt_tokens,
                llm_completion_tokens,
                llm_total_tokens,
                llm_temperature,
                generation_duration_ms,
                status,
                error_message,
                created_at
        """

        params = (
            summary.patient_id,
            summary.visit_ids,
            summary.filter_start_date,
            summary.filter_end_date,
            summary.summary_text,
            summary.llm_model,
            summary.llm_prompt_tokens,
            summary.llm_completion_tokens,
            summary.llm_total_tokens,
            summary.llm_temperature,
            summary.generation_duration_ms,
            summary.status,
            summary.error_message,
        )

        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                row = cur.fetchone()
            conn.commit()

        logger.info(
            "Resumo criado: summary_id=%s, patient_id=%s",
            row["summary_id"],
            row["patient_id"][:8],
        )

        return self._row_to_summary(row)

    def _row_to_summary(self, row: dict) -> Summary:
        """Converte uma linha do banco para objeto Summary."""
        return Summary(
            id=row["id"],
            summary_id=str(row["summary_id"]),
            patient_id=row["patient_id"],
            visit_ids=row["visit_ids"],
            filter_start_date=row["filter_start_date"],
            filter_end_date=row["filter_end_date"],
            summary_text=row["summary_text"],
            llm_model=row["llm_model"],
            llm_prompt_tokens=row["llm_prompt_tokens"],
            llm_completion_tokens=row["llm_completion_tokens"],
            llm_total_tokens=row["llm_total_tokens"],
            llm_temperature=row["llm_temperature"],
            generation_duration_ms=row["generation_duration_ms"],
            status=row["status"],
            error_message=row["error_message"],
            created_at=row["created_at"],
        )


def get_summary_repository() -> SummaryRepository:
    """Factory function para obter instância do repositório."""
    return SummaryRepository()
