"""
Modelo de domínio para Resumo Clínico.

Representa um resumo gerado por LLM a partir das visitas de um paciente.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Summary:
    """
    Representa um resumo clínico gerado por LLM.

    Atributos:
        id: ID sequencial do banco (gerado automaticamente)
        summary_id: UUID único do resumo
        patient_id: Hash SHA-256 do paciente
        visit_ids: IDs das visitas usadas (separados por vírgula)
        filter_start_date: Data inicial do filtro usado
        filter_end_date: Data final do filtro usado
        summary_text: Texto do resumo gerado
        llm_model: Modelo LLM usado (ex: "claude-3-5-sonnet-20241022")
        llm_prompt_tokens: Tokens do prompt
        llm_completion_tokens: Tokens da resposta
        llm_total_tokens: Total de tokens
        llm_temperature: Temperatura usada na geração
        generation_duration_ms: Tempo de geração em milissegundos
        status: Status do resumo (completed, failed)
        error_message: Mensagem de erro se status=failed
        created_at: Data de criação
    """

    patient_id: str
    visit_ids: str
    summary_text: str
    llm_model: str
    id: int | None = None
    summary_id: str | None = None
    filter_start_date: date | None = None
    filter_end_date: date | None = None
    llm_prompt_tokens: int | None = None
    llm_completion_tokens: int | None = None
    llm_total_tokens: int | None = None
    llm_temperature: Decimal | None = None
    generation_duration_ms: int | None = None
    status: str = "completed"
    error_message: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validações básicas após inicialização."""
        if not self.patient_id:
            raise ValueError("patient_id não pode ser vazio")
        if not self.visit_ids:
            raise ValueError("visit_ids não pode ser vazio")
        if not self.summary_text and self.status == "completed":
            raise ValueError("summary_text não pode ser vazio para status completed")
        if not self.llm_model:
            raise ValueError("llm_model não pode ser vazio")

    @property
    def visit_ids_list(self) -> list[str]:
        """Retorna visit_ids como lista."""
        if not self.visit_ids:
            return []
        return [vid.strip() for vid in self.visit_ids.split(",") if vid.strip()]
