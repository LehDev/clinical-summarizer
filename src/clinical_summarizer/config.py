"""
Configuração centralizada da aplicação.

Usa pydantic-settings para carregar variáveis de ambiente com validação de tipos.
O arquivo .env é carregado automaticamente se existir no diretório raiz.

Exemplo de uso:
    from clinical_summarizer.config import get_settings

    settings = get_settings()
    print(settings.postgres_host)
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas de variáveis de ambiente.

    Todas as variáveis são validadas no startup. Se alguma obrigatória
    estiver faltando, a aplicação falha imediatamente com erro claro.
    """

    model_config = SettingsConfigDict(
        # Carrega .env do diretório onde o script é executado
        env_file=".env",
        env_file_encoding="utf-8",
        # Ignora variáveis extras no .env que não estão definidas aqui
        extra="ignore",
        # Case insensitive para nomes de variáveis
        case_sensitive=False,
    )

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "clinical_data"
    postgres_user: str
    postgres_password: str

    # Pool de conexões
    postgres_pool_min_size: int = 2
    postgres_pool_max_size: int = 10

    # -------------------------------------------------------------------------
    # Aplicação
    # -------------------------------------------------------------------------
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_port: int = 8734

    # -------------------------------------------------------------------------
    # CORS - origens do frontend autorizadas a consumir a API
    # -------------------------------------------------------------------------
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # -------------------------------------------------------------------------
    # Google Gemini (opcional)
    # -------------------------------------------------------------------------
    google_api_key: str | None = None

    # -------------------------------------------------------------------------
    # Anthropic Claude (para geração de resumos)
    # -------------------------------------------------------------------------
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_temperature: float = 0.3
    anthropic_max_tokens: int = 4096

    @property
    def postgres_dsn(self) -> str:
        """
        Retorna a connection string completa para o PostgreSQL.

        Formato: postgresql://user:password@host:port/database

        Nota: Usamos o prefixo 'postgresql' (não 'postgres') pois é o formato
        padrão aceito pelo psycopg3.
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_development(self) -> bool:
        """Retorna True se estiver em ambiente de desenvolvimento."""
        return self.app_env == "development"

    @property
    def cors_origins_list(self) -> list[str]:
        """Converte CORS_ORIGINS (string separada por vírgula) em lista."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.

    Usa lru_cache para garantir que o .env seja lido apenas uma vez
    durante o ciclo de vida da aplicação. Isso é importante porque:
    1. Evita I/O desnecessário em cada chamada
    2. Garante consistência (mesmas configs em toda a aplicação)

    Em testes, use `get_settings.cache_clear()` para resetar.
    """
    return Settings()
