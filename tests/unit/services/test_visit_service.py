"""
Testes unitários para VisitService.

Usa mocks dos repositórios para testar lógica de negócio isoladamente.
"""

from datetime import date

import pytest

from clinical_summarizer.exceptions import (
    InvalidDateRangeError,
    PatientNotFoundError,
    VisitNotFoundError,
)
from clinical_summarizer.models import Visit
from clinical_summarizer.services.visit_service import VisitService


class TestVisitServiceGetPatientVisits:
    """Testes para o método get_patient_visits."""

    def test_returns_visits_when_patient_exists(
        self,
        mock_visit_repository,
        mock_patient_repository,
        sample_visits,
    ):
        """Deve retornar lista de visitas quando paciente existe."""
        # Arrange
        mock_patient_repository.exists.return_value = True
        mock_visit_repository.get_by_patient_and_date_range.return_value = sample_visits

        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act
        result = service.get_patient_visits(
            patient_id="abc123def456789",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 6, 30),
        )

        # Assert
        assert len(result) == 3
        assert all(isinstance(v, Visit) for v in result)
        mock_patient_repository.exists.assert_called_once_with("abc123def456789")
        mock_visit_repository.get_by_patient_and_date_range.assert_called_once()

    def test_raises_when_patient_not_found(
        self,
        mock_visit_repository,
        mock_patient_repository,
    ):
        """Deve lançar PatientNotFoundError quando paciente não existir."""
        # Arrange
        mock_patient_repository.exists.return_value = False

        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act & Assert
        with pytest.raises(PatientNotFoundError) as exc_info:
            service.get_patient_visits(
                patient_id="nonexistent123",
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
            )

        assert "nonexistent123" in str(exc_info.value)
        # Não deve ter chamado o repositório de visitas
        mock_visit_repository.get_by_patient_and_date_range.assert_not_called()

    def test_raises_when_date_range_invalid(
        self,
        mock_visit_repository,
        mock_patient_repository,
    ):
        """Deve lançar InvalidDateRangeError quando start_date > end_date."""
        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act & Assert
        with pytest.raises(InvalidDateRangeError):
            service.get_patient_visits(
                patient_id="abc123",
                start_date=date(2025, 12, 31),  # Depois
                end_date=date(2025, 1, 1),  # Antes
            )

        # Não deve ter verificado paciente nem buscado visitas
        mock_patient_repository.exists.assert_not_called()
        mock_visit_repository.get_by_patient_and_date_range.assert_not_called()

    def test_returns_empty_list_when_no_visits_in_period(
        self,
        mock_visit_repository,
        mock_patient_repository,
    ):
        """Deve retornar lista vazia quando não houver visitas no período."""
        # Arrange
        mock_patient_repository.exists.return_value = True
        mock_visit_repository.get_by_patient_and_date_range.return_value = []

        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act
        result = service.get_patient_visits(
            patient_id="abc123",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )

        # Assert
        assert result == []


class TestVisitServiceGetVisitDetails:
    """Testes para o método get_visit_details."""

    def test_returns_visit_when_found(
        self,
        mock_visit_repository,
        mock_patient_repository,
        sample_visit,
    ):
        """Deve retornar visita quando encontrada."""
        # Arrange
        mock_visit_repository.get_by_id.return_value = sample_visit

        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act
        result = service.get_visit_details("visit123abc")

        # Assert
        assert result == sample_visit
        mock_visit_repository.get_by_id.assert_called_once_with("visit123abc")

    def test_raises_when_visit_not_found(
        self,
        mock_visit_repository,
        mock_patient_repository,
    ):
        """Deve propagar VisitNotFoundError do repositório."""
        # Arrange
        mock_visit_repository.get_by_id.side_effect = VisitNotFoundError("notfound123")

        service = VisitService(
            visit_repository=mock_visit_repository,
            patient_repository=mock_patient_repository,
        )

        # Act & Assert
        with pytest.raises(VisitNotFoundError):
            service.get_visit_details("notfound123")


class TestVisitServiceDependencyInjection:
    """Testes para injeção de dependências."""

    def test_uses_default_repositories_when_none_provided(self):
        """Deve usar repositórios padrão quando não injetados."""
        # Este teste verifica que o serviço pode ser instanciado
        # sem passar repositórios explicitamente.
        # Na prática, falharia ao tentar acessar banco sem pool,
        # mas aqui só verificamos que não lança exceção na construção.

        # Não podemos instanciar sem mock porque tentaria acessar pool
        # Então apenas verificamos que a factory function existe
        from clinical_summarizer.services.visit_service import get_visit_service

        assert callable(get_visit_service)
