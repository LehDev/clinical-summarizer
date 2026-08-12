"""
Rotas para execução do pipeline ETL.

Endpoints:
    POST /etl/run - Executa o pipeline Pentaho
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from clinical_summarizer.api.schemas import (
    ETLRunRequest,
    ETLRunResponse,
)
from clinical_summarizer.services.etl_service import ETLService, get_etl_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["ETL Pipeline"])

ETLServiceDep = Annotated[ETLService, Depends(get_etl_service)]


@router.post(
    "/run",
    response_model=ETLRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Executar pipeline ETL",
    description="""
    Executa o pipeline ETL (Pentaho) para extrair e carregar dados.

    O pipeline é executado de forma síncrona - a requisição aguarda
    a conclusão do job antes de retornar.

    **Parâmetros opcionais:**
    - start_date/end_date: Filtrar por período
    - patient_id: Filtrar por paciente específico

    **Timeout:** 5 minutos (300 segundos)
    """,
    responses={
        200: {"description": "Pipeline executado (sucesso ou falha)"},
        500: {"description": "Erro interno ao executar pipeline"},
    },
)
def run_etl_pipeline(
    request: ETLRunRequest,
    service: ETLServiceDep,
) -> ETLRunResponse:
    """
    Executa o pipeline ETL Pentaho.

    Aciona o kitchen.sh e aguarda a conclusão monitorando
    a tabela etl_logs.
    """
    logger.info(
        "Requisição ETL recebida: start_date=%s, end_date=%s, patient_id=%s",
        request.start_date,
        request.end_date,
        request.patient_id,
    )

    result = service.run_pipeline(
        start_date=request.start_date,
        end_date=request.end_date,
        patient_id=request.patient_id,
    )

    response = ETLRunResponse(
        success=result.success,
        message=result.message,
        duration_seconds=result.duration_seconds,
    )

    if result.etl_log:
        response.execution_id = str(result.etl_log.execution_id)
        response.pipeline_name = result.etl_log.pipeline_name
        response.status = result.etl_log.status
        response.records_extracted = result.etl_log.records_extracted
        response.records_transformed = result.etl_log.records_transformed
        response.records_loaded_patients = result.etl_log.records_loaded_patients
        response.records_loaded_visits = result.etl_log.records_loaded_visits
        response.error_message = result.etl_log.error_message

    return response
