"""
Rotas para geração de resumos clínicos.

Endpoints:
    POST /summaries - Gera resumo clínico para um paciente
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from clinical_summarizer.api.schemas import (
    ErrorResponse,
    SummaryRequest,
    SummaryResponse,
)
from clinical_summarizer.exceptions import (
    InvalidDateRangeError,
    LLMConnectionError,
    LLMGenerationError,
    NoVisitsFoundError,
    PatientNotFoundError,
)
from clinical_summarizer.services import SummaryService, get_summary_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/summaries", tags=["Summaries"])

SummaryServiceDep = Annotated[SummaryService, Depends(get_summary_service)]


@router.post(
    "",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar resumo clínico",
    description="""
    Gera um resumo clínico para um paciente com base nas visitas
    do período especificado.

    **Fluxo completo (run_etl=true, padrão):**
    1. Executa o ETL (Pentaho) para carregar dados atualizados
    2. Busca visitas do paciente no período
    3. Gera resumo via LLM (Anthropic Claude)
    4. Salva resumo no banco de dados

    **Requisitos:**
    - ANTHROPIC_API_KEY configurada no servidor
    - Pentaho instalado (se run_etl=true)
    - Paciente deve existir no sistema
    - Deve haver pelo menos uma visita no período

    **Timeout:** ~5 minutos (ETL) + tempo de geração do LLM
    """,
    responses={
        201: {"description": "Resumo gerado com sucesso"},
        404: {"model": ErrorResponse, "description": "Paciente não encontrado"},
        422: {
            "model": ErrorResponse,
            "description": "Dados inválidos ou sem visitas no período",
        },
        503: {
            "model": ErrorResponse,
            "description": "Serviço de LLM indisponível",
        },
    },
)
def generate_summary(
    request: SummaryRequest,
    service: SummaryServiceDep,
) -> SummaryResponse:
    """
    Gera um resumo clínico para o paciente especificado.

    O resumo é baseado em todas as visitas do paciente no período
    informado e é gerado utilizando Anthropic Claude.
    """
    try:
        summary = service.generate_summary(
            patient_id=request.patient_id,
            start_date=request.start_date,
            end_date=request.end_date,
            run_etl=request.run_etl,
        )

        return SummaryResponse(
            summary_id=summary.summary_id,
            patient_id=summary.patient_id,
            summary_text=summary.summary_text,
            visit_count=len(summary.visit_ids_list),
            filter_start_date=summary.filter_start_date,
            filter_end_date=summary.filter_end_date,
            llm_model=summary.llm_model,
            llm_total_tokens=summary.llm_total_tokens,
            generation_duration_ms=summary.generation_duration_ms,
            created_at=summary.created_at,
        )

    except PatientNotFoundError as e:
        logger.warning("Paciente não encontrado: %s", request.patient_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except InvalidDateRangeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    except NoVisitsFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e

    except LLMConnectionError as e:
        logger.error("Erro de conexão com LLM: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de geração de resumos indisponível. Tente novamente.",
        ) from e

    except LLMGenerationError as e:
        logger.error("Erro na geração de resumo: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Erro ao gerar resumo. Tente novamente.",
        ) from e
