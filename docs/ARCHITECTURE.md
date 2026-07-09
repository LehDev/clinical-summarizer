# Arquitetura do Clinical Summarizer

Este documento descreve as decisões arquiteturais do projeto, servindo como
referência técnica para a banca e futuros desenvolvedores.

## Visão Geral

O **Clinical Summarizer** é um serviço Python que:

1. Lê dados clínicos anonimizados de um PostgreSQL (camada Gold do pipeline ETL)
2. Aplica transformações (correção de encoding, parsing de JSON)
3. Gera resumos clínicos automatizados via Google Gemini (LLM)
4. Persiste os resumos e logs de execução

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                    │
│              Endpoints, validação de entrada                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    Service Layer                            │
│         Orquestração, regras de negócio, chamada LLM        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                  Repository Layer                           │
│           Acesso a dados, queries, connection pool          │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     PostgreSQL                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Decisões Arquiteturais

### 1. Padrão Arquitetural: Layered Architecture

**Decisão:** Adotar Layered Architecture (arquitetura em camadas) simplificada.

**Alternativas consideradas:**
- Hexagonal Architecture (Ports & Adapters)
- Clean Architecture
- MVC tradicional

**Justificativa:**

| Critério | Hexagonal/Clean | Layered (escolhida) |
|----------|-----------------|---------------------|
| Complexidade | Alta | Média |
| Curva de aprendizado | Íngreme | Suave |
| Overhead de código | Muitas abstrações | Mínimo |
| Testabilidade | Excelente | Boa |
| Adequação para TCC | Difícil defender | Fácil defender |

Para um serviço com 2-3 endpoints e prazo de TCC, a complexidade adicional de
Hexagonal/Clean Architecture não se justifica. Layered Architecture oferece:

- Separação clara de responsabilidades
- Facilidade de testes com mocks
- Padrão amplamente reconhecido na indústria
- Evolução natural para arquiteturas mais complexas se necessário

**Citação para a banca:**
> "Layered Architecture é um padrão consolidado que oferece separação adequada
> de concerns para o escopo deste projeto. A escolha privilegia simplicidade
> e manutenibilidade sobre abstrações prematuras."

---

### 2. Gerenciador de Dependências: uv

**Decisão:** Usar `uv` como gerenciador de dependências principal.

**Alternativas consideradas:**
- pip + requirements.txt
- Poetry
- PDM

**Justificativa:**

| Critério | pip | Poetry | uv (escolhido) |
|----------|-----|--------|----------------|
| Velocidade | Lenta | Média | 10-100x mais rápido |
| Lock file | Não nativo | Sim | Sim |
| Reprodutibilidade | Fraca | Boa | Boa |
| Compatibilidade | Universal | Boa | Boa + fallback pip |

O `uv` foi escolhido por ser:
- Extremamente rápido (desenvolvido em Rust)
- Compatível com `pyproject.toml` padrão (PEP 517/518)
- Fácil fallback para pip caso necessário

**Fallback para a banca:** Incluímos `requirements.txt` para instalação via pip
caso o avaliador não tenha uv instalado.

---

### 3. Driver PostgreSQL: psycopg3

**Decisão:** Usar `psycopg` (versão 3) com pool de conexões nativo.

**Alternativas consideradas:**
- psycopg2
- asyncpg
- SQLAlchemy

**Justificativa:**

- **psycopg3** é o driver moderno, com suporte nativo a:
  - Connection pooling (`psycopg_pool`)
  - Async (preparado para futuro)
  - Tipagem moderna
- **psycopg2** é legacy e requer compilação em algumas plataformas
- **SQLAlchemy** adicionaria complexidade desnecessária para queries simples
- **asyncpg** é excelente, mas forçaria código async em toda a stack

---

### 4. Validação e Configuração: Pydantic

**Decisão:** Usar Pydantic para validação de entrada e configuração.

**Justificativa:**

- FastAPI já inclui Pydantic como dependência
- `pydantic-settings` carrega `.env` com validação de tipos
- Documentação automática via OpenAPI/Swagger
- Ecossistema maduro e bem documentado

---

### 5. Estrutura de Pastas

```
clinical-summarizer/
├── src/
│   └── clinical_summarizer/
│       ├── api/              # Camada de apresentação
│       │   ├── routes/       # Endpoints organizados por recurso
│       │   ├── schemas.py    # Modelos Pydantic (request/response)
│       │   └── dependencies.py
│       ├── services/         # Lógica de negócio
│       ├── repositories/     # Acesso a dados
│       ├── models/           # Modelos de domínio (dataclasses)
│       ├── config.py         # Configurações
│       ├── exceptions.py     # Exceções customizadas
│       └── main.py           # Entrypoint FastAPI
├── tests/
│   ├── unit/                 # Testes unitários
│   └── integration/          # Testes de integração (futuro)
└── docs/                     # Documentação
```

**Por que `src/` layout:**
- Evita imports acidentais do diretório local
- Padrão recomendado pela comunidade Python
- Facilita empacotamento se necessário

---

### 6. Tratamento de Erros

**Decisão:** Hierarquia de exceções customizadas mapeadas para HTTP.

```
ClinicalSummarizerError (base)
├── DatabaseError → 500
│   ├── DatabaseConnectionError → 503
│   └── QueryError → 500
├── NotFoundError → 404
│   ├── PatientNotFoundError
│   └── VisitNotFoundError
└── ValidationError → 422
    └── InvalidDateRangeError
```

**Justificativa:**
- Exceções de domínio desacopladas de HTTP
- Mapeamento centralizado na camada de API
- Facilita testes (pode verificar exceção específica)
- Mensagens de erro claras para debugging

---

### 7. Testes

**Decisão:** pytest com mocks para testes unitários.

**Alternativas consideradas:**
- Testcontainers (PostgreSQL real em container)
- Banco em memória (SQLite)

**Justificativa:**

Para TCC com prazo limitado:
- Mocks são mais simples de configurar
- Testes rodam mais rápido
- Não requerem Docker instalado
- Focam na lógica de negócio, não na integração

**Estrutura:**
```
tests/
├── conftest.py          # Fixtures compartilhadas
├── unit/
│   ├── repositories/    # Testa queries com mocks
│   └── services/        # Testa lógica de negócio
└── integration/         # (futuro) Testes end-to-end
```

---

### 8. Ferramentas de Qualidade

| Ferramenta | Propósito |
|------------|-----------|
| Ruff | Linter + formatter (substitui flake8/isort/black) |
| pytest | Framework de testes |
| pytest-cov | Cobertura de código |

**Por que Ruff:**
- Uma ferramenta só em vez de três
- 10-100x mais rápido que alternativas
- Desenvolvido pela mesma equipe do uv (Astral)

---

## Fluxo de uma Requisição

```
GET /patients/abc123/visits?start_date=2025-01-01&end_date=2025-12-31

1. FastAPI recebe requisição
2. Pydantic valida parâmetros (path + query)
3. Dependency injection fornece VisitService
4. VisitService.get_patient_visits():
   a. Valida regra de negócio (start <= end)
   b. Verifica se paciente existe via PatientRepository
   c. Busca visitas via VisitRepository
5. Repositório executa query com parâmetros preparados
6. Service retorna lista de Visit (modelos de domínio)
7. API converte para VisitResponse (schema Pydantic)
8. FastAPI serializa JSON e retorna
```

---

## Preparação para Kafka (Futuro)

A arquitetura atual já prepara integração com Kafka:

```python
# Futuro: consumer Kafka chama o mesmo service
@kafka_consumer("clinical-events")
def handle_event(event):
    service = get_visit_service()
    visits = service.get_patient_visits(
        patient_id=event["patient_id"],
        start_date=event["start_date"],
        end_date=event["end_date"],
    )
    # ... processar com LLM
```

A camada de serviço é agnóstica à origem da requisição (HTTP ou Kafka).

---

## Configuração de Ambiente

Variáveis obrigatórias (`.env`):

| Variável | Descrição |
|----------|-----------|
| `POSTGRES_USER` | Usuário do banco |
| `POSTGRES_PASSWORD` | Senha do banco |
| `POSTGRES_HOST` | Host (default: localhost) |
| `POSTGRES_PORT` | Porta (default: 5432) |
| `POSTGRES_DB` | Nome do banco (default: clinical_data) |

---

## Comandos Úteis

```bash
# Instalar dependências
uv sync

# Rodar aplicação
uv run uvicorn clinical_summarizer.main:app --reload

# Rodar testes
uv run pytest

# Rodar testes com cobertura
uv run pytest --cov=clinical_summarizer --cov-report=html

# Verificar código (linter)
uv run ruff check src tests

# Formatar código
uv run ruff format src tests
```

---

## Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Layered Architecture Pattern](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)
