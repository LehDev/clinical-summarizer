"""
Modelo de domínio para Paciente.

Representa um paciente já anonimizado (patient_id é hash SHA-256).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Patient:
    """
    Representa um paciente no sistema.

    Atributos:
        patient_id: Hash SHA-256 do ID original (anonimizado)
        age: Idade do paciente
        gender: Gênero do paciente
        created_at: Data de criação do registro
        updated_at: Data da última atualização

    frozen=True torna a instância imutável, o que:
    - Previne modificações acidentais após criação
    - Permite usar como chave em dicionários/sets
    - Indica claramente que é um objeto de valor (value object)
    """

    patient_id: str
    age: int | None
    gender: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validações básicas após inicialização."""
        if not self.patient_id:
            raise ValueError("patient_id não pode ser vazio")
