"""
Endpoints relacionados a visitas clínicas.
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, status

from clinical_summarizer.api.dependencies import VisitServiceDep
from clinical_summarizer.api.schemas import (
    ErrorResponse,
    PatientEvaluationsResponse,
    VisitEvaluationResponse,
    VisitListResponse,
    VisitResponse,
)
from clinical_summarizer.utils import clean_questions_data, parse_evaluations_raw
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


@router.get(
    "/{patient_id}/evaluations",
    response_model=PatientEvaluationsResponse,
    summary="Avaliações de todas as visitas de um paciente",
    description="""
    Retorna os dados de evaluations_raw parseados de TODAS as visitas
    de um paciente em um período específico.

    Os dados são organizados por visita, cada uma contendo suas seções
    de avaliação com campos e valores formatados.

    Útil para obter uma visão completa do histórico de avaliações do paciente.
    """,
    responses={
        200: {"description": "Avaliações de todas as visitas"},
        404: {"model": ErrorResponse, "description": "Paciente não encontrado"},
        422: {"model": ErrorResponse, "description": "Parâmetros inválidos"},
    },
)
def get_patient_evaluations(
    service: VisitServiceDep,
    patient_id: str = Path(
        description="ID original do paciente (será convertido para hash internamente)",
        min_length=1,
    ),
    start_date: date = Query(
        description="Data inicial do período (formato: YYYY-MM-DD)",
        examples=["2022-10-01"],
    ),
    end_date: date = Query(
        description="Data final do período (formato: YYYY-MM-DD)",
        examples=["2022-10-31"],
    ),
    include_raw_text: bool = Query(
        default=True,
        description="Incluir texto formatado para RAG em cada visita",
    ),
) -> PatientEvaluationsResponse:
    """
    Retorna as avaliações de todas as visitas de um paciente.

    Busca todas as visitas do paciente no período especificado e
    faz o parse dos dados de evaluations_raw de cada uma.

    Args:
        service: Serviço de visitas (injetado).
        patient_id: ID original do paciente.
        start_date: Data inicial do período.
        end_date: Data final do período.
        include_raw_text: Se True, inclui o texto formatado em cada visita.

    Returns:
        Avaliações de todas as visitas organizadas por data.
    """
    try:
        # Buscar todas as visitas do paciente
        visits = service.get_patient_visits(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Processar avaliações de cada visita
        visits_evaluations = []
        visits_with_evaluations = 0

        for visit in visits:
            # Filtro: só inclui visitas com pelo menos um dado relevante
            has_cid_names = visit.cid_names and visit.cid_names.strip()
            has_clinical_evolutions = visit.clinical_evolutions and visit.clinical_evolutions.strip()
            has_sign_symptoms = visit.sign_symptoms and visit.sign_symptoms.strip()
            has_evaluations_raw = visit.evaluations_raw and visit.evaluations_raw.strip()

            if not (has_cid_names or has_clinical_evolutions or has_sign_symptoms or has_evaluations_raw):
                continue

            # Tenta ambos os parsers para suportar diferentes formatos
            raw_data = visit.evaluations_raw

            # Parser para formato antigo (seções com [[{...}]])
            parsed_sections = parse_evaluations_raw(raw_data)

            # Parser para formato novo (questões com question_id/question_name)
            parsed_questions = clean_questions_data(raw_data)

            # Verifica se tem dados em algum dos formatos
            has_sections = parsed_sections.total_filled_fields > 0
            has_questions = len(parsed_questions.questions) > 0

            if has_sections or has_questions:
                visits_with_evaluations += 1

            # Monta o dicionário de questões (question_name -> value)
            questions_dict = {}
            if has_questions:
                questions_dict = parsed_questions.to_name_value_dict()

            # Monta o texto formatado combinando ambos os formatos
            raw_text_parts = []
            if include_raw_text:
                if has_sections:
                    raw_text_parts.append(parsed_sections.to_text())
                if has_questions:
                    raw_text_parts.append(parsed_questions.to_text())

            visits_evaluations.append(
                VisitEvaluationResponse(
                    visit_id=visit.visit_id,
                    visit_date=visit.visit_date,
                    cid_codes=visit.cid_codes,
                    cid_names=visit.cid_names,
                    clinical_evolutions=visit.clinical_evolutions,
                    sign_symptoms=visit.sign_symptoms,
                    evaluation_types=visit.evaluation_types,
                    total_fields=parsed_sections.total_fields + parsed_questions.total_original,
                    total_filled_fields=parsed_sections.total_filled_fields + len(parsed_questions.questions),
                    questions_dict=questions_dict,
                    raw_text="\n\n".join(raw_text_parts) if raw_text_parts else None,
                )
            )

        # Obter o patient_id hash da primeira visita (se houver)
        patient_id_hash = visits[0].patient_id if visits else ""

        return PatientEvaluationsResponse(
            patient_id=patient_id_hash,
            start_date=start_date,
            end_date=end_date,
            total_visits=len(visits_evaluations),
            total_visits_with_evaluations=visits_with_evaluations,
            visits=visits_evaluations,
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
