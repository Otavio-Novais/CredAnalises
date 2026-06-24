"""
O que vai aqui: A prova real da independência das condições booleanas.

Tática: Você precisará de um teste para cada linha da sua tabela verdade simplificada, 
alternando Renda, Score e Co-garantidor para provar que a mudança de uma única variável altera o resultado final da aprovação.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/credit_engine')))

import pytest
from src.credit_engine.rules import avaliar_credito
from src.credit_engine.schemas import ClienteSchema

# Base do cliente padrão para os testes de MC/DC (Idade e nome limpo perfeitos)
CLIENTE_BASE = {
    "idade": 30,
    "valor_imovel": 300000.0,
    "nome_sujo": False,
    "anos_trabalho": 5
}

# ==============================================================================
# PARES DE TESTE MC/DC
# ==============================================================================

def test_mcdc_condicao_A_renda_alta_independente():
    """
    Provar a independência da Condição A (Renda > 5000).
    Par de teste: Mantém Score=650 (V) e Co-garantidor=False.
    """
    # Caso 1: Renda > 5000 (V) e Score > 600 (V) -> Aprovado
    cliente_v = ClienteSchema(renda_mensal=5500.0, score=650, co_garantidor=False, **CLIENTE_BASE)
    assert avaliar_credito(cliente_v) == "Aprovado"

    # Caso 2: Renda <= 5000 (F) e Score > 600 (V) -> Análise Humana
    cliente_f = ClienteSchema(renda_mensal=4500.0, score=650, co_garantidor=False, **CLIENTE_BASE)
    assert avaliar_credito(cliente_f) == "Análise humana"


def test_mcdc_condicao_B_score_independente():
    """
    Provar a independência da Condição B (Score > 600).
    Par de teste: Mantém Renda=5500 (V) e Co-garantidor=False.
    """
    # Caso 1 (Repetido implicitamente para comparação): Renda > 5000 (V) e Score > 600 (V) -> Aprovado
    cliente_v = ClienteSchema(renda_mensal=5500.0, score=650, co_garantidor=False, **CLIENTE_BASE)
    assert avaliar_credito(cliente_v) == "Aprovado"

    # Caso 3: Renda > 5000 (V) e Score <= 600 (F) -> Análise Humana
    cliente_f = ClienteSchema(renda_mensal=5500.0, score=550, co_garantidor=False, **CLIENTE_BASE)
    assert avaliar_credito(cliente_f) == "Análise humana"


def test_mcdc_condicao_C_co_garantidor_independente():
    """
    Provar a independência da Condição C (Possui Co-garantidor).
    Par de teste: Mantém Renda=3500 (V para D, F para A) e Score=550 (F).
    """
    # Caso 4: Renda > 3000 (V), Score < 600 (F) e Co-garantidor (V) -> Aprovado
    cliente_v = ClienteSchema(renda_mensal=3500.0, score=550, co_garantidor=True, **CLIENTE_BASE)
    assert avaliar_credito(cliente_v) == "Aprovado"

    # Caso 5: Renda > 3000 (V), Score < 600 (F) e Co-garantidor (F) -> Análise Humana
    cliente_f = ClienteSchema(renda_mensal=3500.0, score=550, co_garantidor=False, **CLIENTE_BASE)
    assert avaliar_credito(cliente_f) == "Análise humana"