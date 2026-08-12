"""
Schemas Pydantic para validação de requests e serialização de responses.

Estes modelos são diferentes dos modelos de domínio:
- Modelos de domínio (models/): representam entidades do negócio
- Schemas (api/): representam contratos da API (entrada/saída HTTP)

Separar permite:
- Adicionar/remover campos na API sem afetar domínio
- Validação específica para HTTP (ex: formatos de data)
- Documentação automática via OpenAPI/Swagger
"""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class VisitResponse(BaseModel):
    """
    Schema de resposta para uma visita.

    Todos os campos do domínio são expostos, mas podemos
    adicionar/remover conforme necessidade da API.
    """

    model_config = ConfigDict(
        # Permite criar a partir de objetos com atributos (dataclasses)
        from_attributes=True,
        # Exemplo no Swagger
        json_schema_extra={
            "example": {
                "visit_id": "a1b2c3d4e5f6...",
                "patient_id": "f6e5d4c3b2a1...",
                "visit_date": "2025-06-15",
                "cid_codes": "J06.9;J11.1",
                "cid_names": "Infecção respiratória aguda;Influenza",
            }
        },
    )

    visit_id: str
    patient_id: str
    visit_date: date | None = None
    cid_codes: str | None = None
    cid_names: str | None = None
    clinical_evolutions: str | None = None
    sign_symptoms: str | None = None
    prescriptions: str | None = None
    evaluations_raw: str | None = None
    evaluation_types: str | None = None
    created_at: datetime | None = None


class VisitListResponse(BaseModel):
    """
    Schema de resposta para lista de visitas.

    Inclui metadados úteis para o cliente:
    - patient_id: confirma qual paciente foi consultado
    - period: intervalo de datas da busca
    - count: quantidade de visitas encontradas
    - visits: lista de visitas
    """

    patient_id: str
    start_date: date
    end_date: date
    count: int = Field(description="Quantidade de visitas no período")
    visits: list[VisitResponse]


class ErrorResponse(BaseModel):
    """
    Schema padrão para respostas de erro.

    Formato consistente facilita tratamento no frontend.
    """

    detail: str = Field(description="Mensagem de erro legível")
    error_code: str | None = Field(
        default=None,
        description="Código de erro para tratamento programático",
    )


class HealthResponse(BaseModel):
    """Schema de resposta para health check."""

    status: str = Field(description="Status da aplicação")
    database: str = Field(description="Status da conexão com banco")


class CleanedQuestionResponse(BaseModel):
    """Schema de resposta para uma questão limpa."""

    question_id: int = Field(description="ID da questão")
    question_name: str = Field(description="Nome da questão")
    value: str = Field(description="Valor da resposta")
    field_type_id: int = Field(description="Tipo do campo")


class EvaluationSectionResponse(BaseModel):
    """Schema de resposta para uma seção de avaliação."""

    section_index: int = Field(description="Índice da seção")
    fields: dict[str, str] = Field(description="Campos da seção (nome -> valor)")


class VisitEvaluationResponse(BaseModel):
    """Schema de resposta para avaliações de uma única visita."""

    visit_id: str = Field(description="Hash SHA-256 da visita")
    visit_date: date | None = Field(description="Data da visita")
    cid_codes: str | None = Field(default=None, description="Códigos CID")
    cid_names: str | None = Field(default=None, description="Nomes dos CIDs")
    clinical_evolutions: str | None = Field(default=None, description="Evoluções clínicas")
    sign_symptoms: str | None = Field(default=None, description="Sinais e sintomas")
    prescriptions: str | None = Field(default=None, description="Prescrições")
    evaluation_types: str | None = Field(default=None, description="Tipos de avaliação")
    total_fields: int = Field(default=0, description="Total de campos")
    total_filled_fields: int = Field(default=0, description="Total de campos preenchidos")
    questions_dict: dict[str, str] = Field(
        default_factory=dict,
        description="Questões como dicionário (question_name -> value)",
    )
    raw_text: str | None = Field(
        default=None,
        description="Texto formatado das avaliações",
    )


class PatientEvaluationsResponse(BaseModel):
    """Schema de resposta para avaliações de todas as visitas de um paciente."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "f6e5d4c3b2a1...",
                "start_date": "2022-10-01",
                "end_date": "2022-10-31",
                "total_visits": 3,
                "total_visits_with_evaluations": 2,
                "visits": [
                    {
                        "visit_id": "a1b2c3d4e5f6...",
                        "visit_date": "2022-10-15",
                        "total_sections": 5,
                        "total_fields": 50,
                        "total_filled_fields": 30,
                        "sections": [
                            {
                                "section_index": 0,
                                "fields": {
                                    "Nível de Consciência": "Alerta",
                                },
                            }
                        ],
                    }
                ],
            }
        },
    )

    patient_id: str = Field(description="Hash SHA-256 do paciente")
    start_date: date = Field(description="Data inicial do período")
    end_date: date = Field(description="Data final do período")
    total_visits: int = Field(description="Total de visitas no período")
    total_visits_with_evaluations: int = Field(
        description="Total de visitas com avaliações preenchidas"
    )
    visits: list[VisitEvaluationResponse] = Field(
        description="Avaliações de cada visita"
    )


class SummaryRequest(BaseModel):
    """
    Schema de request para geração de resumo clínico.

    O resumo será gerado a partir das visitas do paciente
    no período especificado. Por padrão, executa o ETL (Pentaho)
    antes de gerar o resumo para garantir dados atualizados.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "899",
                "start_date": "2022-10-01",
                "end_date": "2022-10-31",
                "run_etl": True,
            }
        },
    )

    patient_id: str = Field(
        description="ID original do paciente (será convertido para hash)",
        min_length=1,
    )
    start_date: date = Field(description="Data inicial do período")
    end_date: date = Field(description="Data final do período")
    run_etl: bool = Field(
        default=True,
        description="Se True, executa o ETL (Pentaho) antes de gerar o resumo",
    )


class SummaryResponse(BaseModel):
    """
    Schema de resposta para resumo clínico gerado.

    Contém o resumo gerado e metadados sobre a geração.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "summary_id": "550e8400-e29b-41d4-a716-446655440000",
                "patient_id": "f6e5d4c3b2a1...",
                "summary_text": "Paciente apresentou quadro de...",
                "visit_count": 3,
                "llm_model": "claude-sonnet-4-20250514",
                "llm_total_tokens": 1500,
                "generation_duration_ms": 2500,
                "created_at": "2025-06-15T10:30:00",
            }
        },
    )

    summary_id: str = Field(description="UUID único do resumo")
    patient_id: str = Field(description="Hash do paciente")
    summary_text: str = Field(description="Texto do resumo gerado")
    visit_count: int = Field(description="Quantidade de visitas usadas")
    filter_start_date: date = Field(description="Data inicial do filtro")
    filter_end_date: date = Field(description="Data final do filtro")
    llm_model: str = Field(description="Modelo LLM usado")
    llm_total_tokens: int | None = Field(description="Total de tokens usados")
    generation_duration_ms: int | None = Field(description="Tempo de geração em ms")
    created_at: datetime | None = Field(description="Data de criação")


# =============================================================================
# ETL Pipeline Schemas
# =============================================================================


class ETLRunRequest(BaseModel):
    """
    Schema de request para execução do pipeline ETL.

    Todos os campos são opcionais - se não fornecidos,
    o pipeline roda com os filtros padrão definidos no job.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "patient_id": 899,
            }
        },
    )

    start_date: date | None = Field(
        default=None,
        description="Data inicial do filtro (opcional)",
    )
    end_date: date | None = Field(
        default=None,
        description="Data final do filtro (opcional)",
    )
    patient_id: int | None = Field(
        default=None,
        description="ID do paciente para filtrar (opcional)",
    )


class ETLRunResponse(BaseModel):
    """Schema de resposta para execução do pipeline ETL."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Pipeline executado com sucesso",
                "execution_id": "550e8400-e29b-41d4-a716-446655440000",
                "pipeline_name": "ETL_Pipeline",
                "status": "completed",
                "records_extracted": 1500,
                "records_transformed": 1450,
                "records_loaded_patients": 120,
                "records_loaded_visits": 1450,
                "duration_seconds": 45,
            }
        },
    )

    success: bool = Field(description="Se a execução foi bem-sucedida")
    message: str = Field(description="Mensagem de status")
    execution_id: str | None = Field(
        default=None,
        description="UUID da execução",
    )
    pipeline_name: str | None = Field(
        default=None,
        description="Nome do pipeline",
    )
    status: str | None = Field(
        default=None,
        description="Status da execução",
    )
    records_extracted: int | None = Field(
        default=None,
        description="Registros extraídos",
    )
    records_transformed: int | None = Field(
        default=None,
        description="Registros transformados",
    )
    records_loaded_patients: int | None = Field(
        default=None,
        description="Pacientes carregados",
    )
    records_loaded_visits: int | None = Field(
        default=None,
        description="Visitas carregadas",
    )
    duration_seconds: int | None = Field(
        default=None,
        description="Duração em segundos",
    )
    error_message: str | None = Field(
        default=None,
        description="Mensagem de erro (se houver)",
    )
