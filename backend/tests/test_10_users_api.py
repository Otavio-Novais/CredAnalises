from uuid import uuid4

from fastapi.testclient import TestClient

from credit_engine.main import app, get_user_service
from credit_engine.user_service import UserService
from credit_engine.repository import InMemoryUserRepository


# Cria um cliente HTTP com serviço de usuários isolado para cada teste.
def criar_client():
    user_repo = InMemoryUserRepository()
    user_service = UserService(user_repo)

    app.dependency_overrides[get_user_service] = lambda: user_service

    client = TestClient(app)
    return client


# Gera um sufixo único para evitar colisão de email.
def sufixo_unico() -> str:
    return uuid4().hex[:8]


# Verifica se o endpoint de cadastro cria um novo usuário.
def test_register_user():
    client = criar_client()
    sufixo = sufixo_unico()

    payload = {
        "nome": "Davi Torres",
        "email": f"davi_{sufixo}@email.com",
        "senha": "123456"
    }

    response = client.post("/api/v1/users/register", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Davi Torres"
    assert body["email"] == f"davi_{sufixo}@email.com"


# Verifica se o endpoint de login retorna um token válido.
def test_login_user():
    client = criar_client()
    sufixo = sufixo_unico()

    register_payload = {
        "nome": "Davi Torres",
        "email": f"davi_{sufixo}@email.com",
        "senha": "123456"
    }

    login_payload = {
        "email": f"davi_{sufixo}@email.com",
        "senha": "123456"
    }

    client.post("/api/v1/users/register", json=register_payload)
    response = client.post("/api/v1/users/login", json=login_payload)

    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    assert body["usuario"]["email"] == f"davi_{sufixo}@email.com"


# Verifica se o endpoint /me retorna o usuário autenticado.
def test_me_user():
    client = criar_client()
    sufixo = sufixo_unico()

    register_payload = {
        "nome": "Davi Torres",
        "email": f"davi_{sufixo}@email.com",
        "senha": "123456"
    }

    login_payload = {
        "email": f"davi_{sufixo}@email.com",
        "senha": "123456"
    }

    client.post("/api/v1/users/register", json=register_payload)
    login_response = client.post("/api/v1/users/login", json=login_payload)

    token = login_response.json()["token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == f"davi_{sufixo}@email.com"