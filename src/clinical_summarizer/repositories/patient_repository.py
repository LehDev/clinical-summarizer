"""
Repositório para acesso a dados de Pacientes.

Encapsula todas as queries relacionadas à tabela patients.
"""

import logging

from psycopg.rows import dict_row

from clinical_summarizer.exceptions import PatientNotFoundError
from clinical_summarizer.models import Patient
from clinical_summarizer.repositories.base import get_connection

logger = logging.getLogger(__name__)


class PatientRepository:
    """
    Repositório para operações de leitura na tabela patients.
    """

    def get_by_id(self, patient_id: str) -> Patient:
        """
        Busca um paciente específico pelo ID.

        Args:
            patient_id: Hash SHA-256 do ID do paciente.

        Returns:
            Objeto Patient com os dados.

        Raises:
            PatientNotFoundError: Se o paciente não existir.
        """
        query = """
            SELECT
                patient_id,
                age,
                gender,
                created_at,
                updated_at
            FROM patients
            WHERE patient_id = %s
        """

        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (patient_id,))
            row = cur.fetchone()

        if row is None:
            logger.warning("Paciente não encontrado: %s", patient_id)
            raise PatientNotFoundError(patient_id)

        return Patient(
            patient_id=row["patient_id"],
            age=row["age"],
            gender=row["gender"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def exists(self, patient_id: str) -> bool:
        """
        Verifica se um paciente existe no banco.

        Método otimizado que não carrega todos os dados do paciente,
        apenas verifica existência.

        Args:
            patient_id: Hash SHA-256 do ID do paciente.

        Returns:
            True se o paciente existe, False caso contrário.
        """
        query = "SELECT 1 FROM patients WHERE patient_id = %s LIMIT 1"

        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(query, (patient_id,))
            return cur.fetchone() is not None


def get_patient_repository() -> PatientRepository:
    """
    Factory function para obter instância do repositório.

    Usada para dependency injection no FastAPI.
    """
    return PatientRepository()
