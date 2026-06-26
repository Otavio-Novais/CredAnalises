"""
A decisão complexa do sistema (RN02):
    APROVADO se: (A AND B) OR (C AND D)
    onde:
        A = renda_mensal > 5000
        B = score_credito > 600
        C = possui_co_garantidor == True
        D = renda_mensal > 3000

Para cobrir MC/DC, precisamos de um par para cada condição A, B, C, D.
"""

import pytest
from tests.conftest import cliente_factory
from credit_engine.rules import avaliar_credito


# ==============================================================================
# Pares MC/DC para a condição A (renda_mensal > 5000)
# Mantém: B=True (score=650), C=False, D não ativa
# Varia: A
# ==============================================================================

def test_mcdc_condicao_A_renda_alta_determina_resultado():
    """
    Prova que A (renda > 5000) tem impacto independente.
    Contexto: B=True. Mudar A de True→False muda APROVADO→ANALISE_HUMANA.
    """
    # A=True, B=True → APROVADO (via rota padrão)
    cliente_a_verdadeiro = cliente_factory(renda_mensal=5500.0, score_credito=650, possui_co_garantidor=False)
    assert avaliar_credito(cliente_a_verdadeiro)["status"] == "APROVADO"

    # A=False, B=True → não entra na rota padrão → ANALISE_HUMANA (score > 400)
    cliente_a_falso = cliente_factory(renda_mensal=4500.0, score_credito=650, possui_co_garantidor=False)
    assert avaliar_credito(cliente_a_falso)["status"] == "ANALISE_HUMANA"


# ==============================================================================
# Pares MC/DC para a condição B (score_credito > 600)
# Mantém: A=True (renda=5500), C=False
# Varia: B
# ==============================================================================

def test_mcdc_condicao_B_score_determina_resultado():
    """
    Prova que B (score > 600) tem impacto independente.
    Contexto: A=True. Mudar B de True→False muda APROVADO→ANALISE_HUMANA.
    """
    # A=True, B=True → APROVADO
    cliente_b_verdadeiro = cliente_factory(renda_mensal=5500.0, score_credito=650, possui_co_garantidor=False)
    assert avaliar_credito(cliente_b_verdadeiro)["status"] == "APROVADO"

    # A=True, B=False → não entra na rota padrão → ANALISE_HUMANA (score=550 > 400)
    cliente_b_falso = cliente_factory(renda_mensal=5500.0, score_credito=550, possui_co_garantidor=False)
    assert avaliar_credito(cliente_b_falso)["status"] == "ANALISE_HUMANA"


# ==============================================================================
# Pares MC/DC para a condição C (possui_co_garantidor)
# Mantém: A=False (renda=3500, não ativa rota padrão), B=False (score=550), D=True
# Varia: C
# ==============================================================================

def test_mcdc_condicao_C_co_garantidor_determina_resultado():
    """
    Prova que C (co_garantidor) tem impacto independente.
    Contexto: rota padrão não ativa (renda 3500 < 5000 ou score 550 < 600).
    Mudar C de True→False muda APROVADO→ANALISE_HUMANA.
    """
    # C=True, D=True (renda 3500 > 3000) → APROVADO via rota garantidor
    cliente_c_verdadeiro = cliente_factory(renda_mensal=3500.0, score_credito=550, possui_co_garantidor=True)
    assert avaliar_credito(cliente_c_verdadeiro)["status"] == "APROVADO"

    # C=False, D=True → rota garantidor não ativa, rota padrão não ativa → ANALISE_HUMANA
    cliente_c_falso = cliente_factory(renda_mensal=3500.0, score_credito=550, possui_co_garantidor=False)
    assert avaliar_credito(cliente_c_falso)["status"] == "ANALISE_HUMANA"


# ==============================================================================
# Pares MC/DC para a condição D (renda_mensal > 3000 com garantidor)
# Mantém: C=True, A=False (renda não ativa rota padrão), B=False
# Varia: D
# ==============================================================================

def test_mcdc_condicao_D_renda_minima_garantidor_determina_resultado():
    """
    Prova que D (renda > 3000 com garantidor) tem impacto independente.
    Contexto: C=True. Mudar D de True→False muda APROVADO→ANALISE_HUMANA.
    """
    # C=True, D=True (renda 3500 > 3000) → APROVADO
    cliente_d_verdadeiro = cliente_factory(renda_mensal=3500.0, score_credito=550, possui_co_garantidor=True)
    assert avaliar_credito(cliente_d_verdadeiro)["status"] == "APROVADO"

    # C=True, D=False (renda 2500 < 3000) → garantidor não ativa, rota padrão não ativa
    # Score 550 > 400 → ANALISE_HUMANA
    cliente_d_falso = cliente_factory(renda_mensal=2500.0, score_credito=550, possui_co_garantidor=True)
    assert avaliar_credito(cliente_d_falso)["status"] == "ANALISE_HUMANA"


# ==============================================================================
# Tabela Verdade Completa (documentação dos 4 pares MC/DC)
# ==============================================================================

@pytest.mark.parametrize("renda, score, garantidor, status_esperado, descricao", [
    (5500, 650, False, "APROVADO",       "A=T, B=T → rota padrão ativa"),
    (4500, 650, False, "ANALISE_HUMANA", "A=F, B=T → rota padrão inativa"),
    (5500, 550, False, "ANALISE_HUMANA", "A=T, B=F → rota padrão inativa"),
    (3500, 550, True,  "APROVADO",       "C=T, D=T → rota garantidor ativa"),
    (2500, 550, True,  "ANALISE_HUMANA", "C=T, D=F → rota garantidor inativa"),
    (3500, 550, False, "ANALISE_HUMANA", "C=F, D=T → rota garantidor inativa"),
    (2000, 300, False, "RECUSADO",       "Nenhuma rota e score < 400"),
])
def test_tabela_verdade_completa(renda, score, garantidor, status_esperado, descricao):
    """Documenta todos os caminhos lógicos relevantes da decisão RN02."""
    cliente = cliente_factory(renda_mensal=renda, score_credito=score, possui_co_garantidor=garantidor)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado, (
        f"Falhou em: {descricao}. "
        f"Esperado: {status_esperado}, Obtido: {resultado['status']}"
    )
