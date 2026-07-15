"""
Modelos de domínio da aplicação.

Exporta os modelos principais para uso em outras camadas.
"""

from clinical_summarizer.models.patient import Patient
from clinical_summarizer.models.summary import Summary
from clinical_summarizer.models.visit import Visit

__all__ = ["Patient", "Summary", "Visit"]
