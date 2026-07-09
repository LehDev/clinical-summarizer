"""
Modelo de domínio para Visita Clínica.

Representa uma visita/atendimento de um paciente, com todos os dados
clínicos associados (CIDs, evoluções, prescrições, etc).
"""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Visit:
    """
    Representa uma visita clínica no sistema.

    Atributos:
        visit_id: Hash SHA-256 do ID original (anonimizado)
        patient_id: Hash SHA-256 do paciente associado
        visit_date: Data da visita
        cid_codes: Códigos CID separados por delimitador (ex: "J06.9;J11.1")
        cid_names: Nomes dos CIDs correspondentes
        clinical_evolutions: Texto das evoluções clínicas
        sign_symptoms: Sinais e sintomas relatados
        prescriptions: Prescrições médicas
        evaluations_raw: Blob JSON com avaliações (não parseado)
        evaluation_types: Tipos de avaliações realizadas
        created_at: Data de criação do registro

    Notas:
        - Campos de texto podem conter mojibake que será corrigido
          pela camada de serviço antes de enviar ao LLM
        - evaluations_raw será parseado em fase posterior
    """

    visit_id: str
    patient_id: str
    visit_date: date | None = None
    cid_codes: str | None = None
    cid_names: str | None = None
    clinical_evolutions: str | None = None
    sign_symptoms: str | None = None
    prescriptions: str | None = None
    evaluations_raw: str | None = None
    evaluation_types: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validações básicas após inicialização."""
        if not self.visit_id:
            raise ValueError("visit_id não pode ser vazio")
        if not self.patient_id:
            raise ValueError("patient_id não pode ser vazio")

    @property
    def cid_codes_list(self) -> list[str]:
        """
        Retorna códigos CID como lista.

        Assume que os códigos são separados por ponto-e-vírgula.
        Retorna lista vazia se cid_codes for None ou vazio.
        """
        if not self.cid_codes:
            return []
        return [code.strip() for code in self.cid_codes.split(";") if code.strip()]

    @property
    def cid_names_list(self) -> list[str]:
        """
        Retorna nomes dos CIDs como lista.

        Mesmo comportamento de cid_codes_list.
        """
        if not self.cid_names:
            return []
        return [name.strip() for name in self.cid_names.split(";") if name.strip()]
