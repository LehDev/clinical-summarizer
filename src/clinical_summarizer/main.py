"""
Entrypoint principal da aplicação FastAPI.

Para rodar em desenvolvimento:
    uv run uvicorn clinical_summarizer.main:app --reload

Ou com Python/pip:
    uvicorn clinical_summarizer.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from clinical_summarizer.api.routes import etl_router, health_router, summaries_router, visits_router
from clinical_summarizer.config import get_settings
from clinical_summarizer.repositories import close_pool, init_pool

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia ciclo de vida da aplicação.

    O lifespan substitui os eventos on_startup/on_shutdown (deprecated).
    Código antes do yield roda no startup, depois do yield roda no shutdown.

    Responsabilidades:
    - Startup: inicializar pool de conexões, validar configurações
    - Shutdown: fechar pool de conexões, liberar recursos
    """
    # === STARTUP ===
    logger.info("Iniciando aplicação...")

    settings = get_settings()
    logger.info("Ambiente: %s", settings.app_env)

    # Inicializa pool de conexões com o banco
    try:
        init_pool(settings)
        logger.info("Pool de conexões inicializado com sucesso")
    except Exception as e:
        logger.error("Falha ao inicializar pool de conexões: %s", e)
        raise

    yield  # Aplicação rodando

    # === SHUTDOWN ===
    logger.info("Encerrando aplicação...")
    close_pool()
    logger.info("Pool de conexões fechado")


# Cria instância da aplicação
app = FastAPI(
    title="Clinical Summarizer API",
    description=(
        "API para geração de resumos clínicos automatizados via LLM. "
        "Consome dados anonimizados da camada Gold do pipeline ETL."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # Configurações do Swagger UI
    docs_url="/docs",
    redoc_url="/redoc",
)

# Registra routers
app.include_router(health_router)
app.include_router(visits_router)
app.include_router(summaries_router)
app.include_router(etl_router)


# Para rodar diretamente com: python -m clinical_summarizer.main
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "clinical_summarizer.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
