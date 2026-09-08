"""
Constantes das seções do resumo clínico estruturado.

Centraliza as chaves e rótulos usados tanto na construção do prompt
enviado ao LLM quanto na resposta estruturada da API, garantindo que
backend e frontend compartilhem o mesmo contrato de dados.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


class SummarySection:
    """Chaves (machine-readable) de cada etapa do resumo clínico."""

    TITLE = "resumo_clinico"
    PERIOD = "periodo_analisado"
    DIAGNOSES = "diagnosticos_cid"
    VISIT_HISTORY = "historico_atendimentos"
    SYMPTOMS = "sintomas_queixas_principais"
    OBSERVATIONS = "observacoes_relevantes"


# Chave do campo estruturado (fora de `SUMMARY_CONTENT_SECTIONS`) com a
# distribuição de visitas por período dentro do histórico de atendimentos.
# É consumido diretamente pelo frontend (gráfico) — não é texto livre nem
# precisa ser parseado via regex.
VISIT_PERIODS_KEY = "periodos_visitas"


SUMMARY_SECTION_LABELS: dict[str, str] = {
    SummarySection.TITLE: "Resumo Clínico",
    SummarySection.PERIOD: "Período Analisado",
    SummarySection.DIAGNOSES: "Diagnósticos (CID)",
    SummarySection.VISIT_HISTORY: "Histórico de Atendimentos",
    SummarySection.SYMPTOMS: "Sintomas e Queixas Principais",
    SummarySection.OBSERVATIONS: "Observações Relevantes",
}

# Seções com conteúdo gerado pelo LLM (exclui TITLE, que é fixo).
SUMMARY_CONTENT_SECTIONS: tuple[str, ...] = (
    SummarySection.PERIOD,
    SummarySection.DIAGNOSES,
    SummarySection.VISIT_HISTORY,
    SummarySection.SYMPTOMS,
    SummarySection.OBSERVATIONS,
)

# Rótulos apenas das seções de conteúdo, na mesma ordem de `SUMMARY_CONTENT_SECTIONS`
# (exclui TITLE) — usado para expor ao frontend junto de `sections`.
SUMMARY_CONTENT_SECTION_LABELS: dict[str, str] = {
    key: SUMMARY_SECTION_LABELS[key] for key in SUMMARY_CONTENT_SECTIONS
}

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass(frozen=True)
class VisitPeriod:
    """
    Um período dentro do histórico de atendimentos, com sua contagem de visitas.

    Campo estruturado consumido diretamente pelo frontend (ex: gráfico de
    distribuição de visitas) — evita depender de regex sobre o texto livre
    de `historico_atendimentos`, que pode variar de fraseado a cada geração.
    """

    label: str
    start_date: date
    end_date: date
    visit_count: int
    detail: str | None = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "visit_count": self.visit_count,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VisitPeriod":
        return cls(
            label=str(data["label"]).strip(),
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            visit_count=int(data["visit_count"]),
            detail=str(data["detail"]).strip() if data.get("detail") else None,
        )


def _extract_json(raw_text: str) -> dict:
    """
    Extrai o objeto JSON retornado pelo LLM.

    Aceita tanto um JSON "puro" quanto um JSON envolto em blocos de
    código markdown (```json ... ```), que o modelo às vezes adiciona.

    Raises:
        json.JSONDecodeError: Se o texto não contiver um JSON válido.
    """
    text = _CODE_FENCE_RE.sub("", raw_text.strip())

    match = _JSON_BLOCK_RE.search(text)
    if match:
        text = match.group(0)

    return json.loads(text)


def parse_summary_sections(raw_text: str) -> dict[str, str]:
    """
    Extrai as seções de texto em JSON retornadas pelo LLM.

    Raises:
        json.JSONDecodeError: Se o texto não contiver um JSON válido.
    """
    data = _extract_json(raw_text)
    return {key: str(data.get(key, "")).strip() for key in SUMMARY_CONTENT_SECTIONS}


def parse_summary_sections_safe(raw_text: str) -> dict[str, str]:
    """
    Versão tolerante de `parse_summary_sections`.

    Usada para reconstruir a resposta da API a partir de resumos já
    persistidos. Se o texto não for um JSON válido (ex: resumos gerados
    antes desta estrutura, em markdown livre), o texto inteiro é
    colocado na seção de observações para não quebrar o cliente.
    """
    try:
        return parse_summary_sections(raw_text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        sections = {key: "" for key in SUMMARY_CONTENT_SECTIONS}
        sections[SummarySection.OBSERVATIONS] = raw_text.strip()
        return sections


def parse_visit_periods(raw_text: str) -> list[VisitPeriod]:
    """
    Extrai a distribuição estruturada de visitas por período (`periodos_visitas`).

    Tolerante a entradas individuais malformadas: um período inválido é
    descartado (com log) em vez de invalidar o resumo inteiro, já que este
    campo é um complemento visual e não o conteúdo clínico principal.

    Raises:
        json.JSONDecodeError: Se o texto não contiver um JSON válido.
    """
    data = _extract_json(raw_text)
    raw_periods = data.get(VISIT_PERIODS_KEY) or []

    periods = []
    for entry in raw_periods:
        try:
            periods.append(VisitPeriod.from_dict(entry))
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Período de visitas malformado, descartando: %s (%s)", entry, e)

    return periods


def parse_visit_periods_safe(raw_text: str) -> list[VisitPeriod]:
    """Versão tolerante de `parse_visit_periods`, para resumos já persistidos."""
    try:
        return parse_visit_periods(raw_text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return []


def render_summary_markdown(sections: dict[str, str]) -> str:
    """Reconstrói um texto em markdown legível a partir das seções estruturadas."""
    parts = [f"## {SUMMARY_SECTION_LABELS[SummarySection.TITLE]}"]
    for key in SUMMARY_CONTENT_SECTIONS:
        content = sections.get(key, "").strip()
        if content:
            parts.append(f"### {SUMMARY_SECTION_LABELS[key]}\n\n{content}")
    return "\n\n".join(parts)
