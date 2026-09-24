"""
Exceções customizadas da aplicação.

Hierarquia de exceções:
    ClinicalSummarizerError (base)
    ├── DatabaseError
    │   ├── ConnectionError
    │   └── QueryError
    ├── NotFoundError
    │   ├── PatientNotFoundError
    │   └── VisitNotFoundError
    └── ValidationError

Por que usar exceções customizadas:
1. Permite tratamento específico em cada camada
2. Mensagens de erro mais claras para debugging
3. Facilita mapeamento para códigos HTTP na camada de API
4. Testes podem verificar exceções específicas
"""


class ClinicalSummarizerError(Exception):
    """
    Exceção base para todas as exceções da aplicação.

    Todas as outras exceções herdam desta, permitindo capturar
    qualquer erro da aplicação com um único except.
    """

    def __init__(self, message: str = "Erro interno da aplicação"):
        self.message = message
        super().__init__(self.message)


# =============================================================================
# Exceções de Banco de Dados
# =============================================================================


class DatabaseError(ClinicalSummarizerError):
    """Erro genérico relacionado ao banco de dados."""

    def __init__(self, message: str = "Erro no banco de dados"):
        super().__init__(message)


class DatabaseConnectionError(DatabaseError):
    """
    Falha ao conectar com o banco de dados.

    Causas comuns:
    - Credenciais incorretas
    - Banco não está rodando
    - Host/porta incorretos
    - Pool de conexões esgotado
    """

    def __init__(self, message: str = "Não foi possível conectar ao banco de dados"):
        super().__init__(message)


class QueryError(DatabaseError):
    """
    Erro durante execução de uma query.

    Causas comuns:
    - SQL inválido
    - Violação de constraint
    - Timeout
    """

    def __init__(self, message: str = "Erro ao executar query"):
        super().__init__(message)


# =============================================================================
# Exceções de Recurso Não Encontrado
# =============================================================================


class NotFoundError(ClinicalSummarizerError):
    """Recurso solicitado não foi encontrado."""

    def __init__(self, message: str = "Recurso não encontrado"):
        super().__init__(message)


class PatientNotFoundError(NotFoundError):
    """Paciente não encontrado no banco de dados."""

    def __init__(self, patient_id: str):
        self.patient_id = patient_id
        super().__init__(f"Paciente não encontrado: {patient_id}")


class VisitNotFoundError(NotFoundError):
    """Visita não encontrada no banco de dados."""

    def __init__(self, visit_id: str):
        self.visit_id = visit_id
        super().__init__(f"Visita não encontrada: {visit_id}")


# =============================================================================
# Exceções de Validação
# =============================================================================


class ValidationError(ClinicalSummarizerError):
    """
    Erro de validação de dados de entrada.

    Usado quando os dados passam pela validação do Pydantic mas falham
    em regras de negócio adicionais.
    """

    def __init__(self, message: str = "Dados inválidos"):
        super().__init__(message)


class InvalidDateRangeError(ValidationError):
    """Intervalo de datas inválido (ex: data_fim antes de data_inicio)."""

    def __init__(self, message: str = "Intervalo de datas inválido"):
        super().__init__(message)


# =============================================================================
# Exceções de LLM
# =============================================================================


class LLMError(ClinicalSummarizerError):
    """Erro genérico relacionado ao LLM."""

    def __init__(self, message: str = "Erro no serviço de LLM"):
        super().__init__(message)


class LLMConnectionError(LLMError):
    """Falha ao conectar com a API do LLM."""

    def __init__(self, message: str = "Não foi possível conectar ao LLM"):
        super().__init__(message)


class LLMGenerationError(LLMError):
    """Erro durante geração de texto pelo LLM."""

    def __init__(self, message: str = "Erro ao gerar texto"):
        super().__init__(message)


class NoVisitsFoundError(ValidationError):
    """Nenhuma visita encontrada para gerar resumo."""

    def __init__(self, patient_id: str, start_date: str, end_date: str):
        self.patient_id = patient_id
        super().__init__(
            f"Nenhuma visita encontrada para paciente {patient_id} "
            f"entre {start_date} e {end_date}"
        )
