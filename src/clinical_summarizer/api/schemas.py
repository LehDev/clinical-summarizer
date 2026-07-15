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


class SummaryRequest(BaseModel):
    """
    Schema de request para geração de resumo clínico.

    O resumo será gerado a partir das visitas do paciente
    no período especificado.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "patient_id": "899",
                "start_date": "2022-10-01",
                "end_date": "2022-10-31",
            }
        },
    )

    patient_id: str = Field(
        description="ID original do paciente (será convertido para hash)",
        min_length=1,
    )
    start_date: date = Field(description="Data inicial do período")
    end_date: date = Field(description="Data final do período")


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
