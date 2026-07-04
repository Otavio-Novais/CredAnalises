import importlib
import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

from fastapi.testclient import TestClient

from credit_engine.schemas import RespostaSchema


def load_main_module():
    if "sqlalchemy" not in sys.modules:
        sqlalchemy_module = ModuleType("sqlalchemy")
        orm_module = ModuleType("sqlalchemy.orm")

        class DummySQLType:
            def __call__(self, *args, **kwargs):
                return self

        class DummyDeclarativeBase:
            metadata = SimpleNamespace(create_all=lambda **kwargs: None)

        class DummyColumn:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        def create_engine(*args, **kwargs):
            return SimpleNamespace(args=args, kwargs=kwargs)

        def sessionmaker(*args, **kwargs):
            def factory():
                return SimpleNamespace(close=lambda: None)

            return factory

        sqlalchemy_module.create_engine = create_engine
        sqlalchemy_module.Column = DummyColumn
        sqlalchemy_module.Integer = DummySQLType()
        sqlalchemy_module.String = DummySQLType()
        sqlalchemy_module.Float = DummySQLType()
        sqlalchemy_module.DateTime = DummySQLType()
        orm_module.DeclarativeBase = DummyDeclarativeBase
        orm_module.sessionmaker = sessionmaker
        orm_module.Session = object

        sys.modules["sqlalchemy"] = sqlalchemy_module
        sys.modules["sqlalchemy.orm"] = orm_module

    return importlib.import_module("credit_engine.main")


class FakeCreditService:
    def __init__(self):
        self.received_cliente = None
        self.received_limite = None

    def avaliar_credito(self, cliente):
        self.received_cliente = cliente
        return RespostaSchema(
            status_proposta="APROVADO",
            taxa_juros_aplicada=4.5,
            motivo_decisao="Aprovado",
            data_processamento=datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
        )

    def listar_historico(self, limite=50):
        self.received_limite = limite
        return [
            SimpleNamespace(
                id=1,
                nome_proponente="Renan Momo",
                status_proposta="APROVADO",
                taxa_juros_aplicada=4.5,
                motivo_decisao="Aprovado",
                data_processamento=datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc),
            )
        ]


def test_main_routes_exercem_startup_e_fluxo_feliz(monkeypatch):
    main_module = load_main_module()
    app = main_module.app
    chamadas = {"criar_tabelas": 0}

    def fake_criar_tabelas():
        chamadas["criar_tabelas"] += 1

    fake_service = FakeCreditService()
    monkeypatch.setattr(main_module, "criar_tabelas", fake_criar_tabelas)
    app.dependency_overrides[main_module.get_credit_service] = lambda: fake_service

    try:
        with TestClient(app) as client:
            resposta_root = client.get("/")
            assert resposta_root.status_code == 200
            assert resposta_root.json() == {"message": "Credit Engine API está rodando!"}

            resposta_health = client.get("/health")
            assert resposta_health.status_code == 200
            assert resposta_health.json() == {"status": "healthy"}

            payload = {
                "nome": "Renan Momo",
                "idade": 30,
                "rendaMensal": 8000.0,
                "scoreCredito": 800,
                "possuiNomeSujo": False,
                "possuiCoGarantidor": False,
                "tipoFinanciamento": "IMOBILIARIO",
            }

            resposta_eval = client.post("/api/v1/credit/evaluate", json=payload)
            assert resposta_eval.status_code == 200
            assert resposta_eval.json()["status_proposta"] == "APROVADO"
            assert resposta_eval.json()["taxa_juros_aplicada"] == 4.5
            assert resposta_eval.json()["motivo_decisao"] == "Aprovado"

            resposta_hist = client.get("/api/v1/history?limite=2")
            assert resposta_hist.status_code == 200
            assert resposta_hist.json()[0]["id"] == 1
            assert fake_service.received_limite == 2

        assert chamadas["criar_tabelas"] == 1
        assert fake_service.received_cliente is not None
    finally:
        app.dependency_overrides.clear()


def test_main_avaliar_credito_converte_value_error_em_422():
    main_module = load_main_module()
    app = main_module.app

    class RaisingService:
        def avaliar_credito(self, cliente):
            raise ValueError("tipo_financiamento inválido")

    app.dependency_overrides[main_module.get_credit_service] = lambda: RaisingService()

    try:
        with TestClient(app) as client:
            payload = {
                "nome": "Renan Momo",
                "idade": 30,
                "rendaMensal": 8000.0,
                "scoreCredito": 800,
                "possuiNomeSujo": False,
                "possuiCoGarantidor": False,
                "tipoFinanciamento": "IMOBILIARIO",
            }

            resposta = client.post("/api/v1/credit/evaluate", json=payload)
            assert resposta.status_code == 422
            assert resposta.json() == {"detail": "tipo_financiamento inválido"}
    finally:
        app.dependency_overrides.clear()


def test_get_credit_service_instancia_repo_e_service():
    main_module = load_main_module()

    capturado = {}

    class FakeRepository:
        pass

    class FakeService:
        def __init__(self, repo):
            capturado["repo"] = repo

    capturado["db"] = None
    original_repo_class = main_module.SqlCreditRepository
    original_service_class = main_module.CreditService

    try:
        def fake_repository_factory(db):
            capturado["db"] = db
            return FakeRepository()

        main_module.SqlCreditRepository = fake_repository_factory
        main_module.CreditService = FakeService

        db_obj = object()
        service = main_module.get_credit_service(db=db_obj)

        assert isinstance(service, FakeService)
        assert isinstance(capturado["repo"], FakeRepository)
        assert capturado["db"] is db_obj
    finally:
        main_module.SqlCreditRepository = original_repo_class
        main_module.CreditService = original_service_class