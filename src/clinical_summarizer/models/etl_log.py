"""
Modelo de domínio para logs de execução ETL.

Representa um registro de execução do pipeline Pentaho.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID


@dataclass
class ETLLog:
    """
    Representa um log de execução do pipeline ETL.

    Attributes:
        id: ID único do registro.
        execution_id: UUID da execução.
        pipeline_name: Nome do pipeline executado.
        status: Status da execução (ex: 'completed', 'failed').
        filter_start_date: Data inicial do filtro.
        filter_end_date: Data final do filtro.
        filter_patient_id: ID do paciente filtrado (opcional).
        records_extracted: Registros extraídos.
        records_transformed: Registros transformados.
        records_loaded_patients: Pacientes carregados.
        records_loaded_visits: Visitas carregadas.
        started_at: Timestamp de início.
        completed_at: Timestamp de conclusão.
        duration_seconds: Duração em segundos.
        error_message: Mensagem de erro (se houver).
        error_step: Etapa onde ocorreu o erro (se houver).
    """

    execution_id: UUID
    pipeline_name: str
    status: str
    id: int | None = None
    filter_start_date: date | None = None
    filter_end_date: date | None = None
    filter_patient_id: int | None = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded_patients: int = 0
    records_loaded_visits: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = None
    error_message: str | None = None
    error_step: str | None = None

    @property
    def is_completed(self) -> bool:
        """Verifica se a execução foi concluída."""
        return self.status == "completed" and self.completed_at is not None

    @property
    def is_failed(self) -> bool:
        """Verifica se a execução falhou."""
        return self.status == "failed" or self.error_message is not None
