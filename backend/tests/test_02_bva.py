"""
O que vai aqui: Exclusivo para as fronteiras matemáticas.

Tática: Testar estritamente as idades [17, 18, 19] e [74, 75, 76], e os scores [-1, 0, 1] e [999, 1000, 1001].
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/credit_engine')))

import pytest
from src.credit_engine.rules import avaliar_credito
from src.credit_engine.schemas import ClienteSchema

# ==============================================================================
# 1. BVA PARA A FRONTEIRA DE IDADE (Limites: 18 e 75 anos)
# ==============================================================================

@pytest.mark.parametrize(
    "idade, resultado_esperado",
    [
        (17, "Recusado"),  # Limite Inferior - 1 (Inválido)
        (18, "Aprovado"),  # No Limite Inferior (Válido)
        (19, "Aprovado"),  # Limite Inferior + 1 (Válido)
        (74, "Aprovado"),  # Limite Superior - 1 (Válido)
        (75, "Aprovado"),  # No Limite Superior (Válido)
        (76, "Recusado"),  # Limite Superior + 1 (Inválido)
    ]
)
def test_bva_fronteiras_idade(idade, resultado_esperado):
    """Testa os 3 valores das fronteiras inferior (18) e superior (75) da idade"""
    cliente = ClienteSchema(
        idade=idade,
        score=850,  # Mantém o resto perfeito e válido
        renda_mensal=6000.0,
        valor_imovel=300000.0,
        nome_sujo=False,
        co_garantidor=False,
        anos_trabalho=6
    )
    assert avaliar_credito(cliente) == resultado_esperado


# ==============================================================================
# 2. BVA PARA A FRONTEIRA DE SCORE (Limites: 0 e 1000)
# ==============================================================================

@pytest.mark.parametrize(
    "score, resultado_esperado",
    [
        (-1, "Recusado"),   # Limite Inferior - 1 (Inválido)
        (0, "Análise humana"),    # No Limite Inferior (Válido, cai na análise humana por score baixo)
        (1, "Análise humana"),    # Limite Inferior + 1 (Válido)
        (999, "Aprovado"),  # Limite Superior - 1 (Válido)
        (1000, "Aprovado"), # No Limite Superior (Válido)
        (1001, "Recusado"), # Limite Superior + 1 (Inválido)
    ]
)
def test_bva_fronteiras_score(score, resultado_esperado):
    """Testa os 3 valores das fronteiras inferior (0) e superior (1000) do score de crédito"""
    cliente = ClienteSchema(
        idade=30,
        score=score,
        renda_mensal=6000.0,  # Renda alta para tentar aprovação nos scores válidos
        valor_imovel=300000.0,
        nome_sujo=False,
        co_garantidor=False,
        anos_trabalho=6
    )
    assert avaliar_credito(cliente) == resultado_esperado