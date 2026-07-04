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

- React 19.
- Vite.
- React Router.
- TanStack React Query.
- Axios.

### Testes e Qualidade

- Pytest.
- Pytest-cov.
- Radon.
- Mutmut.

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

### 1. Instalar dependências do frontend

As dependências do frontend ficam na pasta `frontend/`:

```bash
npm run install:all
```

### 2. Instalar dependências do backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execução Local

### Backend

Na raiz do repositório:

```bash
npm run dev:backend
```

Ou diretamente no diretório backend:

```bash
cd backend
uvicorn credit_engine.main:app --app-dir src --reload
```

Por padrão, a API sobe em `http://127.0.0.1:8000`.

### Frontend

Na raiz do repositório:

```bash
npm run dev:frontend
```

Ou diretamente na pasta frontend:

```bash
cd frontend
npm run dev
```

### Build do Frontend

```bash
npm run build:frontend
```

## Testes

Os testes automatizados do backend estão organizados por técnica de validação:

- `test_01_equivalence.py`: classes de equivalência.
- `test_02_bva.py`: análise de valor limite.
- `test_03_mcdc.py`: MC/DC.
- `test_04_data_flow.py`: fluxo de dados.

Para executar a suíte:

```bash
cd backend
pytest
```

Para cobertura:

```bash
cd backend
pytest --cov=credit_engine
```

## Qualidade e Análise

O projeto já inclui ferramentas úteis para análise estrutural e mutação de testes:

```bash
cd backend
radon cc src/credit_engine
mutmut run
```

## Variáveis de Ambiente

- `DATABASE_URL`: string de conexão do banco de dados.
- `PORT`: usado no frontend ao publicar a aplicação com `serve`.

Se `DATABASE_URL` não estiver definida, o backend usa SQLite local em `./creditcalc.db`.

## Observações de Implantação

- O backend já está configurado para CORS aberto em desenvolvimento.
- O `Procfile` existe tanto em backend quanto frontend para facilitar deploys em plataformas compatíveis.
- Em produção, recomenda-se restringir o CORS para o domínio do frontend.

## Próximos Passos Possíveis

- Implementar uma interface completa no frontend para consumo da API.
- Adicionar exemplos de payload e respostas no README com base em cenários de teste.
- Incluir diagrama de fluxo da análise de crédito para apresentação acadêmica.
