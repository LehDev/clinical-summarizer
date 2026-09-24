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
class VisitDayCount:
    """Quantidade de visitas em um dia específico dentro de um período."""

    visit_date: date
    visit_count: int

    def to_dict(self) -> dict:
        return {
            "visit_date": self.visit_date.isoformat(),
            "visit_count": self.visit_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VisitDayCount":
        return cls(
            visit_date=date.fromisoformat(data["visit_date"]),
            visit_count=int(data["visit_count"]),
        )


@dataclass(frozen=True)
class VisitPeriod:
    """
    Um período dentro do histórico de atendimentos, com sua contagem de visitas
    por dia.

    Campo estruturado consumido diretamente pelo frontend (ex: gráfico de
    distribuição de visitas) — evita depender de regex sobre o texto livre
    de `historico_atendimentos`, que pode variar de fraseado a cada geração.

    `start_date`, `end_date` e `visit_count` são derivados de `days` em vez
    de pedidos ao LLM diretamente: pedir pro modelo agrupar os dias (que já
    recebe prontos no prompt) é confiável, mas pedir pra ele também somar e
    calcular datas de início/fim é aritmética sujeita a erro — como no caso
    de um período com `visit_count=6` cujo `detail` só citava 4 visitas de
    um único dia, sem contabilizar o resto.
    """

    label: str
    days: tuple[VisitDayCount, ...]

    @property
    def start_date(self) -> date:
        return min(day.visit_date for day in self.days)

    @property
    def end_date(self) -> date:
        return max(day.visit_date for day in self.days)

    @property
    def visit_count(self) -> int:
        return sum(day.visit_count for day in self.days)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "visit_count": self.visit_count,
            "days": [day.to_dict() for day in self.days],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VisitPeriod":
        days = tuple(VisitDayCount.from_dict(day) for day in data["days"])
        if not days:
            raise ValueError("Período de visitas sem dias em 'days'")
        return cls(label=str(data["label"]).strip(), days=days)


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
