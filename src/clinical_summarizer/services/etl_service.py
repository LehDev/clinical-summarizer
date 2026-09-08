"""
Serviço de orquestração ETL.

Executa o pipeline Pentaho e monitora sua conclusão.
"""

import logging
import subprocess
import time
from dataclasses import dataclass
from datetime import date, datetime

from clinical_summarizer.models.etl_log import ETLLog
from clinical_summarizer.repositories.etl_repository import (
    ETLRepository,
    get_etl_repository,
)

logger = logging.getLogger(__name__)

# Configurações do Pentaho
KITCHEN_PATH = "/home/salvus/pentaho/data-integration/kitchen.sh"
JOB_PATH = "/home/salvus/pentaho/data-integration/ETL_Pipeline.kjb"

# Configurações de polling
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 300  # 5 minutos


@dataclass
class ETLResult:
    """Resultado da execução do ETL."""

    success: bool
    message: str
    etl_log: ETLLog | None = None
    duration_seconds: int = 0


class ETLService:
    """
    Serviço para execução e monitoramento do pipeline ETL.

    Responsabilidades:
    1. Executar o job Pentaho via kitchen.sh
    2. Fazer polling na tabela etl_logs
    3. Retornar resultado da execução
    """

    def __init__(self, etl_repository: ETLRepository | None = None):
        self._etl_repo = etl_repository or get_etl_repository()

    def run_pipeline(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        patient_id: int | None = None,
    ) -> ETLResult:
        """
        Executa o pipeline ETL e aguarda conclusão.

        Args:
            start_date: Data inicial do filtro (opcional).
            end_date: Data final do filtro (opcional).
            patient_id: ID do paciente para filtrar (opcional).

        Returns:
            ETLResult com status e métricas da execução.
        """
        started_at = datetime.now()
        logger.info("Iniciando pipeline ETL às %s", started_at)

        # 1. Montar comando do kitchen.sh
        cmd = [KITCHEN_PATH, f"-file={JOB_PATH}"]

        # Adicionar parâmetros se fornecidos
        if start_date:
            cmd.append(f"-param:START_DATE={start_date.isoformat()}")
        if end_date:
            cmd.append(f"-param:END_DATE={end_date.isoformat()}")
        if patient_id:
            cmd.append(f"-param:PATIENT_ID={patient_id}")

        logger.info("Executando comando: %s", " ".join(cmd))

        # 2. Executar o job
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError:
            logger.error("kitchen.sh não encontrado em %s", KITCHEN_PATH)
            return ETLResult(
                success=False,
                message=f"kitchen.sh não encontrado em {KITCHEN_PATH}",
            )
        except Exception as e:
            logger.error("Erro ao iniciar pipeline: %s", e)
            return ETLResult(
                success=False,
                message=f"Erro ao iniciar pipeline: {e}",
            )

        # 3. Fazer polling até conclusão ou timeout
        etl_log = self._poll_for_completion(started_at)

        # 4. Aguardar processo terminar e capturar saída
        stdout, stderr = process.communicate(timeout=POLL_TIMEOUT_SECONDS)

        if process.returncode != 0:
            logger.error("Pipeline falhou com código %d", process.returncode)
            logger.error("Stderr: %s", stderr)
            return ETLResult(
                success=False,
                message=f"Pipeline falhou com código {process.returncode}",
                etl_log=etl_log,
                duration_seconds=int((datetime.now() - started_at).total_seconds()),
            )

        # 5. Retornar resultado
        if etl_log:
            logger.info(
                "Pipeline concluído: %d pacientes, %d visitas em %ds",
                etl_log.records_loaded_patients,
                etl_log.records_loaded_visits,
                etl_log.duration_seconds or 0,
            )
            return ETLResult(
                success=True,
                message="Pipeline executado com sucesso",
                etl_log=etl_log,
                duration_seconds=etl_log.duration_seconds or 0,
            )

        return ETLResult(
            success=True,
            message="Pipeline executado, mas log não encontrado",
            duration_seconds=int((datetime.now() - started_at).total_seconds()),
        )

    def _poll_for_completion(self, started_at: datetime) -> ETLLog | None:
        """
        Faz polling na tabela etl_logs até encontrar conclusão.

        Args:
            started_at: Timestamp de início para filtrar logs.

        Returns:
            ETLLog se encontrado, None se timeout.
        """
        elapsed = 0

        while elapsed < POLL_TIMEOUT_SECONDS:
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

            logger.debug("Polling etl_logs... (%ds)", elapsed)

            etl_log = self._etl_repo.get_latest_completed(since=started_at)

            if etl_log:
                logger.info("Log encontrado: execution_id=%s", etl_log.execution_id)
                return etl_log

        logger.warning("Timeout aguardando conclusão do pipeline")
        return None


_service: ETLService | None = None


def get_etl_service() -> ETLService:
    """Factory function para obter instância do serviço."""
    global _service
    if _service is None:
        _service = ETLService()
    return _service
