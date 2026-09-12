# Clinical Summarizer

Serviço Python para geração de resumos clínicos automatizados via LLM (Anthropic Claude).

## Requisitos

- Python 3.12+
- PostgreSQL (com tabelas `patients`, `visits` e `summaries`)
- [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Chave de API da Anthropic
- Pentaho Data Integration (Kitchen) instalado localmente — apenas se for usar o ETL (`run_etl=true` ou `POST /etl/run`)

## Instalação

### Com uv (recomendado)

```bash
# Instalar uv (se ainda não tiver)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clonar e entrar no diretório
cd clinical-summarizer

# Instalar dependências (cria venv automaticamente)
uv sync

# Instalar dependências de desenvolvimento
uv sync --extra dev
```

### Com pip (alternativa)

```bash
# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou: .venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt  # para desenvolvimento

# Instalar o pacote em modo editável
pip install -e .
```

## Configuração

1. Copie o arquivo de exemplo:
   ```bash
   cp .env.example .env
   ```

2. Edite `.env` com suas credenciais:
   ```env
   # PostgreSQL
   POSTGRES_USER=seu_usuario
   POSTGRES_PASSWORD=sua_senha
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=clinical_data

   # Aplicação
   APP_PORT=8734

   # Origens do frontend autorizadas a consumir a API (CORS, separadas por vírgula)
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173

   # Anthropic Claude (obrigatório para geração de resumos)
   ANTHROPIC_API_KEY=sua_api_key_aqui
   ANTHROPIC_MODEL=claude-sonnet-4-20250514
   ANTHROPIC_TEMPERATURE=0.3
   ANTHROPIC_MAX_TOKENS=4096
   ```

## Uso

### Rodar a aplicação

```bash
# Com uv
uv run uvicorn clinical_summarizer.main:app --reload --port 8734

# Com pip (ambiente virtual ativado)
source .venv/bin/activate && uvicorn clinical_summarizer.main:app --reload --port 8734
```

> **Nota:** Se estiver usando VSCode instalado via Snap, rode os comandos em um terminal externo.

> A porta é configurável via `APP_PORT` no `.env` (default `8734`). Como o `uvicorn` via CLI não lê `APP_PORT` automaticamente, passe `--port` explicitamente ou rode com `python -m clinical_summarizer.main`, que usa a config.

A API estará disponível em:
- **Swagger UI:** http://localhost:8734/docs
- **ReDoc:** http://localhost:8734/redoc

### Endpoints disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações da API |
| GET | `/health` | Health check |
| GET | `/patients/{patient_id}/visits` | Lista visitas de um paciente |
| GET | `/patients/{patient_id}/evaluations` | Avaliações de todas as visitas de um paciente |
| GET | `/patients/visits/{visit_id}` | Detalhes de uma visita |
| POST | `/summaries` | Gera resumo clínico via LLM |
| POST | `/etl/run` | Executa o pipeline ETL (Pentaho) manualmente |

### Exemplos de requisições

#### Listar visitas de um paciente
```bash
curl "http://localhost:8734/patients/899/visits?start_date=2022-10-01&end_date=2022-10-31"
```

#### Obter avaliações de todas as visitas de um paciente
```bash
curl "http://localhost:8734/patients/899/evaluations?start_date=2022-10-01&end_date=2022-10-31"
```

Resposta:
```json
{
  "patient_id": "91d95f436356bc3df44d44406a139351debd...",
  "start_date": "2022-10-01",
  "end_date": "2022-10-31",
  "total_visits": 4,
  "total_visits_with_evaluations": 1,
  "visits": [
    {
      "visit_id": "bdc5d8a48c23897906b09a9a3680bd2e9c8b...",
      "visit_date": "2022-10-26",
      "total_sections": 140,
      "total_filled_fields": 777,
      "sections": [...],
      "raw_text": "=== Seção 1 ===\n- Campo: Valor\n..."
    }
  ]
}
```

#### Gerar resumo clínico
```bash
curl -X POST "http://localhost:8734/summaries" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "899",
    "start_date": "2022-10-01",
    "end_date": "2022-10-31"
  }'
```

Resposta: o resumo é retornado tanto em markdown (`summary_text`, para exibição simples)
quanto estruturado por etapa em `sections`, para o frontend renderizar cada bloco
separadamente. `section_labels` e `section_order` trazem os rótulos em português e a
ordem de exibição recomendada, para não precisar hardcodar isso no cliente. `visit_periods`
traz a distribuição de visitas por período (e, dentro de cada período, por dia em `days`)
como dado estruturado, para o frontend montar o gráfico de histórico sem depender de
parsing de texto — `start_date`, `end_date` e `visit_count` de cada período são somas/
limites derivados de `days`, não gerados diretamente pelo LLM.

```json
{
  "summary_id": "550e8400-e29b-41d4-a716-446655440000",
  "patient_id": "f6e5d4c3b2a1...",
  "summary_text": "## Resumo Clínico\n\n### Período Analisado\n...",
  "sections": {
    "periodo_analisado": "01/10/2022 a 31/10/2022",
    "diagnosticos_cid": "J06.9 - Infecção respiratória aguda",
    "historico_atendimentos": "Paciente atendido em 15/10 e 26/10...",
    "sintomas_queixas_principais": "Febre, tosse...",
    "observacoes_relevantes": "Recomenda-se acompanhamento..."
  },
  "section_labels": {
    "periodo_analisado": "Período Analisado",
    "diagnosticos_cid": "Diagnósticos (CID)",
    "historico_atendimentos": "Histórico de Atendimentos",
    "sintomas_queixas_principais": "Sintomas e Queixas Principais",
    "observacoes_relevantes": "Observações Relevantes"
  },
  "section_order": [
    "periodo_analisado",
    "diagnosticos_cid",
    "historico_atendimentos",
    "sintomas_queixas_principais",
    "observacoes_relevantes"
  ],
  "visit_periods": [
    {
      "label": "Primeira semana",
      "start_date": "2022-10-15",
      "end_date": "2022-10-15",
      "visit_count": 1,
      "days": [
        {"visit_date": "2022-10-15", "visit_count": 1}
      ]
    },
    {
      "label": "Última semana",
      "start_date": "2022-10-26",
      "end_date": "2022-10-26",
      "visit_count": 3,
      "days": [
        {"visit_date": "2022-10-26", "visit_count": 3}
      ]
    }
  ],
  "visit_count": 4,
  "filter_start_date": "2022-10-01",
  "filter_end_date": "2022-10-31",
  "llm_model": "claude-sonnet-4-20250514",
  "llm_total_tokens": 1500,
  "generation_duration_ms": 2500,
  "created_at": "2025-06-15T10:30:00"
}
```

#### Executar o pipeline ETL manualmente
```bash
curl -X POST "http://localhost:8734/etl/run" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "patient_id": 899
  }'
```

## Banco de Dados

### Tabela summaries

Os resumos gerados são salvos na tabela `summaries`:

```sql
CREATE TABLE summaries (
    id SERIAL PRIMARY KEY,
    summary_id UUID DEFAULT gen_random_uuid() UNIQUE,
    patient_id VARCHAR(64) NOT NULL REFERENCES patients(patient_id),
    visit_ids TEXT NOT NULL,
    filter_start_date DATE,
    filter_end_date DATE,
    summary_text TEXT NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    llm_prompt_tokens INTEGER,
    llm_completion_tokens INTEGER,
    llm_total_tokens INTEGER,
    llm_temperature NUMERIC(3,2),
    generation_duration_ms INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Testes

```bash
# Rodar todos os testes
uv run pytest

# Com cobertura
uv run pytest --cov=clinical_summarizer --cov-report=html

# Testes específicos
uv run pytest tests/unit/services/
```

## Qualidade de Código

```bash
# Verificar problemas
uv run ruff check src tests

# Corrigir automaticamente
uv run ruff check --fix src tests

# Formatar código
uv run ruff format src tests
```

## Estrutura do Projeto

```
clinical-summarizer/
├── src/clinical_summarizer/
│   ├── api/              # Endpoints FastAPI
│   │   ├── routes/       # Routers (health, visits, summaries, etl)
│   │   └── schemas.py    # Schemas Pydantic
│   ├── services/         # Lógica de negócio
│   │   ├── visit_service.py
│   │   ├── etl_service.py          # Execução do pipeline Pentaho
│   │   ├── summary_service.py      # RAG com Anthropic
│   │   └── summary_sections.py     # Constantes e parsing das seções do resumo
│   ├── repositories/     # Acesso a dados (patients, visits, summaries, etl_log)
│   ├── models/           # Modelos de domínio
│   ├── utils/            # Utilitários
│   │   ├── hashing.py
│   │   └── evaluation_parser.py  # Parser de evaluations_raw
│   └── main.py           # Entrypoint
├── tests/                # Testes
├── docs/                 # Documentação
└── pyproject.toml        # Configuração do projeto
```

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md) - Decisões arquiteturais e justificativas

## Licença

MIT
