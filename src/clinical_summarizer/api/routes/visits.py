"""
Endpoints relacionados a visitas clínicas.
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, status

from clinical_summarizer.api.dependencies import VisitServiceDep
from clinical_summarizer.api.schemas import (
    ErrorResponse,
    VisitListResponse,
    VisitResponse,
)
from clinical_summarizer.exceptions import (
    InvalidDateRangeError,
    PatientNotFoundError,
    VisitNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Visits"])


@router.get(
    "/{patient_id}/visits",
    response_model=VisitListResponse,
    summary="Lista visitas de um paciente",
    description="Retorna todas as visitas de um paciente em um período específico.",
    responses={
        200: {"description": "Lista de visitas encontradas"},
        404: {"model": ErrorResponse, "description": "Paciente não encontrado"},
        422: {"model": ErrorResponse, "description": "Parâmetros inválidos"},
    },
)
def get_patient_visits(
    service: VisitServiceDep,
    patient_id: str = Path(
        description="ID original do paciente (será convertido para hash internamente)",
        min_length=1,
    ),
    start_date: date = Query(
        description="Data inicial do período (formato: YYYY-MM-DD)",
        examples=["2025-01-01"],
    ),
    end_date: date = Query(
        description="Data final do período (formato: YYYY-MM-DD)",
        examples=["2025-12-31"],
    ),
) -> VisitListResponse:
    """
    Busca visitas de um paciente em um período.

    Este endpoint será usado futuramente pelo Kafka consumer para
    disparar geração de resumos clínicos.

    Args:
        service: Serviço de visitas (injetado).
        patient_id: ID original do paciente (convertido para hash internamente).
        start_date: Data inicial (inclusiva).
        end_date: Data final (inclusiva).

    Returns:
        Lista de visitas no período com metadados.

    Raises:
        HTTPException 404: Se paciente não existir.
        HTTPException 422: Se intervalo de datas for inválido.
    """
    try:
        visits = service.get_patient_visits(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
        )

        return VisitListResponse(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            count=len(visits),
            visits=[VisitResponse.model_validate(v) for v in visits],
        )

    except PatientNotFoundError as e:
        logger.warning("Paciente não encontrado: %s", patient_id[:8])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e


@router.get(
    "/visits/{visit_id}",
    response_model=VisitResponse,
    summary="Detalhes de uma visita",
    description="Retorna todos os dados de uma visita específica.",
    responses={
        200: {"description": "Dados da visita"},
        404: {"model": ErrorResponse, "description": "Visita não encontrada"},
    },
)
def get_visit_details(
    service: VisitServiceDep,
    visit_id: str = Path(
        description="ID original da visita (será convertido para hash internamente)",
        min_length=1,
    ),
) -> VisitResponse:
    """
    Busca detalhes completos de uma visita.

    Args:
        service: Serviço de visitas (injetado).
        visit_id: ID original da visita (convertido para hash internamente).

    Returns:
        Dados completos da visita.

    Raises:
        HTTPException 404: Se visita não existir.
    """
    try:
        visit = service.get_visit_details(visit_id)
        return VisitResponse.model_validate(visit)

    except VisitNotFoundError as e:
        logger.warning("Visita não encontrada: %s", visit_id[:8])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
