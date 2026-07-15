"""
Routers da API.

Cada arquivo neste diretório contém um router com endpoints relacionados.
"""

from clinical_summarizer.api.routes.health import router as health_router
from clinical_summarizer.api.routes.summaries import router as summaries_router
from clinical_summarizer.api.routes.visits import router as visits_router

__all__ = ["health_router", "summaries_router", "visits_router"]
