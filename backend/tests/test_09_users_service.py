import pytest
import hashlib

from credit_engine.user_service import UserService
from credit_engine.repository import InMemoryUserRepository


# Verifica se um usuario pode ser registrado corretamente e se a senha nao fica salva em texto puro.
def test_registrar_usuario():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    usuario = service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    assert usuario.id == 1
    assert usuario.nome == "Davi Torres"
    assert usuario.email == "davi@email.com"

    salvo = repo.buscar_usuario_por_email("davi@email.com")
    assert salvo is not None
    assert salvo.senha_hash != "123456"
    assert salvo.senha_salt is not None
    assert len(salvo.senha_hash) > 0


# Verifica se o sistema impede cadastro com email ja existente.
def test_email_duplicado():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    with pytest.raises(ValueError, match="email ja cadastrado"):
        service.registrar_usuario(
            nome="Outro Nome",
            email="davi@email.com",
            senha="abcdef"
        )

    assert len(repo._usuarios) == 1


def test_login_email_inexistente():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    with pytest.raises(ValueError, match="credenciais invalidas"):
        service.login(
            email="nao_existe@email.com",
            senha="123456"
        )


# Verifica se um usuario valido consegue fazer login e receber um token de autenticacao.
def test_login_valido():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    resposta = service.login(
        email="davi@email.com",
        senha="123456"
    )

    assert resposta["token"] is not None
    assert len(resposta["token"]) == 64
    assert all(caractere in "0123456789abcdef" for caractere in resposta["token"])
    assert set(resposta.keys()) == {"token", "usuario"}
    assert resposta["usuario"].email == "davi@email.com"
    assert len(repo._sessoes) == 1
    assert repo._sessoes[0].token_hash == hashlib.sha256(resposta["token"].encode()).hexdigest()


# Verifica se o login falha quando a senha esta incorreta.
def test_login_invalido():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    with pytest.raises(ValueError, match="credenciais invalidas"):
        service.login(
            email="davi@email.com",
            senha="senha_errada"
        )

    with pytest.raises(ValueError) as excinfo_senha:
        service.login(
            email="davi@email.com",
            senha="senha_errada"
        )

    assert str(excinfo_senha.value) == "credenciais invalidas"

    with pytest.raises(ValueError) as excinfo_email:
        service.login(
            email="nao_existe@email.com",
            senha="senha_errada"
        )

    assert str(excinfo_email.value) == "credenciais invalidas"


# Verifica se o sistema consegue recuperar o usuario a partir do token gerado no login.
def test_buscar_usuario_por_token():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    resposta = service.login(
        email="davi@email.com",
        senha="123456"
    )

    usuario = service.buscar_usuario_por_token(resposta["token"])

    assert usuario is not None
    assert usuario.email == "davi@email.com"


def test_buscar_usuario_por_token_passa_hash_correto_para_repositorio():
    class FakeRepo:
        def __init__(self):
            self.received_hash = None

        def buscar_usuario_por_token_hash(self, token_hash):
            self.received_hash = token_hash
            return None

    repo = FakeRepo()
    service = UserService(repo)

    service.buscar_usuario_por_token("meu-token")

    esperado = hashlib.sha256("meu-token".encode()).hexdigest()
    assert repo.received_hash == esperado


def test_login_token_tem_tamanho_exato_e_usuario_preservado():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    service.registrar_usuario(
        nome="Davi Torres",
        email="davi2@email.com",
        senha="123456"
    )

    resposta = service.login(
        email="davi2@email.com",
        senha="123456"
    )

    assert len(resposta["token"]) == 64
    assert resposta["usuario"].email == "davi2@email.com"


def test_buscar_usuario_por_token_inexistente_retorna_none():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    assert service.buscar_usuario_por_token("token-que-nao-existe") is None


def test_repositorio_usuario_inicia_vazio():
    repo = InMemoryUserRepository()

    assert repo._usuarios == []
    assert repo._sessoes == []
    assert repo._next_user_id == 1
    assert repo._next_session_id == 1


def test_buscar_usuario_por_token_hash_direto():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    usuario = service.registrar_usuario(
        nome="Davi Torres",
        email="davi@email.com",
        senha="123456"
    )

    resposta = service.login(
        email="davi@email.com",
        senha="123456"
    )

    token_hash = hashlib.sha256(resposta["token"].encode()).hexdigest()
    encontrado = repo.buscar_usuario_por_token_hash(token_hash)

    assert encontrado is not None
    assert encontrado.id == usuario.id


def test_repositorio_usuario_cria_usuario_sessao_e_filtra_por_token():
    repo = InMemoryUserRepository()

    usuario_1 = repo.criar_usuario(
        nome="Usuario 1",
        email="u1@email.com",
        senha_hash="hash-1",
        senha_salt="salt-1",
    )
    usuario_2 = repo.criar_usuario(
        nome="Usuario 2",
        email="u2@email.com",
        senha_hash="hash-2",
        senha_salt="salt-2",
    )

    sessao_1 = repo.criar_sessao(usuario_id=usuario_1.id, token_hash="token-hash-1")
    sessao_2 = repo.criar_sessao(usuario_id=usuario_2.id, token_hash="token-hash-2")

    assert usuario_1.id == 1
    assert usuario_2.id == 2
    assert sessao_1.id == 1
    assert sessao_2.id == 2
    assert repo.buscar_usuario_por_id(1).email == "u1@email.com"
    assert repo.buscar_usuario_por_email("u2@email.com").nome == "Usuario 2"
    assert repo.buscar_usuario_por_token_hash("token-hash-1").email == "u1@email.com"
    assert repo.buscar_usuario_por_token_hash("token-hash-2").email == "u2@email.com"
    assert repo.buscar_usuario_por_token_hash("token-invalido") is None


def test_registrar_usuario_bloqueia_email_duplicado_com_repositorio_falso():
    class FakeRepo:
        def __init__(self):
            self.criar_usuario_called = False

        def buscar_usuario_por_email(self, email):
            return object()

        def criar_usuario(self, **kwargs):
            self.criar_usuario_called = True
            raise AssertionError("criar_usuario nao deveria ser chamado quando email existe")

    service = UserService(FakeRepo())

    with pytest.raises(ValueError, match="email ja cadastrado"):
        service.registrar_usuario(
            nome="Duplicado",
            email="dup@email.com",
            senha="123456",
        )


def test_hash_senha_depende_do_salt():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    hash_um = service._gerar_hash_senha("123456", "salt-1")
    hash_um_repetido = service._gerar_hash_senha("123456", "salt-1")
    hash_dois = service._gerar_hash_senha("123456", "salt-2")

    assert hash_um == hash_um_repetido
    assert hash_um != hash_dois


def test_verificar_senha_true_e_false():
    repo = InMemoryUserRepository()
    service = UserService(repo)

    salt = "salt-3"
    senha_hash = service._gerar_hash_senha("123456", salt)

    assert service._verificar_senha("123456", salt, senha_hash) is True
    assert service._verificar_senha("outra-senha", salt, senha_hash) is False