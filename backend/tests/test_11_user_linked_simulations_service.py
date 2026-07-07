import hashlib
import json

from credit_engine.schemas import ClienteSchema
from credit_engine.service import CreditService
from credit_engine.repository import InMemoryCreditRepository
from datetime import datetime, timezone


# Cria um cliente válido para os testes de serviço.
def criar_cliente(nome: str) -> ClienteSchema:
    return ClienteSchema(
        nome=nome,
        idade=30,
        renda_mensal=8000.0,
        score_credito=800,
        possui_nome_sujo=False,
        possui_co_garantidor=False,
        tipo_financiamento="IMOBILIARIO",
    )


# Verifica se uma simulação anônima é salva sem usuario_id.
def test_simulacao_anonima_salva_sem_usuario():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Anonimo")
    service.avaliar_credito(cliente)

    registro = repo.listar_simulacoes(limite=1)[0]

    assert registro.nome_proponente == "Cliente Anonimo"
    assert registro.usuario_id is None


# Verifica se uma simulação autenticada é salva com usuario_id.
def test_simulacao_autenticada_salva_com_usuario():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Autenticado")
    service.avaliar_credito(cliente, usuario_id=7)

    registro = repo.listar_simulacoes(limite=1)[0]

    assert registro.nome_proponente == "Cliente Autenticado"
    assert registro.usuario_id == 7


# Verifica se o hash muda entre contexto anônimo e autenticado.
def test_hash_muda_entre_anonimo_e_autenticado():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Hash")

    hash_anonimo = service._gerar_hash(cliente)
    hash_usuario = service._gerar_hash(cliente, usuario_id=5)

    assert hash_anonimo != hash_usuario


# Verifica se o histórico pode ser filtrado por usuário.
def test_historico_filtrado_por_usuario():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente_a = criar_cliente("Cliente Usuario 1")
    cliente_b = criar_cliente("Cliente Usuario 2")
    cliente_c = criar_cliente("Cliente Anonimo 2")

    service.avaliar_credito(cliente_a, usuario_id=1)
    service.avaliar_credito(cliente_b, usuario_id=2)
    service.avaliar_credito(cliente_c)

    historico_usuario_1 = service.listar_historico(usuario_id=1)
    historico_usuario_2 = service.listar_historico(usuario_id=2)
    historico_geral = service.listar_historico()

    assert len(historico_usuario_1) == 1
    assert historico_usuario_1[0].nome_proponente == "Cliente Usuario 1"
    assert historico_usuario_1[0].usuario_id == 1

    assert len(historico_usuario_2) == 1
    assert historico_usuario_2[0].nome_proponente == "Cliente Usuario 2"
    assert historico_usuario_2[0].usuario_id == 2

    assert len(historico_geral) == 3


# Verifica se duas simulações iguais podem coexistir quando uma é anônima e outra autenticada.
def test_simulacao_anonima_e_autenticada_nao_colidem_no_cache():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Escopo")

    resposta_anonima = service.avaliar_credito(cliente)
    resposta_autenticada = service.avaliar_credito(cliente, usuario_id=10)

    historico = service.listar_historico()

    assert len(historico) == 2
    assert resposta_anonima.status_proposta == resposta_autenticada.status_proposta


def test_listar_historico_com_usuario_id_usa_repositorio_filtrado():
    class FakeRepo:
        def __init__(self):
            self.received_usuario_id = None
            self.received_limite = None

        def listar_simulacoes(self, limite=50):
            self.received_limite = limite
            return ["geral"]

        def listar_simulacoes_por_usuario(self, usuario_id, limite=50):
            self.received_usuario_id = usuario_id
            self.received_limite = limite
            return ["filtrado"]

    repo = FakeRepo()
    service = CreditService(repo)

    assert service.listar_historico(usuario_id=42, limite=3) == ["filtrado"]
    assert repo.received_usuario_id == 42
    assert repo.received_limite == 3


def test_avaliar_credito_autenticado_reaproveita_cache_do_mesmo_usuario():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Cache Usuario")

    primeira = service.avaliar_credito(cliente, usuario_id=7)
    segunda = service.avaliar_credito(cliente, usuario_id=7)

    assert primeira.motivo_decisao.startswith("A") or primeira.motivo_decisao.startswith("[CACHE]")
    assert segunda.motivo_decisao.startswith("[CACHE]")
    assert len(repo.listar_simulacoes()) == 1
    assert repo.listar_simulacoes()[0].usuario_id == 7


def test_gerar_hash_inclui_usuario_id_exatamente():
    repo = InMemoryCreditRepository()
    service = CreditService(repo)

    cliente = criar_cliente("Cliente Hash Exato")

    dados_anonimos = {
        "nome": cliente.nome,
        "idade": cliente.idade,
        "renda_mensal": cliente.renda_mensal,
        "score_credito": cliente.score_credito,
        "possui_nome_sujo": cliente.possui_nome_sujo,
        "possui_co_garantidor": cliente.possui_co_garantidor,
        "tipo_financiamento": cliente.tipo_financiamento,
    }
    dados_usuario = dict(dados_anonimos)
    dados_usuario["usuario_id"] = 7

    esperado_anonimo = hashlib.md5(json.dumps(dados_anonimos, sort_keys=True).encode()).hexdigest()
    esperado_usuario = hashlib.md5(json.dumps(dados_usuario, sort_keys=True).encode()).hexdigest()

    assert service._gerar_hash(cliente) == esperado_anonimo
    assert service._gerar_hash(cliente, usuario_id=7) == esperado_usuario
    assert esperado_anonimo != esperado_usuario


def test_repositorio_credito_lista_por_usuario_e_limite():
    repo = InMemoryCreditRepository()

    registro_1 = repo.salvar_simulacao(
        nome_proponente="Cliente 1",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.5,
        motivo_decisao="ok",
        hash_requisicao="hash-1",
        usuario_id=10,
    )
    registro_2 = repo.salvar_simulacao(
        nome_proponente="Cliente 2",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.2,
        motivo_decisao="ok",
        hash_requisicao="hash-2",
        usuario_id=20,
    )
    registro_3 = repo.salvar_simulacao(
        nome_proponente="Cliente 3",
        status_proposta="RECUSADO",
        taxa_juros_aplicada=None,
        motivo_decisao="ok",
        hash_requisicao="hash-3",
        usuario_id=10,
    )

    assert registro_1.usuario_id == 10
    assert registro_2.usuario_id == 20
    assert registro_3.usuario_id == 10

    historico_usuario_10 = repo.listar_simulacoes_por_usuario(usuario_id=10, limite=10)
    historico_usuario_20 = repo.listar_simulacoes_por_usuario(usuario_id=20, limite=10)
    historico_usuario_10_limite_1 = repo.listar_simulacoes_por_usuario(usuario_id=10, limite=1)

    assert [registro.nome_proponente for registro in historico_usuario_10] == ["Cliente 3", "Cliente 1"]
    assert [registro.nome_proponente for registro in historico_usuario_20] == ["Cliente 2"]
    assert [registro.nome_proponente for registro in historico_usuario_10_limite_1] == ["Cliente 3"]


def test_avaliar_credito_autenticado_preserva_usuario_id_no_cache_e_persistencia():
    class FakeRepo:
        def __init__(self):
            self.saved = []
            self.buscar_por_hash_args = []

        def buscar_por_hash(self, hash_requisicao):
            self.buscar_por_hash_args.append(hash_requisicao)
            return None

        def salvar_simulacao(
            self,
            nome_proponente,
            status_proposta,
            taxa_juros_aplicada,
            motivo_decisao,
            hash_requisicao,
            usuario_id=None,
        ):
            registro = type(
                "Registro",
                (),
                {
                    "id": len(self.saved) + 1,
                    "nome_proponente": nome_proponente,
                    "status_proposta": status_proposta,
                    "taxa_juros_aplicada": taxa_juros_aplicada,
                    "motivo_decisao": motivo_decisao,
                        "data_processamento": datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
                    "hash_requisicao": hash_requisicao,
                    "usuario_id": usuario_id,
                },
            )()
            self.saved.append(registro)
            return registro

        def listar_simulacoes(self, limite=50):
            return list(self.saved)[:limite]

        def listar_simulacoes_por_usuario(self, usuario_id, limite=50):
            return [r for r in self.saved if r.usuario_id == usuario_id][:limite]

    repo = FakeRepo()
    service = CreditService(repo)
    cliente = criar_cliente("Cliente Autenticado Hash")

    resposta = service.avaliar_credito(cliente, usuario_id=77)

    assert repo.saved[-1].usuario_id == 77
    assert repo.buscar_por_hash_args[-1] == service._gerar_hash(cliente, usuario_id=77)
    assert resposta.motivo_decisao.startswith("Aprovado") or resposta.motivo_decisao.startswith("[CACHE]")