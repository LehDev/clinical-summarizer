"""
Endpoints de health check.

Útil para:
- Kubernetes liveness/readiness probes
- Load balancers verificarem se instância está saudável
- Monitoramento de infraestrutura
"""

import logging

from fastapi import APIRouter, status

from clinical_summarizer.api.schemas import HealthResponse
from clinical_summarizer.repositories.base import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica saúde da aplicação",
    description="Retorna status da aplicação e conexão com banco de dados.",
)
def health_check() -> HealthResponse:
    """
    Endpoint de health check.

    Verifica:
    1. Aplicação está respondendo
    2. Conexão com PostgreSQL está funcionando

    Returns:
        Status da aplicação e do banco.
    """
    db_status = "healthy"

    try:
        # Tenta executar query simples para verificar conexão
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")

    except Exception as e:
        logger.error("Health check falhou - banco indisponível: %s", e)
        db_status = "unhealthy"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Root endpoint",
    description="Endpoint raiz com informações básicas da API.",
)
def root() -> dict:
    """Endpoint raiz retorna informações básicas da API."""
    return {
        "service": "clinical-summarizer",
        "version": "0.1.0",
        "docs": "/docs",
    }
