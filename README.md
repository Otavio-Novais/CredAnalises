# CERASA — Motor de Análise de Crédito

[![Backend CI](https://github.com/Otavio-Novais/CredAnalises/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/Otavio-Novais/CredAnalises/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/Otavio-Novais/CredAnalises/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/Otavio-Novais/CredAnalises/actions/workflows/frontend-ci.yml)
![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688)
![Streamlit](https://img.shields.io/badge/Streamlit-frontend-FF4B4B)

Motor de análise de crédito com **API em FastAPI** e **interface em Streamlit**. Ele avalia propostas de financiamento (imobiliário ou estudantil) com regras de negócio determinísticas, calcula a taxa de juros pela faixa de score e guarda cada decisão com a justificativa, para auditoria.

O projeto foi feito para a disciplina de **Validação e Verificação de Software** (Ciência da Computação, UNIFESP). As regras de negócio foram escritas para servir de alvo das principais técnicas de teste: particionamento de equivalência, análise de valor limite, MC/DC, fluxo de dados, máquina de estados e teste de mutação.

## Destaques

| | |
|---|---|
| **136 testes automatizados** (+3 E2E com Selenium) | organizados por técnica de teste, de `test_01` a `test_13` |
| **98% de cobertura** de linhas no backend | `pytest --cov=credit_engine` |
| **Teste de mutação** com Mutmut | relatório em [`backend/MUTATION_REPORT.pdf`](backend/MUTATION_REPORT.pdf) |
| **Complexidade ciclomática** controlada | o CI falha se o Radon encontrar uma função acima da classe B |
| **Idempotência** | requisições idênticas em até 60 s retornam o resultado em cache |
| **Autenticação** | senha com PBKDF2-SHA256 + salt e token Bearer aleatório |

## Arquitetura

```text
┌──────────────────────┐   HTTP/JSON   ┌───────────────────────────────────────┐
│  Streamlit (frontend)│ ────────────► │  FastAPI (backend)                     │
│  simulação, histórico│               │  main.py      → rotas e dependências   │
│  login e cadastro    │ ◄──────────── │  service.py   → orquestração e cache   │
└──────────────────────┘               │  rules.py     → regras de crédito      │
                                       │  repository.py / database.py           │
                                       │               → SQLAlchemy (SQLite/PG) │
                                       └───────────────────────────────────────┘
```

O serviço de crédito recebe o repositório por injeção de dependência. Nos testes ele usa um repositório em memória; em execução, o repositório SQL.

## Regras de negócio

As regras ficam em [`rules.py`](backend/src/credit_engine/rules.py) e os parâmetros em [`constants.py`](backend/src/credit_engine/constants.py). A avaliação segue esta ordem:

1. **Tipo de financiamento** diferente de `IMOBILIARIO` ou `ESTUDANTIL` → `RECUSADO`
2. **Idade** fora de 18 a 75 anos → `RECUSADO`
3. **Restrição cadastral** (nome sujo) → `RECUSADO`
4. **Aprovação automática** quando `(renda > R$ 5.000 E score > 600) OU (co-garantidor E renda > R$ 3.000)` → `APROVADO`
5. **Score acima de 400** sem atingir a aprovação → `ANALISE_HUMANA`
6. Caso contrário → `RECUSADO`

**Taxa de juros** (aplicada quando a proposta não é recusada):

| Faixa de score | Ajuste | Imobiliário (base 10%) | Estudantil (base 6%) |
|---|---|---|---|
| 801 a 1000 | −1,5 p.p. | 8,5% | 4,5% |
| 601 a 800 | −0,5 p.p. | 9,5% | 5,5% |
| 401 a 600 | +1,0 p.p. | 11,0% | 7,0% |
| 0 a 400 | +3,0 p.p. | 13,0% | 9,0% |

## Estratégia de testes

| Arquivo | Técnica / escopo |
|---|---|
| `test_01_equivalence.py` | Particionamento de equivalência (classes válidas e inválidas) |
| `test_02_bva.py` | Análise de valor limite (idade 18/75, renda, faixas de score) |
| `test_03_mcdc.py` | MC/DC sobre a expressão `(A ∧ B) ∨ (C ∧ D)` da aprovação |
| `test_04_data_flow.py` | Fluxo de dados (pares def-use) em `calcular_taxa_juros()` |
| `test_05_state.py` | Transições de status da proposta |
| `test_06_integration.py` | Integração avaliar → salvar → consultar |
| `test_07_main.py` | Endpoints da API (FastAPI `TestClient`) |
| `test_08_database.py` | Camada ORM e repositório SQL |
| `test_09_users_service.py` | Serviço de usuários (hash de senha, tokens) |
| `test_10_users_api.py` | Endpoints `/api/v1/users/*` |
| `test_11_user_linked_simulations_service.py` | Histórico por usuário e isolamento do cache |
| `test_12_user_linked_simulations_api.py` | Endpoint `GET /api/v1/users/me/history` |
| `test_13_e2e.py` | E2E com Selenium: cadastro → login → simulação → histórico |

As fixtures comuns ficam em [`conftest.py`](backend/tests/conftest.py): `cliente_factory(**overrides)`, `cliente_perfeito` e `in_memory_service`.

## Como rodar

**Requisitos:** Python 3.11+.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn credit_engine.main:app --app-dir src --reload
```

A API sobe em `http://127.0.0.1:8000`, com documentação interativa em `/docs`.

### Frontend

```bash
cd frontend
python -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt
cd src
streamlit run app.py
```

A interface abre em `http://localhost:8501`.

### Testes e métricas

```bash
cd backend
pytest --ignore=tests/test_13_e2e.py               # testes unitários e de integração
pytest --cov=credit_engine --cov-report=html       # cobertura
radon cc src/credit_engine -s -a                   # complexidade ciclomática
radon mi src/credit_engine                         # índice de manutenibilidade
mutmut run && mutmut results                       # teste de mutação
```

O `test_13_e2e.py` precisa do backend e do frontend rodando e do Google Chrome instalado.

### Variáveis de ambiente

| Variável | Onde | Padrão |
|---|---|---|
| `DATABASE_URL` | backend | `sqlite:///./newcreditcalc.db` (aceita PostgreSQL) |
| `API_URL` | frontend | `http://localhost:8000` |

## API

| Método | Endpoint | Descrição | Auth |
|---|---|---|---|
| GET | `/` | Mensagem de status | — |
| GET | `/health` | Health check | — |
| POST | `/api/v1/users/register` | Cadastra usuário (201) | — |
| POST | `/api/v1/users/login` | Retorna token de acesso | — |
| GET | `/api/v1/users/me` | Dados do usuário autenticado | obrigatória |
| POST | `/api/v1/credit/evaluate` | Avalia uma proposta | opcional |
| GET | `/api/v1/history?limite=50` | Últimas simulações (todas) | — |
| GET | `/api/v1/users/me/history?limite=50` | Simulações do usuário autenticado | obrigatória |

Rotas autenticadas usam o header `Authorization: Bearer <token>`.

<details>
<summary><b>Exemplos de requisição e resposta</b></summary>

**Cadastro** — `POST /api/v1/users/register`

```json
{ "nome": "João da Silva", "email": "joao@example.com", "senha": "senha123" }
```

**Login** — `POST /api/v1/users/login`

```json
{ "email": "joao@example.com", "senha": "senha123" }
```

```json
{
  "token": "5a8b32fb0426e402548b2c0c...",
  "usuario": { "id": 1, "nome": "João da Silva", "email": "joao@example.com" }
}
```

**Avaliação** — `POST /api/v1/credit/evaluate`

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

```json
{
  "status_proposta": "APROVADO",
  "taxa_juros_aplicada": 0.085,
  "motivo_decisao": "Aprovado por critério padrão: renda R$ 6,000.00 (mínimo R$ 5,000.00) e score 850 (mínimo 600). Modalidade: Imobiliário.",
  "data_processamento": "2026-11-06T00:22:27.226865"
}
```

Os endpoints de histórico retornam uma lista com `id`, `nome_proponente`, `status_proposta`, `taxa_juros_aplicada`, `motivo_decisao` e `data_processamento`.

</details>

## Persistência e idempotência

As simulações ficam na tabela `simulacoes` (SQLAlchemy). Cada requisição gera um hash MD5 dos dados do proponente, que inclui o `usuario_id` quando há login. Se o mesmo hash aparecer em até 60 segundos, a API devolve a decisão salva com o prefixo `[CACHE]`, sem reprocessar nem duplicar o registro.

## Estrutura

```text
CredAnalises/
├── .github/workflows/
│   ├── backend-ci.yml         # pytest + radon + mutmut
│   └── frontend-ci.yml        # pylint + flake8 + teste de inicialização
├── backend/
│   ├── requirements.txt
│   ├── setup.cfg              # config do pytest, radon e mutmut
│   ├── mutmut_runner.py
│   ├── MUTATION_REPORT.pdf
│   ├── src/credit_engine/
│   │   ├── main.py            # rotas FastAPI e dependências
│   │   ├── service.py         # orquestração, hash e idempotência
│   │   ├── rules.py           # regras de crédito e cálculo de juros
│   │   ├── constants.py       # limites e taxas
│   │   ├── schemas.py         # modelos Pydantic
│   │   ├── repository.py      # interfaces e repositórios em memória
│   │   ├── database.py        # ORM e repositório SQL
│   │   └── user_service.py    # cadastro, login e tokens
│   └── tests/                 # test_01 … test_13 + conftest.py
└── frontend/src/
    ├── app.py                 # app Streamlit
    ├── requirements.txt
    ├── images/
    └── auth/                  # cliente HTTP, telas de login e histórico pessoal
```

## Deploy (Render)

| Serviço | Build | Start |
|---|---|---|
| Backend | `pip install -r backend/requirements.txt` | `cd backend && uvicorn credit_engine.main:app --app-dir src --host 0.0.0.0 --port $PORT` |
| Frontend | `pip install -r frontend/src/requirements.txt` | `cd frontend/src && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0` |

No Render, defina `DATABASE_URL` no backend e `API_URL` no frontend. As origens aceitas pelo CORS ficam em `main.py`.

## Limitações conhecidas e próximos passos

- Usuários e sessões ficam **em memória** e se perdem quando a API reinicia; só as simulações vão para o banco.
- Os tokens não expiram. O próximo passo seria expiração com refresh token.
- O histórico geral (`/api/v1/history`) é público.
- Ideias: rate limiting, papéis de usuário (admin, analista, cliente) e migração do evento `startup` para `lifespan` do FastAPI.
