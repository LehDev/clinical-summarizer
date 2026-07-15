"""
Camada de serviço - lógica de negócio e orquestração.
"""

from clinical_summarizer.services.summary_service import (
    SummaryService,
    get_summary_service,
)
from clinical_summarizer.services.visit_service import VisitService, get_visit_service

__all__ = [
    "SummaryService",
    "VisitService",
    "get_summary_service",
    "get_visit_service",
]
