# Projeto VDDS - Motor de Análise de Crédito

Projeto desenvolvido para a disciplina de **Validação e Verificação de Software**. O sistema implementa um motor de análise de crédito com backend em **FastAPI** e frontend em **Streamlit**, com foco em regras de negócio determinísticas, persistência de simulações e apoio a testes de software.

## Objetivo

O projeto simula a avaliação de propostas de crédito a partir de dados do proponente. A API processa a solicitação, aplica regras de aprovação, calcula taxa de juros quando aplicável e registra o histórico da análise para auditoria.

O repositório também foi estruturado para apoiar técnicas de teste vistas na disciplina, como:

- Particionamento de Equivalência.
- Análise de Valor Limite (BVA).
- MC/DC.
- Fluxo de Dados (Def-Use).

## Estrutura do Projeto

```text
projeto_VDDS/
├── package.json
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── setup.cfg
│   ├── src/
│   │   └── credit_engine/
│   │       ├── constants.py
│   │       ├── database.py
│   │       ├── main.py
│   │       ├── repository.py
│   │       ├── rules.py
│   │       ├── schemas.py
│   │       └── service.py
│   └── tests/
│       ├── conftest.py
│       ├── test_01_equivalence.py
│       ├── test_02_bva.py
│       ├── test_03_mcdc.py
│       ├── test_04_data_flow.py
│       ├── test_05_state.py
│       └── test_06_integration.py
└── frontend/
    ├── README.md
    ├── Procfile
    ├── venv/ (ambiente virtual)
    └── src/
        ├── app.py (Streamlit app)
        ├── requirements.txt
```
```

## Tecnologias Utilizadas

### Backend

- Python 3.
- FastAPI.
- Uvicorn.
- SQLAlchemy.
- SQLite por padrão em ambiente local.

### Frontend

- Python 3.11
- Streamlit.
- Requests.
- Pandas.

### Testes e Qualidade

- Pytest (Backend).
- Pytest-cov.
- Radon.
- Mutmut.
- Pylint (Frontend).
- Flake8 (Frontend).

## Regras de Negócio

O motor de crédito trabalha com as seguintes decisões principais:

- Validação de idade entre 18 e 75 anos.
- Validação de tipo de financiamento: `IMOBILIARIO` ou `ESTUDANTIL`.
- Recusa automática para clientes com restrição cadastral.
- Aprovação automática quando há renda e score suficientes.
- Aprovação alternativa com co-garantidor.
- Encaminhamento para análise humana quando o score está em uma faixa intermediária.
- Cálculo de taxa de juros com base no tipo de financiamento e na faixa de score.
- Registro de histórico com suporte a idempotência por janela de 60 segundos.

## Backend

### Endpoints

#### `GET /`

Retorna uma mensagem simples indicando que a API está ativa.

#### `GET /health`

Endpoint de saúde da aplicação.

#### `POST /api/v1/credit/evaluate`

Avalia uma proposta de crédito.

Exemplo de payload:

```json
{
  "nome": "João da Silva",
  "idade": 30,
  "rendaMensal": 6000,
  "scoreCredito": 850,
  "possuiNomeSujo": false,
  "possuiCoGarantidor": false,
  "tipoFinanciamento": "IMOBILIARIO"
}
```

Resposta esperada:

```json
{
  "status_proposta": "APROVADO",
  "taxa_juros_aplicada": 0.085,
  "motivo_decisao": "...",
  "data_processamento": "2026-07-03T12:00:00Z"
}
```

#### `GET /api/v1/history`

Retorna o histórico das últimas simulações salvas no banco.

### Modelagem dos Dados

O backend usa Pydantic para validação e serialização dos dados de entrada e saída:

- `ClienteSchema`: dados enviados para análise.
- `RespostaSchema`: retorno da avaliação.
- `SimulacaoRegistradaSchema`: representação de registros salvos no histórico.

### Persistência

Em ambiente local, o projeto usa SQLite com o arquivo `creditcalc.db`. Em produção, a URL do banco é lida da variável de ambiente `DATABASE_URL`.

O repositório SQLAlchemy cria a tabela `simulacoes` com:

- identificador incremental;
- nome do proponente;
- status da proposta;
- taxa aplicada;
- motivo da decisão;
- data de processamento;
- hash da requisição.

## Frontend

O frontend está preparado com Vite e React e serve como base para a interface da aplicação. No estado atual do projeto, a tela principal é um placeholder de configuração, então a parte visual ainda está em evolução.

## Instalação

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r src/requirements.txt
```

## Execução Local

### Backend

```bash
cd backend
uvicorn credit_engine.main:app --app-dir src --reload
```

Por padrão, a API sobe em `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend/src
streamlit run app.py
```

A aplicação abre em `http://localhost:8501`.

### Testes do Backend

```bash
cd backend
pytest                          # Executar todos os testes
pytest --cov=credit_engine      # Com cobertura
pytest -v                       # Modo verbose
```

## Testes

Os testes automatizados estão organizados por técnica de validação:

**Backend:**
- `test_01_equivalence.py`: classes de equivalência.
- `test_02_bva.py`: análise de valor limite.
- `test_03_mcdc.py`: MC/DC.
- `test_04_data_flow.py`: fluxo de dados.
- `test_05_state.py`: máquina de estados.
- `test_06_integration.py`: testes de integração.

**CI/CD:**

O projeto usa GitHub Actions para validação automática:

- `.github/workflows/backend-ci.yml`: testes do backend (Pytest, Radon, Mutmut).
- `.github/workflows/frontend-ci.yml`: validação do frontend (Pylint, Flake8, startup test).

## Qualidade e Análise

**Backend:**

```bash
cd backend
radon cc src/credit_engine              # Complexidade ciclomática
mutmut run                              # Testes de mutação
flake8 src/credit_engine                # Estilo de código
```

**Frontend:**

```bash
cd frontend/src
pylint app.py                           # Análise estática
flake8 app.py                           # Estilo PEP 8
```

## Deployment no Render

O projeto está configurado para deploy automático no Render:

### Backend

1. Conectar repositório no Render
2. Criar serviço Web com:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn credit_engine.main:app --app-dir src --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11

### Frontend

1. Criar serviço Web com:
   - **Build Command**: `pip install -r src/requirements.txt`
   - **Start Command**: `cd frontend/src && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
   - **Environment**: Python 3.11

### Variáveis de Ambiente

- `DATABASE_URL`: string de conexão do banco (opcional, usa SQLite local por padrão)
- Backend e Frontend devem ter configuração CORS apropriada para produção

### Observações

- O backend já está configurado para CORS aberto em desenvolvimento.
- Cada serviço tem seu próprio `Procfile` para facilitar o deployment.
- Em produção no Render, a variável `$PORT` é automaticamente injetada.

## Próximos Passos Possíveis

- Adicionar mais testes de integração entre frontend e backend no Streamlit.
- Implementar persistência em banco de dados relacional (PostgreSQL) em produção.
- Adicionar autenticação e autorização.
- Expandir a suite de testes com Selenium para testes end-to-end.
- Criar dashboard de análise de dados com pandas/plotly no frontend.
