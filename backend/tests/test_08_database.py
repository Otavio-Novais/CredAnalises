import importlib
import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace


def load_database_module():
    if "sqlalchemy" not in sys.modules:
        sqlalchemy_module = ModuleType("sqlalchemy")
        orm_module = ModuleType("sqlalchemy.orm")

        class DummySQLType:
            def __call__(self, *args, **kwargs):
                return self

        class DummyDeclarativeBase:
            metadata = SimpleNamespace(create_all=lambda **kwargs: None)

            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class DummyColumn:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def desc(self):
                return self

        def create_engine(*args, **kwargs):
            return SimpleNamespace(args=args, kwargs=kwargs)

        def sessionmaker(*args, **kwargs):
            return lambda: SimpleNamespace(close=lambda: None)

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

    return importlib.import_module("credit_engine.database")


def test_criar_tabelas_chama_metadata_create_all(monkeypatch):
    database_module = load_database_module()

    chamado = {}

    def fake_create_all(*, bind):
        chamado["bind"] = bind

    monkeypatch.setattr(database_module.Base.metadata, "create_all", fake_create_all)

    database_module.criar_tabelas()

    assert chamado["bind"] == database_module.engine


def test_get_db_abre_e_fecha_sessao(monkeypatch):
    database_module = load_database_module()

    fechado = {"value": False}

    class FakeDb:
        def close(self):
            fechado["value"] = True

    monkeypatch.setattr(database_module, "SessionLocal", lambda: FakeDb())

    generator = database_module.get_db()
    db = next(generator)

    assert isinstance(db, FakeDb)

    try:
        next(generator)
    except StopIteration:
        pass

    assert fechado["value"] is True


def test_sql_credit_repository_mapeia_registros(monkeypatch):
    database_module = load_database_module()

    class FakeColumn:
        def desc(self):
            return self

    class FakeSimulacaoORM:
        id = FakeColumn()
        hash_requisicao = FakeColumn()

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            if not hasattr(self, "data_processamento"):
                self.data_processamento = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(database_module, "SimulacaoORM", FakeSimulacaoORM)

    class FakeOrmObj:
        id = 10
        nome_proponente = "Renan Momo"
        status_proposta = "APROVADO"
        taxa_juros_aplicada = 4.5
        motivo_decisao = "Aprovado"
        data_processamento = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)
        hash_requisicao = "hash-123"

    class FakeQuery:
        def __init__(self, result):
            self.result = result

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def first(self):
            return self.result

        def all(self):
            return [self.result]

    class FakeDb:
        def __init__(self):
            self.added = None
            self.committed = False
            self.refreshed = None
            self.query_result = FakeOrmObj()

        def add(self, obj):
            self.added = obj

        def commit(self):
            self.committed = True

        def refresh(self, obj):
            self.refreshed = obj

        def query(self, model):
            return FakeQuery(self.query_result)

    fake_db = FakeDb()
    repository = database_module.SqlCreditRepository(fake_db)

    registro = repository.salvar_simulacao(
        nome_proponente="Renan Momo",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.5,
        motivo_decisao="Aprovado",
        hash_requisicao="hash-123",
    )

    assert fake_db.added is not None
    assert fake_db.committed is True
    assert fake_db.refreshed is fake_db.added
    assert registro.nome_proponente == "Renan Momo"

    encontrado = repository.buscar_por_hash("hash-123")
    assert encontrado.hash_requisicao == "hash-123"

    historico = repository.listar_simulacoes(limite=5)
    assert len(historico) == 1
    assert historico[0].id == 10