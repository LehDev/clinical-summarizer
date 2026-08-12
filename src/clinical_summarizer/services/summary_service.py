"""
Serviço de Resumos Clínicos - orquestração de RAG com LLM.

Coordena a busca de visitas, geração de resumo via Anthropic Claude,
e persistência do resultado no banco de dados.
"""

import logging
import time
from datetime import date
from decimal import Decimal

import anthropic

from clinical_summarizer.config import get_settings
from clinical_summarizer.exceptions import (
    LLMConnectionError,
    LLMGenerationError,
    NoVisitsFoundError,
)
from clinical_summarizer.models import Summary, Visit
from clinical_summarizer.repositories import (
    SummaryRepository,
    get_summary_repository,
)
from clinical_summarizer.services.etl_service import ETLService, get_etl_service
from clinical_summarizer.services.visit_service import VisitService, get_visit_service

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Você é um assistente médico especializado em análise de prontuários clínicos.
Sua tarefa é gerar resumos clínicos concisos e informativos a partir dos dados de visitas médicas.

Diretrizes:
1. Seja objetivo e use terminologia médica apropriada
2. Organize as informações de forma cronológica quando relevante
3. Destaque diagnósticos (CIDs), sintomas principais e tratamentos prescritos
4. Identifique padrões ou evolução do quadro clínico
5. Mantenha a confidencialidade - não adicione informações não presentes nos dados
6. Use formato estruturado com seções claras
7. Escreva em português brasileiro

Formato do resumo:
## Resumo Clínico

### Período Analisado
[Datas do período]

### Diagnósticos (CID)
[Lista de CIDs com descrições]

### Histórico de Atendimentos
[Resumo cronológico das visitas]

### Sintomas e Queixas Principais
[Sintomas relatados]

### Tratamentos e Prescrições
[Medicamentos e procedimentos]

### Observações Relevantes
[Outros pontos importantes]
"""


def _format_visit_for_prompt(visit: Visit) -> str:
    """Formata uma visita para incluir no prompt do LLM."""
    parts = [f"### Visita em {visit.visit_date}"]

    if visit.cid_codes and visit.cid_names:
        parts.append(f"**CIDs:** {visit.cid_codes} - {visit.cid_names}")

    if visit.sign_symptoms:
        parts.append(f"**Sinais/Sintomas:** {visit.sign_symptoms}")

    if visit.clinical_evolutions:
        parts.append(f"**Evolução Clínica:** {visit.clinical_evolutions}")

    if visit.prescriptions:
        parts.append(f"**Prescrições:** {visit.prescriptions}")

    return "\n".join(parts)


def _build_user_prompt(visits: list[Visit], start_date: date, end_date: date) -> str:
    """Constrói o prompt do usuário com os dados das visitas."""
    visits_text = "\n\n".join(_format_visit_for_prompt(v) for v in visits)

    return f"""Analise os dados das visitas médicas abaixo e gere um resumo clínico estruturado.

## Dados das Visitas ({len(visits)} visitas entre {start_date} e {end_date})

{visits_text}

---
Por favor, gere o resumo clínico seguindo o formato especificado."""


class SummaryService:
    """
    Serviço para geração de resumos clínicos via LLM.

    Orquestra:
    1. Execução do ETL (Pentaho) para carregar dados frescos
    2. Busca de visitas do paciente
    3. Construção do prompt
    4. Chamada à API do Anthropic Claude
    5. Persistência do resumo no banco
    """

    def __init__(
        self,
        visit_service: VisitService | None = None,
        summary_repository: SummaryRepository | None = None,
        etl_service: ETLService | None = None,
    ):
        self._visit_service = visit_service or get_visit_service()
        self._summary_repo = summary_repository or get_summary_repository()
        self._etl_service = etl_service or get_etl_service()
        self._settings = get_settings()

        if self._settings.anthropic_api_key:
            self._client = anthropic.Anthropic(
                api_key=self._settings.anthropic_api_key
            )
        else:
            self._client = None

    def generate_summary(
        self,
        patient_id: str,
        start_date: date,
        end_date: date,
        run_etl: bool = True,
    ) -> Summary:
        """
        Gera um resumo clínico para um paciente.

        Args:
            patient_id: ID original do paciente.
            start_date: Data inicial do período.
            end_date: Data final do período.
            run_etl: Se True, executa o ETL antes de buscar dados.

        Returns:
            Objeto Summary com o resumo gerado e metadados.

        Raises:
            NoVisitsFoundError: Se não houver visitas no período.
            LLMConnectionError: Se não conseguir conectar ao LLM.
            LLMGenerationError: Se houver erro na geração.
        """
        if not self._client:
            raise LLMConnectionError(
                "ANTHROPIC_API_KEY não configurada. "
                "Adicione ao arquivo .env"
            )

        # 1. Executar ETL para carregar dados frescos
        if run_etl:
            logger.info("Executando ETL para paciente %s...", patient_id)
            etl_result = self._etl_service.run_pipeline(
                start_date=start_date,
                end_date=end_date,
                patient_id=int(patient_id),
            )
            if etl_result.success:
                logger.info(
                    "ETL concluído: %d visitas carregadas",
                    etl_result.etl_log.records_loaded_visits if etl_result.etl_log else 0,
                )
            else:
                logger.warning("ETL falhou: %s", etl_result.message)

        # 2. Buscar visitas do paciente
        visits = self._visit_service.get_patient_visits(
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
        )

        if not visits:
            raise NoVisitsFoundError(patient_id, str(start_date), str(end_date))

        # 2. Construir prompt
        user_prompt = _build_user_prompt(visits, start_date, end_date)

        # 3. Chamar LLM
        start_time = time.time()
        try:
            response = self._client.messages.create(
                model=self._settings.anthropic_model,
                max_tokens=self._settings.anthropic_max_tokens,
                temperature=self._settings.anthropic_temperature,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
        except anthropic.APIConnectionError as e:
            logger.error("Erro de conexão com Anthropic: %s", e)
            raise LLMConnectionError(f"Erro de conexão: {e}") from e
        except anthropic.APIError as e:
            logger.error("Erro da API Anthropic: %s", e)
            raise LLMGenerationError(f"Erro na API: {e}") from e

        generation_duration_ms = int((time.time() - start_time) * 1000)

        # 4. Extrair resultado
        summary_text = response.content[0].text

        # 5. Obter hash do patient_id (mesmo usado nas visitas)
        from clinical_summarizer.utils import hash_id
        patient_id_hash = hash_id(patient_id)

        # 6. Criar objeto Summary
        visit_ids = ",".join(v.visit_id for v in visits)

        summary = Summary(
            patient_id=patient_id_hash,
            visit_ids=visit_ids,
            filter_start_date=start_date,
            filter_end_date=end_date,
            summary_text=summary_text,
            llm_model=self._settings.anthropic_model,
            llm_prompt_tokens=response.usage.input_tokens,
            llm_completion_tokens=response.usage.output_tokens,
            llm_total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            llm_temperature=Decimal(str(self._settings.anthropic_temperature)),
            generation_duration_ms=generation_duration_ms,
            status="completed",
        )

        # 7. Persistir no banco
        saved_summary = self._summary_repo.create(summary)

        logger.info(
            "Resumo gerado: summary_id=%s, visitas=%d, tokens=%d, tempo=%dms",
            saved_summary.summary_id,
            len(visits),
            saved_summary.llm_total_tokens,
            generation_duration_ms,
        )

        return saved_summary


def get_summary_service() -> SummaryService:
    """Factory function para obter instância do serviço."""
    return SummaryService()
