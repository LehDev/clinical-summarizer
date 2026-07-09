"""
Fixtures compartilhadas para testes.

Este arquivo é automaticamente carregado pelo pytest.
Fixtures definidas aqui estão disponíveis em todos os testes.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from clinical_summarizer.models import Patient, Visit

# =============================================================================
# Fixtures de Dados de Teste
# =============================================================================


@pytest.fixture
def sample_patient() -> Patient:
    """Retorna um paciente de exemplo para testes."""
    return Patient(
        patient_id="abc123def456789",
        age=45,
        gender="F",
        created_at=datetime(2025, 1, 1, 10, 0, 0),
        updated_at=datetime(2025, 1, 1, 10, 0, 0),
    )


@pytest.fixture
def sample_visit() -> Visit:
    """Retorna uma visita de exemplo para testes."""
    return Visit(
        visit_id="visit123abc",
        patient_id="abc123def456789",
        visit_date=date(2025, 6, 15),
        cid_codes="J06.9;J11.1",
        cid_names="Infecção respiratória aguda;Influenza",
        clinical_evolutions="Paciente apresentou melhora",
        sign_symptoms="Febre, tosse, dor de garganta",
        prescriptions="Dipirona 500mg",
        evaluations_raw='{"tipo": "consulta"}',
        evaluation_types="consulta",
        created_at=datetime(2025, 6, 15, 14, 30, 0),
    )


@pytest.fixture
def sample_visits() -> list[Visit]:
    """Retorna uma lista de visitas de exemplo para testes."""
    return [
        Visit(
            visit_id="visit001",
            patient_id="abc123def456789",
            visit_date=date(2025, 6, 15),
            cid_codes="J06.9",
            cid_names="Infecção respiratória aguda",
        ),
        Visit(
            visit_id="visit002",
            patient_id="abc123def456789",
            visit_date=date(2025, 6, 10),
            cid_codes="J11.1",
            cid_names="Influenza",
        ),
        Visit(
            visit_id="visit003",
            patient_id="abc123def456789",
            visit_date=date(2025, 5, 20),
            cid_codes="R50.9",
            cid_names="Febre não especificada",
        ),
    ]


# =============================================================================
# Fixtures de Mocks
# =============================================================================


@pytest.fixture
def mock_visit_repository():
    """
    Retorna um mock do VisitRepository.

    Uso:
        def test_algo(mock_visit_repository):
            mock_visit_repository.get_by_id.return_value = Visit(...)
    """
    return MagicMock()


@pytest.fixture
def mock_patient_repository():
    """Retorna um mock do PatientRepository."""
    return MagicMock()


# =============================================================================
# Fixtures para Testes de API
# =============================================================================


@pytest.fixture
def mock_pool():
    """
    Mock do pool de conexões para testes de API.

    Evita que os testes tentem conectar ao banco real.
    """
    with patch("clinical_summarizer.repositories.base._pool") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def test_client(mock_pool):
    """
    Cliente de teste para endpoints FastAPI.

    Usa mock do pool de conexões para não depender de banco real.

    Uso:
        def test_endpoint(test_client):
            response = test_client.get("/health")
            assert response.status_code == 200
    """
    # Importa aqui para evitar inicialização prematura
    from clinical_summarizer.main import app

    # Patch do init_pool para não tentar conectar ao banco
    with patch("clinical_summarizer.main.init_pool"):
        with patch("clinical_summarizer.main.close_pool"):
            with TestClient(app) as client:
                yield client
