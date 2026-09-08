"""
Camada de serviço - lógica de negócio e orquestração.
"""

from clinical_summarizer.services.etl_service import ETLService, get_etl_service
from clinical_summarizer.services.summary_service import (
    SummaryService,
    get_summary_service,
)
from clinical_summarizer.services.summary_sections import (
    SUMMARY_CONTENT_SECTION_LABELS,
    SUMMARY_CONTENT_SECTIONS,
    SUMMARY_SECTION_LABELS,
    SummarySection,
    VisitPeriod,
    parse_summary_sections_safe,
    parse_visit_periods_safe,
    render_summary_markdown,
)
from clinical_summarizer.services.visit_service import VisitService, get_visit_service

__all__ = [
    "ETLService",
    "SUMMARY_CONTENT_SECTION_LABELS",
    "SUMMARY_CONTENT_SECTIONS",
    "SUMMARY_SECTION_LABELS",
    "SummaryService",
    "SummarySection",
    "VisitPeriod",
    "VisitService",
    "get_etl_service",
    "get_summary_service",
    "get_visit_service",
    "parse_summary_sections_safe",
    "parse_visit_periods_safe",
    "render_summary_markdown",
]
