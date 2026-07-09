# Clinical Summarizer

Serviço Python para geração de resumos clínicos automatizados via LLM (Google Gemini).

## Requisitos

- Python 3.12+
- PostgreSQL (com tabelas `patients` e `visits` já populadas pelo ETL)
- [uv](https://docs.astral.sh/uv/) (recomendado) ou pip

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
```

## Configuração

1. Copie o arquivo de exemplo:
   ```bash
   cp .env.example .env
   ```

2. Edite `.env` com suas credenciais do PostgreSQL:
   ```
   POSTGRES_USER=seu_usuario
   POSTGRES_PASSWORD=sua_senha
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=clinical_data
   ```

## Uso

### Rodar a aplicação

```bash
# Com uv
uv run uvicorn clinical_summarizer.main:app --reload

# Com pip (ambiente virtual ativado)
uvicorn clinical_summarizer.main:app --reload
```

A API estará disponível em:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/` | Informações da API |
| GET | `/health` | Health check |
| GET | `/patients/{patient_id}/visits` | Lista visitas de um paciente |
| GET | `/patients/visits/{visit_id}` | Detalhes de uma visita |

### Exemplo de requisição

```bash
curl "http://localhost:8000/patients/abc123/visits?start_date=2025-01-01&end_date=2025-12-31"
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
│   ├── api/           # Endpoints FastAPI
│   ├── services/      # Lógica de negócio
│   ├── repositories/  # Acesso a dados
│   ├── models/        # Modelos de domínio
│   └── main.py        # Entrypoint
├── tests/             # Testes
├── docs/              # Documentação
└── pyproject.toml     # Configuração do projeto
```

## Documentação

- [Arquitetura](docs/ARCHITECTURE.md) - Decisões arquiteturais e justificativas

## Licença

MIT
