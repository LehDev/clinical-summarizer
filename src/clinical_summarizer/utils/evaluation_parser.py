"""
Parser para dados de evaluations_raw da tabela visits.

Os dados vêm como uma string contendo múltiplos arrays JSON separados por ", ".
Cada array representa uma seção de avaliação com campos e valores.

Estrutura de cada campo:
{
    "id": int,
    "name": str,           # Nome do campo (ex: "Nível de Consciência")
    "fieldTypeId": int,    # Tipo do campo (6=select, 9=text, 10=textarea, 11=date, etc)
    "value": any,          # Valor do campo
    "groupId": int|null,   # ID do grupo (para campos agrupados)
    "repeated": int|null,  # Indica se é campo repetido
    "dependence": int|null,
    "dependenceConditionId": int|null,
    "sessionId": int
}

Tipos de campo (fieldTypeId):
    6  = Select (valor é o ID da opção selecionada)
    7  = Multi-select (valor é lista de IDs)
    9  = Texto curto
    10 = Texto longo (textarea)
    11 = Data (ISO format)
    12 = Imagem/Arquivo
    13 = Número
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvaluationField:
    """Representa um campo de avaliação."""

    id: int
    name: str
    field_type_id: int
    value: Any
    group_id: int | None = None
    repeated: int | None = None
    dependence: int | None = None
    dependence_condition_id: int | None = None
    session_id: int = 1

    @property
    def field_type_name(self) -> str:
        """Retorna o nome legível do tipo de campo."""
        types = {
            6: "select",
            7: "multi_select",
            9: "text",
            10: "textarea",
            11: "date",
            12: "file",
            13: "number",
        }
        return types.get(self.field_type_id, "unknown")

    @property
    def has_value(self) -> bool:
        """Verifica se o campo tem valor preenchido."""
        if self.value is None:
            return False
        if isinstance(self.value, str) and not self.value.strip():
            return False
        if isinstance(self.value, list) and len(self.value) == 0:
            return False
        return True

    def get_formatted_value(self) -> str | None:
        """Retorna o valor formatado como string legível."""
        if not self.has_value:
            return None

        # Data ISO -> formato legível
        if self.field_type_id == 11 and isinstance(self.value, str):
            try:
                dt = datetime.fromisoformat(self.value.replace("Z", "+00:00"))
                return dt.strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                return str(self.value)

        # Lista (multi-select ou repeated)
        if isinstance(self.value, list):
            # Ignora listas de arquivos/imagens
            if self.field_type_id == 12:
                return f"[{len(self.value)} arquivo(s)]"
            # Lista de valores
            return ", ".join(str(v) for v in self.value if v)

        return str(self.value)


@dataclass
class EvaluationSection:
    """Representa uma seção de avaliação (um array de campos)."""

    fields: list[EvaluationField] = field(default_factory=list)

    def get_fields_with_values(self) -> list[EvaluationField]:
        """Retorna apenas campos que têm valor preenchido."""
        return [f for f in self.fields if f.has_value]

    def to_dict(self) -> dict[str, Any]:
        """Converte a seção para dicionário nome->valor."""
        result = {}
        for f in self.get_fields_with_values():
            formatted = f.get_formatted_value()
            if formatted:
                result[f.name] = formatted
        return result

    def to_text(self) -> str:
        """Converte a seção para texto legível."""
        lines = []
        for f in self.get_fields_with_values():
            formatted = f.get_formatted_value()
            if formatted:
                lines.append(f"- {f.name}: {formatted}")
        return "\n".join(lines)


@dataclass
class ParsedEvaluation:
    """Resultado do parsing de evaluations_raw."""

    sections: list[EvaluationSection] = field(default_factory=list)
    raw_data: str | None = None
    parse_errors: list[str] = field(default_factory=list)

    @property
    def total_fields(self) -> int:
        """Total de campos em todas as seções."""
        return sum(len(s.fields) for s in self.sections)

    @property
    def total_filled_fields(self) -> int:
        """Total de campos preenchidos."""
        return sum(len(s.get_fields_with_values()) for s in self.sections)

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário com todas as seções."""
        result = {
            "total_sections": len(self.sections),
            "total_fields": self.total_fields,
            "total_filled_fields": self.total_filled_fields,
            "sections": [],
        }
        for i, section in enumerate(self.sections):
            section_data = section.to_dict()
            if section_data:  # Só inclui seções com dados
                result["sections"].append({
                    "section_index": i,
                    "fields": section_data,
                })
        return result

    def to_text(self) -> str:
        """Converte para texto legível (útil para RAG)."""
        parts = []
        for i, section in enumerate(self.sections):
            text = section.to_text()
            if text:
                parts.append(f"=== Seção {i + 1} ===\n{text}")
        return "\n\n".join(parts)

    def get_all_fields_dict(self) -> dict[str, str]:
        """Retorna todos os campos como um único dicionário."""
        result = {}
        for section in self.sections:
            result.update(section.to_dict())
        return result


def parse_evaluations_raw(raw_data: str | None) -> ParsedEvaluation:
    """
    Faz o parse da coluna evaluations_raw.

    Args:
        raw_data: String contendo os dados JSON das avaliações.

    Returns:
        ParsedEvaluation com as seções parseadas.

    Exemplo de entrada:
        '[[{"id":1,"name":"Campo1",...}], [{"id":2,"name":"Campo2",...}]]'
    """
    result = ParsedEvaluation(raw_data=raw_data)

    if not raw_data or not raw_data.strip():
        return result

    try:
        # Tenta parsear como JSON direto (formato mais comum)
        # O formato parece ser: [[...]], [[...]], [[...]]
        # Isso é uma string com múltiplos arrays separados por ", "

        # Remove espaços extras e tenta identificar o formato
        cleaned = raw_data.strip()

        # Se começa com [[ e termina com ]], tenta parsear
        if cleaned.startswith("[[") and cleaned.endswith("]]"):
            # Divide por "]], [[" para separar as seções
            # Primeiro, vamos tentar parsear como um array de arrays
            sections_raw = _split_json_arrays(cleaned)

            for section_str in sections_raw:
                try:
                    section_data = json.loads(section_str)
                    section = _parse_section(section_data)
                    result.sections.append(section)
                except json.JSONDecodeError as e:
                    result.parse_errors.append(f"Erro ao parsear seção: {e}")

        else:
            # Tenta parsear como JSON simples
            data = json.loads(cleaned)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list):
                        section = _parse_section(item)
                        result.sections.append(section)

    except json.JSONDecodeError as e:
        logger.warning("Erro ao parsear evaluations_raw: %s", e)
        result.parse_errors.append(f"JSON inválido: {e}")
    except Exception as e:
        logger.error("Erro inesperado ao parsear evaluations_raw: %s", e)
        result.parse_errors.append(f"Erro inesperado: {e}")

    return result


def _split_json_arrays(data: str) -> list[str]:
    """
    Divide a string em arrays JSON individuais.

    Entrada: '[[{...}]], [[{...}]], [[{...}]]'
    Saída: ['[[{...}]]', '[[{...}]]', '[[{...}]]']
    """
    # Usa regex para encontrar padrões [[...]]
    pattern = r'\[\[.*?\]\]'
    matches = re.findall(pattern, data, re.DOTALL)

    if matches:
        return matches

    # Fallback: retorna a string original em uma lista
    return [data]


def _parse_section(data: list) -> EvaluationSection:
    """Parseia uma seção (lista de campos)."""
    section = EvaluationSection()

    # Pode ser [[{...}]] ou [{...}]
    fields_list = data[0] if data and isinstance(data[0], list) else data

    for item in fields_list:
        if isinstance(item, dict):
            try:
                field = EvaluationField(
                    id=item.get("id", 0),
                    name=item.get("name", ""),
                    field_type_id=item.get("fieldTypeId", 0),
                    value=item.get("value"),
                    group_id=item.get("groupId"),
                    repeated=item.get("repeated"),
                    dependence=item.get("dependence"),
                    dependence_condition_id=item.get("dependenceConditionId"),
                    session_id=item.get("sessionId", 1),
                )
                section.fields.append(field)
            except Exception as e:
                logger.warning("Erro ao parsear campo: %s - %s", item, e)

    return section


# =============================================================================
# Funções para limpar dados de questões (novo formato)
# =============================================================================


@dataclass
class CleanedQuestion:
    """Representa uma questão limpa e formatada."""

    question_id: int
    question_name: str
    value: str
    field_type_id: int

    def to_dict(self) -> dict[str, Any]:
        """Converte para dicionário."""
        return {
            "question_id": self.question_id,
            "question_name": self.question_name,
            "value": self.value,
            "fieldTypeId": self.field_type_id,
        }


@dataclass
class CleanedQuestionsResult:
    """Resultado da limpeza de questões."""

    questions: list[CleanedQuestion] = field(default_factory=list)
    total_original: int = 0
    total_removed: int = 0
    parse_errors: list[str] = field(default_factory=list)

    def to_dict_list(self) -> list[dict[str, Any]]:
        """Retorna lista de dicionários."""
        return [q.to_dict() for q in self.questions]

    def to_name_value_dict(self) -> dict[str, str]:
        """Retorna dicionário question_name -> value."""
        result = {}
        for q in self.questions:
            # Se houver duplicatas, mantém o último valor
            result[q.question_name] = q.value
        return result

    def to_text(self) -> str:
        """Retorna texto formatado."""
        lines = []
        for q in self.questions:
            lines.append(f"- {q.question_name}: {q.value}")
        return "\n".join(lines)


def _is_empty_value(value: Any) -> bool:
    """
    Verifica se o valor deve ser considerado vazio/nulo.

    Retorna True para:
    - None
    - "null" (string)
    - "" (string vazia)
    - strings só com espaços
    - listas vazias
    """
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip().lower()
        if stripped == "" or stripped == "null":
            return True
    if isinstance(value, list) and len(value) == 0:
        return True
    return False


def clean_questions_data(raw_data: str | None) -> CleanedQuestionsResult:
    """
    Limpa dados de questões removendo objetos com value nulo ou vazio.

    Formato esperado:
    [
        {"question_id": 123, "question_name": "Campo", "value": "Valor", "fieldTypeId": 9},
        ...
    ]

    Remove objetos onde value é:
    - None
    - "null" (string)
    - "" (string vazia)

    Args:
        raw_data: String JSON com array de questões.

    Returns:
        CleanedQuestionsResult com questões limpas e estatísticas.
    """
    result = CleanedQuestionsResult()

    if not raw_data or not raw_data.strip():
        return result

    try:
        data = json.loads(raw_data.strip())

        if not isinstance(data, list):
            result.parse_errors.append("Dados não são uma lista")
            return result

        result.total_original = len(data)
        seen_ids = set()  # Para remover duplicatas

        for item in data:
            if not isinstance(item, dict):
                continue

            value = item.get("value")
            question_id = item.get("question_id", 0)

            # Pula se valor é vazio/nulo
            if _is_empty_value(value):
                result.total_removed += 1
                continue

            # Pula duplicatas (mesmo question_id)
            if question_id in seen_ids:
                result.total_removed += 1
                continue

            seen_ids.add(question_id)

            # Cria questão limpa
            question = CleanedQuestion(
                question_id=question_id,
                question_name=item.get("question_name", "").strip(),
                value=str(value).strip() if value is not None else "",
                field_type_id=item.get("fieldTypeId", 0),
            )
            result.questions.append(question)

    except json.JSONDecodeError as e:
        logger.warning("Erro ao parsear questions data: %s", e)
        result.parse_errors.append(f"JSON inválido: {e}")
    except Exception as e:
        logger.error("Erro inesperado ao limpar questions data: %s", e)
        result.parse_errors.append(f"Erro inesperado: {e}")

    return result
