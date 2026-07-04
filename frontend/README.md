# Frontend - CreditCalc Engine (Streamlit)

Interface web para o motor de análise de crédito construída com **Streamlit**.

## Requisitos

- Python 3.8+
- `pip` ou `pip3`

## Instalação

### 1. Criar ambiente virtual (recomendado)

```bash
cd frontend
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r src/requirements.txt
```

## Executar Localmente

```bash
cd src
streamlit run app.py
```

A aplicação abrirá em `http://localhost:8501`

## Dependências

- **streamlit**: Framework para UI interativa
- **requests**: Cliente HTTP para comunicar com o backend
- **pandas**: Manipulação de dados

## Configuração da API

Por padrão, o app espera que o backend está rodando em `http://localhost:8000`.

Para mudar o URL da API, edite `src/app.py`:

```python
API_BASE_URL = "http://seu-backend-url:porta"
```

## Deployment (Heroku)

O `Procfile` está configurado para rodar o Streamlit em produção:

```
web: cd src && streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

