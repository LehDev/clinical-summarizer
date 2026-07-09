"""
Testes unitários para VisitRepository.

Usa mocks para simular conexão com banco de dados.
Testes focam na lógica do repositório, não na integração com PostgreSQL.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from clinical_summarizer.exceptions import VisitNotFoundError
from clinical_summarizer.models import Visit
from clinical_summarizer.repositories.visit_repository import VisitRepository


class TestVisitRepositoryGetById:
    """Testes para o método get_by_id."""

    def test_get_by_id_returns_visit_when_found(self):
        """Deve retornar Visit quando encontrar no banco."""
        # Arrange: dados simulados do banco
        mock_row = {
            "visit_id": "visit123",
            "patient_id": "patient456",
            "visit_date": date(2025, 6, 15),
            "cid_codes": "J06.9",
            "cid_names": "Infecção respiratória",
            "clinical_evolutions": "Evolução do paciente",
            "sign_symptoms": "Febre, tosse",
            "prescriptions": "Dipirona 500mg",
            "evaluations_raw": '{"tipo": "consulta"}',
            "evaluation_types": "consulta",
            "created_at": datetime(2025, 6, 15, 10, 0, 0),
        }

        # Mock da conexão e cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = mock_row
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch(
            "clinical_summarizer.repositories.visit_repository.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            # Act
            repo = VisitRepository()
            result = repo.get_by_id("visit123")

        # Assert
        assert isinstance(result, Visit)
        assert result.visit_id == "visit123"
        assert result.patient_id == "patient456"
        assert result.cid_codes == "J06.9"

    def test_get_by_id_raises_when_not_found(self):
        """Deve lançar VisitNotFoundError quando visita não existir."""
        # Mock retornando None (não encontrado)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch(
            "clinical_summarizer.repositories.visit_repository.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            repo = VisitRepository()

            # Assert: deve lançar exceção
            with pytest.raises(VisitNotFoundError) as exc_info:
                repo.get_by_id("nonexistent123")

            assert "nonexistent123" in str(exc_info.value)


class TestVisitRepositoryGetByPatientAndDateRange:
    """Testes para o método get_by_patient_and_date_range."""

    def test_returns_list_of_visits_when_found(self):
        """Deve retornar lista de visitas quando encontrar no período."""
        # Arrange
        mock_rows = [
            {
                "visit_id": "visit001",
                "patient_id": "patient123",
                "visit_date": date(2025, 6, 15),
                "cid_codes": "J06.9",
                "cid_names": "Infecção",
                "clinical_evolutions": None,
                "sign_symptoms": None,
                "prescriptions": None,
                "evaluations_raw": None,
                "evaluation_types": None,
                "created_at": None,
            },
            {
                "visit_id": "visit002",
                "patient_id": "patient123",
                "visit_date": date(2025, 6, 10),
                "cid_codes": "J11.1",
                "cid_names": "Influenza",
                "clinical_evolutions": None,
                "sign_symptoms": None,
                "prescriptions": None,
                "evaluations_raw": None,
                "evaluation_types": None,
                "created_at": None,
            },
        ]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch(
            "clinical_summarizer.repositories.visit_repository.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            # Act
            repo = VisitRepository()
            result = repo.get_by_patient_and_date_range(
                patient_id="patient123",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 30),
            )

        # Assert
        assert len(result) == 2
        assert all(isinstance(v, Visit) for v in result)
        assert result[0].visit_id == "visit001"
        assert result[1].visit_id == "visit002"

    def test_returns_empty_list_when_no_visits(self):
        """Deve retornar lista vazia quando não houver visitas no período."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch(
            "clinical_summarizer.repositories.visit_repository.get_connection"
        ) as mock_get_conn:
            mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

            repo = VisitRepository()
            result = repo.get_by_patient_and_date_range(
                patient_id="patient123",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
            )

        assert result == []
