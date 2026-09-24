# Arquitetura do Clinical Summarizer

Este documento descreve as decisões arquiteturais do projeto, servindo como
referência técnica para a banca e futuros desenvolvedores.

## Visão Geral

O **Clinical Summarizer** é um serviço Python que:

1. Opcionalmente aciona o pipeline ETL (Pentaho Kitchen) para atualizar a
   camada Gold com dados clínicos anonimizados
2. Lê esses dados de um PostgreSQL
3. Aplica transformações (correção de encoding, parsing de JSON/avaliações)
4. Gera resumos clínicos estruturados via LLM (Anthropic Claude)
5. Persiste os resumos e logs de execução do ETL

```
┌───────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                     │
│              Endpoints, validação de entrada               │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       Service Layer                          │
│      Orquestração, regras de negócio, ETL (Pentaho), LLM     │
└──────────┬─────────────────────────────────────┬─────────────┘
           │                                     │
┌──────────▼──────────────┐          ┌───────────▼───────────────┐
│    Repository Layer      │          │   Anthropic Claude API    │
│  Acesso a dados,          │          │   (geração de resumos)    │
│  connection pool          │          └────────────────────────────┘
└──────────┬────────────────┘
           │
┌──────────▼─────────────────────┐     ┌──────────────────────────────┐
│           PostgreSQL            │◄────│  Pentaho Kitchen (kitchen.sh)│
│  patients, visits, summaries,   │     │  subprocess + polling na      │
│  etl_logs                       │     │  tabela etl_logs              │
└──────────────────────────────────┘     └──────────────────────────────┘
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

### 5. Geração de Resumos: Anthropic Claude com saída estruturada em JSON

**Decisão:** `SummaryService` chama a API do Anthropic Claude
(`anthropic_model`, configurável via `.env`) com um `SYSTEM_PROMPT` que
força o modelo a responder **apenas** com um objeto JSON (sem markdown,
sem texto livre), contendo uma chave por seção do resumo
(`services/summary_sections.py::SummarySection`) mais uma chave estruturada
`periodos_visitas` com a distribuição de visitas por período/dia.

**Justificativa:**

- Texto livre exigiria parsing por regex no backend (frágil) ou no frontend
  (acopla o frontend ao fraseado do modelo). JSON estruturado remove essa
  fragilidade e dá ao frontend um contrato estável (`sections`,
  `section_labels`, `section_order`, `visit_periods`).
- **Datas/contagens não são confiadas ao LLM para aritmética:** o prompt
  já informa a distribuição de visitas por dia calculada em Python
  (`_format_visits_by_day`); o modelo só precisa *agrupar* esses dias em
  períodos com sentido clínico (`VisitPeriod.days`). `start_date`,
  `end_date` e `visit_count` de cada período são **derivados** de `days`
  (propriedades calculadas, não campos que o LLM preenche diretamente) —
  evita o caso observado de um período `visit_count=6` cujo texto livre só
  citava 4 visitas de um único dia, sem contabilizar o resto.
- Entradas malformadas em `periodos_visitas` são descartadas
  individualmente (`parse_visit_periods_safe`) sem invalidar o resumo
  inteiro — o LLM é uma fonte não confiável por natureza.
- O resultado (seções + períodos) é persistido como JSON em
  `summaries.summary_text`, então a resposta da API é reconstruída a
  partir do banco sem precisar rechamar o LLM.

**Tratamento de erros:** falhas de conexão ou geração viram
`LLMConnectionError`/`LLMGenerationError` (ver seção de exceções), e a
ausência de visitas no período vira `NoVisitsFoundError` antes mesmo de
chamar o LLM.

---

### 6. Atualização de Dados: Pipeline ETL Pentaho acionado via subprocess

**Decisão:** Quando `run_etl=true` (padrão em `POST /summaries`, ou via
`POST /etl/run`), `ETLService.run_pipeline()` invoca o `kitchen.sh`
(Pentaho Data Integration) como subprocesso (`subprocess.Popen`) passando
`START_DATE`/`END_DATE`/`PATIENT_ID` como parâmetros do job, e faz
*polling* na tabela `etl_logs` (a cada `POLL_INTERVAL_SECONDS`, até
`POLL_TIMEOUT_SECONDS` = 5 min) até encontrar o registro de conclusão.

**Justificativa:**

- O pipeline Gold já existe em Pentaho (fora do escopo deste serviço);
  reescrevê-lo em Python não se justificava para o TCC.
- Rodar de forma síncrona (a requisição aguarda o `communicate()` do
  processo) simplifica o fluxo: o cliente sabe que os dados estão
  atualizados antes do resumo ser gerado, sem precisar de webhook/callback.
- O polling na tabela `etl_logs` (em vez de só checar o exit code do
  processo) permite capturar métricas de negócio (registros extraídos/
  carregados) que o Pentaho grava no banco, não no stdout.
- **Trade-off aceito:** os caminhos do Pentaho (`KITCHEN_PATH`, `JOB_PATH`
  em `services/etl_service.py`) são absolutos e fixos no código-fonte,
  amarrados à máquina onde o Pentaho está instalado — aceitável para o
  escopo do TCC (ambiente único de demonstração), mas seria o primeiro
  ponto a mover para variável de ambiente numa evolução do projeto.
- Se o ETL falhar, o resumo ainda é gerado com os dados já existentes no
  banco (falha do ETL é logada como warning, não interrompe o fluxo) —
  prioriza disponibilidade sobre garantir dado sempre fresco.

---

### 7. Estrutura de Pastas

```
clinical-summarizer/
├── src/
│   └── clinical_summarizer/
│       ├── api/                  # Camada de apresentação
│       │   ├── routes/           # Endpoints por recurso (health, visits, summaries, etl)
│       │   ├── schemas.py        # Modelos Pydantic (request/response)
│       │   └── dependencies.py
│       ├── services/             # Lógica de negócio
│       │   ├── visit_service.py
│       │   ├── etl_service.py        # Orquestração do pipeline Pentaho
│       │   ├── summary_service.py    # RAG com Anthropic Claude
│       │   └── summary_sections.py   # Contrato/parsing das seções do resumo
│       ├── repositories/         # Acesso a dados (patients, visits, summaries, etl_log)
│       ├── models/               # Modelos de domínio (dataclasses)
│       ├── utils/                # Utilitários (hashing, parsing de avaliações)
│       ├── config.py             # Configurações
│       ├── exceptions.py         # Exceções customizadas
│       └── main.py               # Entrypoint FastAPI
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

### 8. Tratamento de Erros

**Decisão:** Hierarquia de exceções customizadas mapeadas para HTTP.

```
ClinicalSummarizerError (base)
├── DatabaseError → 500
│   ├── DatabaseConnectionError → 503
│   └── QueryError → 500
├── NotFoundError → 404
│   ├── PatientNotFoundError
│   └── VisitNotFoundError
├── ValidationError → 422
│   ├── InvalidDateRangeError
│   └── NoVisitsFoundError    # nenhuma visita no período pedido
└── LLMError → 503
    ├── LLMConnectionError    # falha ao conectar/autenticar na Anthropic
    └── LLMGenerationError    # resposta do LLM não é um JSON válido, etc.
```

**Justificativa:**
- Exceções de domínio desacopladas de HTTP
- Mapeamento centralizado na camada de API (`routes/summaries.py`, por
  exemplo, converte `NoVisitsFoundError`/`InvalidDateRangeError` em 404/422
  e `LLMError` em 503 — ver tabela de status HTTP nos exemplos do README)
- Facilita testes (pode verificar exceção específica)
- Mensagens de erro claras para debugging

---

### 9. Testes

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

### 10. Ferramentas de Qualidade

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

### Fluxo de consulta de visitas

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

### Fluxo de geração de resumo clínico (fluxo principal)

```
POST /summaries  {"patient_id": "899", "start_date": "...", "end_date": "...", "run_etl": true}

1. FastAPI recebe requisição, Pydantic valida o body (SummaryRequest)
2. SummaryService.generate_summary():
   a. (se run_etl=true) ETLService.run_pipeline() aciona o kitchen.sh (Pentaho)
      e faz polling em etl_logs até concluir ou estourar o timeout de 5 min;
      falha aqui só gera warning no log, não interrompe o fluxo
   b. VisitService busca as visitas do paciente no período (Postgres)
      → sem visitas, levanta NoVisitsFoundError (422)
   c. Monta o prompt: distribuição de visitas por dia (calculada em Python)
      + dados de cada visita (CIDs, sintomas, evolução clínica)
   d. Chama a API da Anthropic (client.messages.create) com o SYSTEM_PROMPT
      que exige resposta em JSON estruturado
      → erro de conexão/geração vira LLMConnectionError/LLMGenerationError (503)
   e. Faz o parse do JSON: seções de texto (parse_summary_sections) e
      distribuição de visitas por período (parse_visit_periods, que
      descarta entradas malformadas sem falhar o resumo inteiro)
   f. Persiste o resumo (seções + períodos serializados em JSON) na tabela
      summaries via SummaryRepository
3. API monta SummaryResponse (sections, section_labels, section_order,
   visit_periods, metadados de tokens/tempo) e retorna 201
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

Variáveis opcionais, com default (`config.py`):

| Variável | Default | Descrição |
|----------|---------|-----------|
| `POSTGRES_HOST` | `localhost` | Host do Postgres |
| `POSTGRES_PORT` | `5432` | Porta do Postgres |
| `POSTGRES_DB` | `clinical_data` | Nome do banco |
| `POSTGRES_POOL_MIN_SIZE` / `POSTGRES_POOL_MAX_SIZE` | `2` / `10` | Tamanho do connection pool |
| `APP_ENV` | `development` | `development` \| `staging` \| `production` |
| `APP_PORT` | `8734` | Porta da API (uvicorn via CLI não lê essa var — ver README) |
| `APP_LOG_LEVEL` | `INFO` | Nível de log |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Origens do frontend liberadas no CORS (separadas por vírgula) |
| `ANTHROPIC_API_KEY` | — | **Obrigatória para `POST /summaries`** — sem ela, `SummaryService` levanta `LLMConnectionError` |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-20241022` | Modelo usado na geração de resumos |
| `ANTHROPIC_TEMPERATURE` | `0.3` | Temperatura da geração |
| `ANTHROPIC_MAX_TOKENS` | `4096` | Limite de tokens de saída |

O ETL (Pentaho) não é configurado via `.env` — os caminhos do `kitchen.sh` e
do job estão fixos em `services/etl_service.py` (ver decisão 6, acima).

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
- [Anthropic Claude API (Messages)](https://docs.anthropic.com/)
- [Layered Architecture Pattern](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)
