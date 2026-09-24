"""
Serviço de Resumos Clínicos - orquestração de RAG com LLM.

Coordena a busca de visitas, geração de resumo via Anthropic Claude,
e persistência do resultado no banco de dados.
"""

import json
import logging
import time
from collections import Counter
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
from clinical_summarizer.services.summary_sections import (
    SUMMARY_CONTENT_SECTIONS,
    SUMMARY_SECTION_LABELS,
    VISIT_PERIODS_KEY,
    parse_summary_sections,
    parse_visit_periods,
)
from clinical_summarizer.services.visit_service import VisitService, get_visit_service

logger = logging.getLogger(__name__)

# Aliases locais para as chaves/rótulos das seções, evitando repetir
# `SummarySection.X` / `SUMMARY_SECTION_LABELS[...]` ao montar o prompt.
_PERIOD, _DIAGNOSES, _VISIT_HISTORY, _SYMPTOMS, _OBSERVATIONS = SUMMARY_CONTENT_SECTIONS
_LABEL = SUMMARY_SECTION_LABELS

_SUMMARY_JSON_EXAMPLE = json.dumps(
    {
        **{key: f"<{_LABEL[key]}>" for key in SUMMARY_CONTENT_SECTIONS},
        VISIT_PERIODS_KEY: [
            {
                "label": "Primeira semana",
                "days": [
                    {"visit_date": "2023-04-01", "visit_count": 2},
                    {"visit_date": "2023-04-03", "visit_count": 4},
                ],
            },
            {
                "label": "Segunda semana",
                "days": [
                    {"visit_date": "2023-04-10", "visit_count": 3},
                    {"visit_date": "2023-04-13", "visit_count": 2},
                ],
            },
        ],
    },
    ensure_ascii=False,
    indent=2,
)

SYSTEM_PROMPT = f"""Você é um assistente médico especializado em análise de prontuários clínicos.
Sua tarefa é gerar resumos clínicos concisos e informativos a partir dos dados de visitas médicas.

Diretrizes:
1. Seja objetivo e use terminologia médica apropriada
2. Organize as informações de forma cronológica quando relevante
3. Destaque diagnósticos (CIDs), sintomas principais e tratamentos prescritos
4. Identifique padrões ou evolução do quadro clínico
5. Mantenha a confidencialidade - não adicione informações não presentes nos dados
6. Escreva em português brasileiro
7. Se as informações forem insuficientes, sugira fazer outra pesquisa alterando as datas para que outras visitas sejam analisadas

Formato de resposta:
Responda APENAS com um objeto JSON válido (sem texto antes ou depois, sem blocos de
código markdown), contendo exatamente estas chaves:

- "{_PERIOD}": {_LABEL[_PERIOD]} (datas do período)
- "{_DIAGNOSES}": {_LABEL[_DIAGNOSES]} (lista de CIDs com descrições)
- "{_VISIT_HISTORY}": {_LABEL[_VISIT_HISTORY]} (resumo cronológico das visitas)
- "{_SYMPTOMS}": {_LABEL[_SYMPTOMS]} (sintomas relatados)
- "{_OBSERVATIONS}": {_LABEL[_OBSERVATIONS]} (outros pontos importantes)
- "{VISIT_PERIODS_KEY}": lista opcional de objetos agrupando, em períodos com
  sentido clínico/temporal, os dias de visita já listados em "Distribuição de
  Visitas por Dia" abaixo — para o frontend renderizar um gráfico (dado
  estruturado — não repita esses números como texto livre em
  "{_VISIT_HISTORY}", apenas descreva o histórico normalmente lá).
  Agrupe TODOS os dias com visita em algum período, sem deixar nenhum de
  fora. Cada objeto deve conter exatamente estas chaves:
    - "label": rótulo curto do período (ex: "Primeira semana", "Início do mês");
      não precisa ser literalmente uma semana, use o que descrever melhor
    - "days": lista de objetos {{"visit_date": "AAAA-MM-DD", "visit_count": N}},
      um para cada dia do período — copie as datas e contagens exatamente
      da "Distribuição de Visitas por Dia" informada, não invente nem
      recalcule números (data inicial, final e total do período são
      derivados automaticamente a partir desta lista)

Cada valor de seção de texto deve ser uma string simples (use "\\n" para quebras
de linha e "-" para listas).

Exemplo de formato (apenas ilustrativo):
{_SUMMARY_JSON_EXAMPLE}
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


    return "\n".join(parts)


def _format_visits_by_day(visits: list[Visit]) -> str:
    """Conta as visitas por dia e formata a distribuição para o prompt."""
    counts = Counter(v.visit_date for v in visits if v.visit_date is not None)
    lines = [
        f"- {day.strftime('%d/%m/%Y')}: {count} visita(s)"
        for day, count in sorted(counts.items())
    ]
    return "\n".join(lines)


def _build_user_prompt(visits: list[Visit], start_date: date, end_date: date) -> str:
    """Constrói o prompt do usuário com os dados das visitas."""
    visits_text = "\n\n".join(_format_visit_for_prompt(v) for v in visits)
    visits_by_day = _format_visits_by_day(visits)

    return f"""Analise os dados das visitas médicas abaixo e gere um resumo clínico estruturado.

## Dados das Visitas ({len(visits)} visitas entre {start_date} e {end_date})

### Distribuição de Visitas por Dia
{visits_by_day}

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

        # 4. Extrair e validar o resultado estruturado (JSON por seção)
        llm_text = response.content[0].text
        try:
            sections = parse_summary_sections(llm_text)
        except json.JSONDecodeError as e:
            logger.error("Resposta do LLM não é um JSON válido: %s", e)
            raise LLMGenerationError(
                f"Formato de resposta inválido do LLM: {e}"
            ) from e

        # Campo estruturado (não é texto livre) com a distribuição de visitas
        # por período — entradas malformadas são descartadas individualmente
        # por `parse_visit_periods`, sem invalidar o resumo inteiro.
        visit_periods = parse_visit_periods(llm_text)

        # Persistimos os dados já estruturados (JSON por seção + períodos)
        # para que o frontend consiga renderizar cada etapa do resumo e o
        # gráfico de distribuição separadamente.
        summary_text = json.dumps(
            {**sections, VISIT_PERIODS_KEY: [p.to_dict() for p in visit_periods]},
            ensure_ascii=False,
        )

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
