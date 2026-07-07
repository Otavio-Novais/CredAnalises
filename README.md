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
│   │       ├── __init__.py
│   │       ├── constants.py
│   │       ├── database.py
│   │       ├── main.py
│   │       ├── repository.py
│   │       ├── rules.py
│   │       ├── schemas.py
│   │       ├── service.py
│   │       └── user_service.py
│   └── tests/
│       ├── conftest.py
│       ├── test_01_equivalence.py
│       ├── test_02_bva.py
│       ├── test_03_mcdc.py
│       ├── test_04_data_flow.py
│       ├── test_05_state.py
│       ├── test_06_integration.py
│       ├── test_07_main.py
│       ├── test_08_database.py
│       ├── test_09_users_service.py
│       ├── test_10_users_api.py
│       ├── test_11_user_linked_simulations_service.py
│       ├── test_12_user_linked_simulations_api.py
│       └── test_13_e2e.py
└── frontend/
    ├── README.md
    ├── Procfile
    ├── venv/ (ambiente virtual)
    └── src/
        ├── app.py (Streamlit app principal)
        ├── requirements.txt
        └── auth/
            ├── __init__.py
            ├── auth_api.py
            ├── auth_ui.py
            └── historico_pessoal.py
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
- Cálculo de taxa de juros com base no tipo de financiamento e na faixa de score:
  - IMOBILIÁRIO: 10% de taxa base
  - ESTUDANTIL: 6% de taxa base
  - Ajustes por score: -1.5% (801+), -0.5% (601-800), +1.0% (401-600), +3.0% (0-400)
- Registro de histórico com suporte a idempotência por janela de 60 segundos (cache por usuário).
- **Autenticação de usuários** com tokens JWT-like (Bearer tokens).
- **Histórico vinculado a usuários** com escopo privado e público.

## Backend

### Autenticação

A API implementa autenticação baseada em **Bearer tokens**. Cada usuário registrado recebe um token de autenticação que deve ser incluído no header `Authorization` nas requisições autenticadas:

```
Authorization: Bearer <token>
```

Os tokens são gerados com SHA256 e associados ao usuário autenticado. Simulações de crédito podem ser realizadas com ou sem autenticação.

### Endpoints

#### Health & Info

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|---------------|
| GET | `/` | Verifica se a API está ativa | ❌ |
| GET | `/health` | Status da aplicação | ❌ |

#### Gerenciamento de Usuários

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|---------------|
| POST | `/api/v1/users/register` | Registra novo usuário (201 Created) | ❌ |
| POST | `/api/v1/users/login` | Login e obtenção de token | ❌ |
| GET | `/api/v1/users/me` | Obtém dados do usuário autenticado | ✅ Requerida |

#### Avaliação de Crédito

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|---------------|
| POST | `/api/v1/credit/evaluate` | Avalia proposta de crédito (idempotente 60s) | 🔓 Opcional |
| GET | `/api/v1/history` | Histórico de todas as simulações (limite: 100) | ❌ |
| GET | `/api/v1/users/me/history` | Histórico de simulações do usuário autenticado | ✅ Requerida |

**Exemplos de Requisições:**

**POST `/api/v1/users/register`**

```json
{
  "username": "joao_silva",
  "email": "joao@example.com",
  "password": "senha_segura_123"
}
```

**POST `/api/v1/users/login`**

```json
{
  "username": "joao_silva",
  "password": "senha_segura_123"
}
```

Resposta:
```json
{
  "access_token": "sha256_hash_token",
  "token_type": "bearer"
}
```

**POST `/api/v1/credit/evaluate`**

Payload (sem autenticação ou com token no header):

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
  "motivo_decisao": "Renda e score suficientes para aprovação",
  "data_processamento": "2026-07-03T12:00:00Z"
}
```

**GET `/api/v1/users/me/history`**

Retorna apenas as simulações do usuário autenticado:

```json
{
  "simulacoes": [
    {
      "id": 1,
      "nome_proponente": "João da Silva",
      "status_proposta": "APROVADO",
      "taxa_juros_aplicada": 0.085,
      "motivo_decisao": "...",
      "data_processamento": "2026-07-03T12:00:00Z"
    }
  ]
}
```

### Modelagem dos Dados

O backend usa Pydantic para validação e serialização dos dados de entrada e saída:

**Schemas de Crédito:**
- `ClienteSchema`: dados enviados para análise (nome, idade, renda, score, etc.).
- `RespostaSchema`: retorno da avaliação (status, taxa, motivo, data).
- `SimulacaoRegistradaSchema`: representação de registros salvos no histórico.

**Schemas de Usuário:**
- `UsuarioRegistroSchema`: dados para registro (username, email, password).
- `UsuarioLoginSchema`: credenciais de login (username, password).
- `TokenSchema`: token de autenticação retornado após login.
- `UsuarioSchema`: dados do usuário autenticado.

### Persistência

Em ambiente local, o projeto usa SQLite com o arquivo `creditcalc.db`. Em produção, a URL do banco é lida da variável de ambiente `DATABASE_URL` (suporta PostgreSQL).

O repositório SQLAlchemy cria a tabela `simulacoes` com os seguintes campos:

- `id` (PK, auto-increment): identificador incremental
- `nome_proponente`: nome do proponente
- `status_proposta`: status (APROVADO, ANALISE_HUMANA, RECUSADO)
- `taxa_juros_aplicada`: taxa aplicada (nullable)
- `motivo_decisao`: justificativa da decisão
- `data_processamento`: timestamp com timezone (UTC)
- `hash_requisicao`: hash MD5 da requisição (para idempotência)
- `usuario_id` (nullable, indexed): ID do usuário autenticado (vincula simulação ao usuário)

**Sistema de Idempotência:**
O sistema gera um hash MD5 da requisição e mantém cache por 60 segundos. Quando autenticado, o hash inclui o `usuario_id`, garantindo isolamento de cache por usuário.

## Frontend

O frontend é uma aplicação Streamlit interativa que permite simular avaliações de crédito e consultar histórico. A aplicação inclui autenticação integrada e gestão de sessão.

### Estrutura do Frontend

**`app.py`** - Aplicação principal Streamlit com:
- Interface para entrada de dados de simulação
- Cartões de resultado coloridos (✅ APROVADO / ⏳ ANALISE_HUMANA / ❌ RECUSADO)
- Exibição de histórico com filtros
- Gestão de autenticação (estado de sessão)
- Conversão de timezone (BRT)

**Módulo `auth/`** - Componentes de autenticação e histórico:
- `auth_api.py`: Camada de comunicação HTTP com backend (registro, login, requisições autenticadas)
- `auth_ui.py`: Componentes Streamlit de UI (login/registro em abas, gestão de tokens)
- `historico_pessoal.py`: Visualização de histórico pessoal do usuário autenticado

### Fluxo de Autenticação

1. Usuário se registra ou faz login pela interface de abas no Streamlit
2. Token é armazenado em `st.session_state`
3. Nas requisições subsequentes, o token é incluído no header `Authorization: Bearer <token>`
4. Simulações vinculadas ao usuário autenticado aparecem em "Minhas Simulações"
5. Usuários não autenticados ainda podem fazer simulações anônimas

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

Os testes automatizados estão organizados por técnica de validação e funcionalidade. O projeto inclui **13 arquivos de teste** cobrindo diferentes aspectos:

### Testes de Técnicas de Validação (Motor de Crédito)

- `test_01_equivalence.py`: **Particionamento de Equivalência** - partições válidas/inválidas
- `test_02_bva.py`: **Análise de Valor Limite** - limites de idade (18, 75), score, renda
- `test_03_mcdc.py`: **MC/DC** - cobertura completa da lógica booleana complexa
- `test_04_data_flow.py`: **Fluxo de Dados (Def-Use)** - caminhos de definição e uso em `calcular_taxa_juros()`
- `test_05_state.py`: **Máquina de Estados** - transições de status (APROVADO → ANALISE_HUMANA → RECUSADO)

### Testes de Integração e API

- `test_06_integration.py`: Testes de integração completa (avaliar → salvar → recuperar)
- `test_07_main.py`: Testes dos endpoints FastAPI
- `test_08_database.py`: Unitário/componente da camada ORM e repositório SQL

### Testes de Autenticação e Usuários

- `test_09_users_service.py`: Serviço de usuários (hash de senha, geração de tokens)
- `test_10_users_api.py`: Endpoints de usuários (`/api/v1/users/*`)
- `test_11_user_linked_simulations_service.py`: Histórico vinculado a usuários e cache isolado
- `test_12_user_linked_simulations_api.py`: Endpoint `GET /api/v1/users/me/history`

### Testes End-to-End

- `test_13_e2e.py`: Fluxos completos de ponta a ponta (registro → login → simulação → histórico)

### Infraestrutura de Testes

**`conftest.py`** fornece:
- `cliente_factory(**overrides)`: Builder para criar clientes de teste com dados customizáveis
- `cliente_perfeito`: Fixture com dados de cliente ideal
- `in_memory_service`: Fixture de `CreditService` com repositório em memória para testes isolados

**CI/CD:**

O projeto usa GitHub Actions para validação automática:

- `.github/workflows/backend-ci.yml`: testes do backend (Pytest, Radon, Mutmut).
- `.github/workflows/frontend-ci.yml`: validação do frontend (Pylint, Flake8, startup test).

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

## Qualidade de Código e Análise

### Testes de Mutação

O projeto usa **Mutmut** para análise de mutação (mede a efetividade dos testes):

```bash
cd backend
mutmut run          # Executa testes de mutação
mutmut results      # Exibe relatório de mutantes
```

Configuração em `setup.cfg`:
- Muta todos os arquivos em `src/credit_engine/`
- Não limita a testes apenas de linhas cobertas (`mutate_only_covered_lines = False`)
- Runner customizado para suporte a DI e fixtures

### Relatórios e Métricas

```bash
cd backend

# Cobertura de testes
pytest --cov=credit_engine --cov-report=html

# Complexidade ciclomática
radon cc src/credit_engine

# Análise de manutenibilidade
radon mi src/credit_engine

# Estilo PEP 8
flake8 src/credit_engine
```

## Variáveis de Ambiente

Configure as seguintes variáveis de ambiente conforme necessário:

```bash
# Backend (opcional)
DATABASE_URL=postgresql://user:password@localhost/creditdb  # Padrão: SQLite local

# Frontend (opcional)
API_URL=http://localhost:8000  # URL da API backend
```

## Próximos Passos Possíveis

- Implementar refresh tokens e expiração de sessão
- Adicionar rate limiting para endpoints críticos
- Implementar permissões e papéis de usuário (admin, analista, cliente)
- Expandir testes com Selenium para UI end-to-end
- Criar dashboard de análise de dados com pandas/plotly no frontend
- Migrar dados para banco de dados relacional com histórico de versões
- Implementar webhooks para notificações de decisão
