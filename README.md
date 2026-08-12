# Clinical Summarizer

Serviço Python para geração de resumos clínicos automatizados via LLM (Anthropic Claude).

## Requisitos

- Python 3.12+
- PostgreSQL (com tabelas `patients`, `visits` e `summaries`)
- [uv](https://docs.astral.sh/uv/) (recomendado) ou pip
- Chave de API da Anthropic

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
uv run uvicorn clinical_summarizer.main:app --reload

# Com pip (ambiente virtual ativado)
source .venv/bin/activate && uvicorn clinical_summarizer.main:app --reload
```

> **Nota:** Se estiver usando VSCode instalado via Snap, rode os comandos em um terminal externo.

A API estará disponível em:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações da API |
| GET | `/health` | Health check |
| GET | `/patients/{patient_id}/visits` | Lista visitas de um paciente |
| GET | `/patients/{patient_id}/evaluations` | Avaliações de todas as visitas de um paciente |
| GET | `/patients/visits/{visit_id}` | Detalhes de uma visita |
| POST | `/summaries` | Gera resumo clínico via LLM |

### Exemplos de requisições

#### Listar visitas de um paciente
```bash
curl "http://localhost:8000/patients/899/visits?start_date=2022-10-01&end_date=2022-10-31"
```

#### Obter avaliações de todas as visitas de um paciente
```bash
curl "http://localhost:8000/patients/899/evaluations?start_date=2022-10-01&end_date=2022-10-31"
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
curl -X POST "http://localhost:8000/summaries" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "899",
    "start_date": "2022-10-01",
    "end_date": "2022-10-31"
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
│   │   ├── routes/       # Routers (health, visits, summaries)
│   │   └── schemas.py    # Schemas Pydantic
│   ├── services/         # Lógica de negócio
│   │   ├── visit_service.py
│   │   └── summary_service.py  # RAG com Anthropic
│   ├── repositories/     # Acesso a dados
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
