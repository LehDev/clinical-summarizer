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
