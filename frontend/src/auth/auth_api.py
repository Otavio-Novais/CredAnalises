"""
Módulo de comunicação com a API de autenticação.
=================================================

Separa toda a lógica HTTP de autenticação em um lugar só.
O app.py chama estas funções sem saber os detalhes do protocolo.

Padrão de autenticação da API (implementado pela equipe):
  - Login retorna um token
  - Requisições autenticadas enviam: Authorization: Bearer <token>
  - O backend vincula simulações ao usuário quando o token está presente
"""

import requests

API_BASE_URL = "http://localhost:8000"
TIMEOUT = 10


def registrar(nome: str, email: str, senha: str) -> dict:
    """
    Cadastra um novo usuário.
    POST /api/v1/users/register

    Retorna:
        {"ok": True, "dados": {...}}    → usuário criado
        {"ok": False, "erro": "..."}    → email duplicado ou erro
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/users/register",
            json={"nome": nome, "email": email, "senha": senha},
            timeout=TIMEOUT,
        )
        if resp.status_code == 201:
            return {"ok": True, "dados": resp.json()}
        elif resp.status_code == 400:
            # email já cadastrado
            return {"ok": False, "erro": resp.json().get("detail", "Erro no cadastro")}
        elif resp.status_code == 422:
            # validação Pydantic (senha curta, email inválido)
            detalhes = resp.json().get("detail", [])
            msgs = [e.get("msg", "") for e in detalhes]
            return {"ok": False, "erro": "Dados inválidos: " + "; ".join(msgs)}
        else:
            return {"ok": False, "erro": f"Erro {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline. Verifique se o backend está rodando."}
    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "A API demorou demais para responder."}


def login(email: str, senha: str) -> dict:
    """
    Faz login e retorna o token de acesso.
    POST /api/v1/users/login

    Retorna:
        {"ok": True, "token": "...", "usuario": {...}}
        {"ok": False, "erro": "credenciais invalidas"}
    """
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/users/login",
            json={"email": email, "senha": senha},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            dados = resp.json()
            return {
                "ok": True,
                "token": dados["token"],
                "usuario": dados["usuario"],
            }
        elif resp.status_code == 401:
            return {"ok": False, "erro": "Email ou senha incorretos."}
        else:
            return {"ok": False, "erro": f"Erro {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline. Verifique se o backend está rodando."}
    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "A API demorou demais para responder."}


def buscar_meus_dados(token: str) -> dict:
    """
    Retorna os dados do usuário logado.
    GET /api/v1/users/me  (requer Bearer token)
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return {"ok": True, "dados": resp.json()}
        elif resp.status_code == 401:
            return {"ok": False, "erro": "Sessão expirada. Faça login novamente."}
        else:
            return {"ok": False, "erro": f"Erro {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline."}


def buscar_meu_historico(token: str, limite: int = 50) -> dict:
    """
    Retorna o histórico de simulações DO USUÁRIO logado.
    GET /api/v1/users/me/history  (requer Bearer token)

    Este é o "consultar mais rápido" — o usuário vê só as simulações dele.
    """
    try:
        resp = requests.get(
            f"{API_BASE_URL}/api/v1/users/me/history",
            headers={"Authorization": f"Bearer {token}"},
            params={"limite": limite},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return {"ok": True, "dados": resp.json()}
        elif resp.status_code == 401:
            return {"ok": False, "erro": "Sessão expirada. Faça login novamente."}
        else:
            return {"ok": False, "erro": f"Erro {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline."}


def avaliar_credito_autenticado(dados: dict, token: str | None = None) -> dict:
    """
    Avalia crédito, vinculando ao usuário se houver token.
    POST /api/v1/credit/evaluate

    Se token for None → avaliação anônima (não salva no histórico do usuário)
    Se token existir  → header Bearer, simulação vinculada ao usuário logado

    Este é o "vínculo opcional" da API: o mesmo endpoint funciona
    logado ou anônimo, dependendo da presença do token.
    """
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/v1/credit/evaluate",
            json=dados,
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return {"ok": True, "dados": resp.json()}
        elif resp.status_code == 422:
            detalhes = resp.json().get("detail", [])
            if isinstance(detalhes, list):
                msgs = [f"{e.get('loc',['?'])[-1]}: {e.get('msg','')}" for e in detalhes]
                return {"ok": False, "erro": "Dados inválidos: " + "; ".join(msgs)}
            return {"ok": False, "erro": str(detalhes)}
        else:
            return {"ok": False, "erro": f"Erro {resp.status_code}: {resp.text}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline. Verifique se o backend está rodando."}
    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "A API demorou demais para responder."}
