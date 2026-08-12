"""
Camada de repositório - acesso a dados.

Exporta repositórios e funções de infraestrutura do pool de conexões.
"""

from clinical_summarizer.repositories.base import (
    close_pool,
    get_connection,
    get_pool,
    init_pool,
)
from clinical_summarizer.repositories.etl_repository import (
    ETLRepository,
    get_etl_repository,
)
from clinical_summarizer.repositories.patient_repository import (
    PatientRepository,
    get_patient_repository,
)
from clinical_summarizer.repositories.summary_repository import (
    SummaryRepository,
    get_summary_repository,
)
from clinical_summarizer.repositories.visit_repository import (
    VisitRepository,
    get_visit_repository,
)

__all__ = [
    # Infraestrutura
    "init_pool",
    "close_pool",
    "get_pool",
    "get_connection",
    # Repositórios
    "ETLRepository",
    "PatientRepository",
    "SummaryRepository",
    "VisitRepository",
    "get_etl_repository",
    "get_patient_repository",
    "get_summary_repository",
    "get_visit_repository",
]
