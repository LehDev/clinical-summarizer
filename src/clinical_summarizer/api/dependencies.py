"""
Dependências injetáveis para endpoints FastAPI.

FastAPI usa o sistema de Depends() para injeção de dependências.
Isso permite:
- Reutilizar lógica comum entre endpoints
- Substituir dependências em testes
- Manter endpoints limpos e focados
"""

from typing import Annotated

from fastapi import Depends

from clinical_summarizer.services import VisitService, get_visit_service

# Type alias para injeção do VisitService
# Uso: def endpoint(service: VisitServiceDep)
VisitServiceDep = Annotated[VisitService, Depends(get_visit_service)]
