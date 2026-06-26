
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from credit_engine.repository import CreditRepository, SimulacaoRecord


# Em produção (Heroku), DATABASE_URL vem da variável de ambiente.
# Localmente, usamos SQLite no arquivo creditcalc.db.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creditcalc.db")

# O Heroku fornece URLs PostgreSQL no formato "postgres://...",
# mas o SQLAlchemy moderno exige "postgresql://..."
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 
class Base(DeclarativeBase):
    pass


class SimulacaoORM(Base):
    """
    Modelo ORM da tabela 'simulacoes'.
    Cada instância desta classe = uma linha na tabela.
    """
    __tablename__ = "simulacoes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome_proponente = Column(String, nullable=False)
    status_proposta = Column(String, nullable=False)     # APROVADO | ANALISE_HUMANA | RECUSADO
    taxa_juros_aplicada = Column(Float, nullable=True)   # Null para recusados
    motivo_decisao = Column(String, nullable=False)
    data_processamento = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    hash_requisicao = Column(String, unique=True, index=True, nullable=False)


def criar_tabelas():
    """Cria todas as tabelas no banco se não existirem."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



class SqlCreditRepository(CreditRepository):
    """
    Repositório real que persiste no banco via SQLAlchemy.
    Usado em produção e nos testes de integração.
    """

    def __init__(self, db: Session):
        self.db = db

    def salvar_simulacao(
        self,
        nome_proponente: str,
        status_proposta: str,
        taxa_juros_aplicada: Optional[float],
        motivo_decisao: str,
        hash_requisicao: str,
    ) -> SimulacaoRecord:
        orm_obj = SimulacaoORM(
            nome_proponente=nome_proponente,
            status_proposta=status_proposta,
            taxa_juros_aplicada=taxa_juros_aplicada,
            motivo_decisao=motivo_decisao,
            hash_requisicao=hash_requisicao,
        )
        self.db.add(orm_obj)
        self.db.commit()
        self.db.refresh(orm_obj)
        return self._to_record(orm_obj)

    def buscar_por_hash(self, hash_requisicao: str) -> Optional[SimulacaoRecord]:
        orm_obj = (
            self.db.query(SimulacaoORM)
            .filter(SimulacaoORM.hash_requisicao == hash_requisicao)
            .first()
        )
        return self._to_record(orm_obj) if orm_obj else None

    def listar_simulacoes(self, limite: int = 50) -> list[SimulacaoRecord]:
        resultados = (
            self.db.query(SimulacaoORM)
            .order_by(SimulacaoORM.id.desc())
            .limit(limite)
            .all()
        )
        return [self._to_record(r) for r in resultados]

    @staticmethod
    def _to_record(orm_obj: SimulacaoORM) -> SimulacaoRecord:
        """Converte objeto ORM para SimulacaoRecord (desacopla ORM do resto)."""
        return SimulacaoRecord(
            id=orm_obj.id,
            nome_proponente=orm_obj.nome_proponente,
            status_proposta=orm_obj.status_proposta,
            taxa_juros_aplicada=orm_obj.taxa_juros_aplicada,
            motivo_decisao=orm_obj.motivo_decisao,
            data_processamento=orm_obj.data_processamento,
            hash_requisicao=orm_obj.hash_requisicao,
        )
