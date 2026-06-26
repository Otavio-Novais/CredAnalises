
import pytest
from credit_engine.schemas import ClienteSchema
from credit_engine.repository import InMemoryCreditRepository
from credit_engine.service import CreditService


def cliente_factory(**overrides) -> ClienteSchema:
    defaults = {
        "nome": "João da Silva",
        "idade": 30,
        "renda_mensal": 6000.0,
        "score_credito": 850,
        "possui_nome_sujo": False,
        "possui_co_garantidor": False,
        "tipo_financiamento": "IMOBILIARIO",
    }
    defaults.update(overrides)
    return ClienteSchema(**defaults)


@pytest.fixture
def cliente_perfeito() -> ClienteSchema:
    """Cliente com todos os atributos no melhor cenário possível."""
    return cliente_factory()


@pytest.fixture
def in_memory_service() -> CreditService:
    """CreditService com repositório em memória — para testes de service."""
    return CreditService(InMemoryCreditRepository())
