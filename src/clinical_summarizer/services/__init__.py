"""
Camada de serviço - lógica de negócio e orquestração.
"""

from clinical_summarizer.services.visit_service import VisitService, get_visit_service

__all__ = ["VisitService", "get_visit_service"]
