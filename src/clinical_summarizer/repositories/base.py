"""
Infraestrutura base para repositórios.

Gerencia o pool de conexões PostgreSQL usando psycopg3.
O pool é inicializado uma vez e reutilizado por toda a aplicação.

Por que usar connection pool:
1. Evita overhead de criar/destruir conexões a cada query
2. Limita número máximo de conexões ao banco
3. Gerencia conexões ociosas automaticamente
4. Melhora performance em cenários de alta concorrência
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

from psycopg import Connection, OperationalError
from psycopg_pool import ConnectionPool

from clinical_summarizer.config import Settings, get_settings
from clinical_summarizer.exceptions import DatabaseConnectionError, QueryError

logger = logging.getLogger(__name__)

# Pool global - inicializado uma vez via init_pool()
_pool: ConnectionPool | None = None


def init_pool(settings: Settings | None = None) -> ConnectionPool:
    """
    Inicializa o pool de conexões PostgreSQL.

    Deve ser chamado uma vez durante o startup da aplicação (ex: lifespan do FastAPI).
    Conexões subsequentes usam o pool já criado.

    Args:
        settings: Configurações da aplicação. Se None, carrega do ambiente.

    Returns:
        O pool de conexões criado.

    Raises:
        DatabaseConnectionError: Se não conseguir conectar ao banco.
    """
    global _pool

    if _pool is not None:
        logger.warning("Pool já inicializado. Retornando pool existente.")
        return _pool

    if settings is None:
        settings = get_settings()

    try:
        _pool = ConnectionPool(
            conninfo=settings.postgres_dsn,
            min_size=settings.postgres_pool_min_size,
            max_size=settings.postgres_pool_max_size,
            # Timeout para obter conexão do pool (em segundos)
            timeout=30.0,
            # Verifica se conexões estão válidas antes de entregar
            check=ConnectionPool.check_connection,
        )
        # Abre o pool (cria conexões mínimas)
        _pool.open()
        logger.info(
            "Pool de conexões inicializado: min=%d, max=%d",
            settings.postgres_pool_min_size,
            settings.postgres_pool_max_size,
        )
        return _pool

    except OperationalError as e:
        logger.error("Falha ao conectar ao PostgreSQL: %s", e)
        raise DatabaseConnectionError(
            f"Não foi possível conectar ao banco de dados: {e}"
        ) from e


def close_pool() -> None:
    """
    Fecha o pool de conexões.

    Deve ser chamado durante o shutdown da aplicação.
    Aguarda todas as conexões serem devolvidas antes de fechar.
    """
    global _pool

    if _pool is not None:
        _pool.close()
        _pool = None
        logger.info("Pool de conexões fechado.")


def get_pool() -> ConnectionPool:
    """
    Retorna o pool de conexões.

    Raises:
        DatabaseConnectionError: Se o pool não foi inicializado.
    """
    if _pool is None:
        raise DatabaseConnectionError(
            "Pool de conexões não inicializado. Chame init_pool() primeiro."
        )
    return _pool


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """
    Context manager para obter uma conexão do pool.

    A conexão é automaticamente devolvida ao pool ao sair do bloco with,
    mesmo se ocorrer exceção. Isso garante que não haja vazamento de conexões.

    Exemplo de uso:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM patients")
                rows = cur.fetchall()

    Yields:
        Conexão PostgreSQL do pool.

    Raises:
        DatabaseConnectionError: Se não conseguir obter conexão.
        QueryError: Se ocorrer erro durante uso da conexão.
    """
    pool = get_pool()

    try:
        # pool.connection() é um context manager que devolve a conexão ao sair
        with pool.connection() as conn:
            yield conn

    except OperationalError as e:
        logger.error("Erro de conexão: %s", e)
        raise DatabaseConnectionError(f"Erro de conexão com o banco: {e}") from e

    except Exception as e:
        logger.error("Erro durante execução de query: %s", e)
        raise QueryError(f"Erro ao executar operação no banco: {e}") from e
