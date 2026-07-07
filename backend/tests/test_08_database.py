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

        setattr(sqlalchemy_module, "create_engine", create_engine)
        setattr(sqlalchemy_module, "Column", DummyColumn)
        setattr(sqlalchemy_module, "Integer", DummySQLType())
        setattr(sqlalchemy_module, "String", DummySQLType())
        setattr(sqlalchemy_module, "Float", DummySQLType())
        setattr(sqlalchemy_module, "DateTime", DummySQLType())
        setattr(orm_module, "DeclarativeBase", DummyDeclarativeBase)
        setattr(orm_module, "sessionmaker", sessionmaker)
        setattr(orm_module, "Session", object)

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
        def __eq__(self, other):
            return ("eq", other)

        def desc(self):
            return ("desc",)

    class FakeSimulacaoORM:
        id = FakeColumn()
        hash_requisicao = FakeColumn()

        def __init__(self, **kwargs):
            self.received_kwargs = dict(kwargs)
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
            self.filter_args = None
            self.order_by_args = None
            self.limit_arg = None

        def filter(self, *args, **kwargs):
            self.filter_args = args
            return self

        def order_by(self, *args, **kwargs):
            self.order_by_args = args
            return self

        def limit(self, *args, **kwargs):
            self.limit_arg = args[0] if args else None
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
            self.last_query_model = None
            self.last_query = None

        def add(self, obj):
            self.added = obj

        def commit(self):
            self.committed = True

        def refresh(self, obj):
            self.refreshed = obj

        def query(self, model):
            self.last_query_model = model
            self.last_query = FakeQuery(self.query_result)
            return self.last_query

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
    assert fake_db.added.nome_proponente == "Renan Momo"
    assert fake_db.added.status_proposta == "APROVADO"
    assert fake_db.added.taxa_juros_aplicada == 4.5
    assert fake_db.added.motivo_decisao == "Aprovado"
    assert fake_db.added.hash_requisicao == "hash-123"
    assert fake_db.added.received_kwargs == {
        "nome_proponente": "Renan Momo",
        "status_proposta": "APROVADO",
        "taxa_juros_aplicada": 4.5,
        "motivo_decisao": "Aprovado",
        "hash_requisicao": "hash-123",
    }
    assert fake_db.committed is True
    assert fake_db.refreshed is fake_db.added
    assert registro.nome_proponente == "Renan Momo"
    assert registro.status_proposta == "APROVADO"
    assert registro.taxa_juros_aplicada == 4.5
    assert registro.motivo_decisao == "Aprovado"
    assert registro.hash_requisicao == "hash-123"

    encontrado = repository.buscar_por_hash("hash-123")
    assert fake_db.last_query_model is FakeSimulacaoORM
    query_busca = fake_db.last_query
    assert query_busca is not None
    assert query_busca.filter_args == (("eq", "hash-123"),)
    assert encontrado.hash_requisicao == "hash-123"

    historico = repository.listar_simulacoes(limite=5)
    assert fake_db.last_query_model is FakeSimulacaoORM
    query_historico = fake_db.last_query
    assert query_historico is not None
    assert query_historico.order_by_args == (("desc",),)
    assert query_historico.limit_arg == 5
    assert len(historico) == 1
    assert historico[0].id == 10

    historico_padrao = repository.listar_simulacoes()
    assert fake_db.last_query_model is FakeSimulacaoORM
    query_padrao = fake_db.last_query
    assert query_padrao is not None
    assert query_padrao.order_by_args == (("desc",),)
    assert query_padrao.limit_arg == 50
    assert len(historico_padrao) == 1
    assert historico_padrao[0].id == 10


def test_sql_credit_repository_filtra_por_usuario_id(monkeypatch):
    database_module = load_database_module()

    class FakeColumn:
        def __eq__(self, other):
            return ("eq", other)

        def desc(self):
            return ("desc",)

    class FakeSimulacaoORM:
        id = FakeColumn()
        hash_requisicao = FakeColumn()
        usuario_id = FakeColumn()

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(database_module, "SimulacaoORM", FakeSimulacaoORM)

    class FakeOrmObj:
        id = 11
        nome_proponente = "Cliente 1"
        status_proposta = "APROVADO"
        taxa_juros_aplicada = 4.0
        motivo_decisao = "ok"
        data_processamento = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)
        hash_requisicao = "hash-user-1"
        usuario_id = 99

    class FakeQuery:
        def __init__(self, result):
            self.result = result
            self.filter_args = None
            self.order_by_args = None
            self.limit_arg = None

        def filter(self, *args, **kwargs):
            self.filter_args = args
            return self

        def order_by(self, *args, **kwargs):
            self.order_by_args = args
            return self

        def limit(self, *args, **kwargs):
            self.limit_arg = args[0] if args else None
            return self

        def first(self):
            return self.result

        def all(self):
            return [self.result]

    class FakeDb:
        def __init__(self):
            self.last_query_model = None
            self.last_query = None

        def query(self, model):
            self.last_query_model = model
            self.last_query = FakeQuery(FakeOrmObj())
            return self.last_query

    repository = database_module.SqlCreditRepository(FakeDb())

    registros = repository.listar_simulacoes_por_usuario(usuario_id=99, limite=7)

    query = repository.db.last_query
    assert query is not None
    assert repository.db.last_query_model is FakeSimulacaoORM
    assert query.filter_args == (("eq", 99),)
    assert query.order_by_args == (("desc",),)
    assert query.limit_arg == 7
    assert len(registros) == 1
    assert registros[0].usuario_id == 99


def test_sql_credit_repository_to_record_preserva_usuario_id_nulo(monkeypatch):
    database_module = load_database_module()

    class FakeOrmObj:
        id = 12
        nome_proponente = "Cliente Anonimo"
        status_proposta = "RECUSADO"
        taxa_juros_aplicada = None
        motivo_decisao = "sem perfil"
        data_processamento = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)
        hash_requisicao = "hash-anonimo"

    record = database_module.SqlCreditRepository._to_record(FakeOrmObj())

    assert record.usuario_id is None
    assert record.nome_proponente == "Cliente Anonimo"


def test_sql_credit_repository_persiste_usuario_id(monkeypatch):
    database_module = load_database_module()

    class FakeSimulacaoORM:
        def __init__(self, **kwargs):
            self.received_kwargs = dict(kwargs)
            for key, value in kwargs.items():
                setattr(self, key, value)
            self.id = 13
            self.data_processamento = datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(database_module, "SimulacaoORM", FakeSimulacaoORM)

    class FakeDb:
        def __init__(self):
            self.added = None
            self.committed = False
            self.refreshed = None

        def add(self, obj):
            self.added = obj

        def commit(self):
            self.committed = True

        def refresh(self, obj):
            self.refreshed = obj

    repo = database_module.SqlCreditRepository(FakeDb())

    registro = repo.salvar_simulacao(
        nome_proponente="Cliente 77",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.1,
        motivo_decisao="ok",
        hash_requisicao="hash-77",
        usuario_id=77,
    )

    assert repo.db.added is not None
    assert repo.db.added.received_kwargs["usuario_id"] == 77
    assert repo.db.committed is True
    assert repo.db.refreshed is repo.db.added
    assert registro.usuario_id == 77