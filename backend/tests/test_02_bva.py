"""
Para cada fronteira, testamos 3 pontos:
  (fronteira - 1), (fronteira), (fronteira + 1)

Fronteiras deste sistema:
  Idade: 18 (mínimo), 75 (máximo)
  Score: 0 (mínimo), 1000 (máximo)
  Score de aprovação: 600 (limiar de aprovação automática)
  Score de análise: 400 (limiar de análise humana)
"""

import pytest
from tests.conftest import cliente_factory
from credit_engine.rules import avaliar_credito, calcular_taxa_juros
from credit_engine.constants import (
    IDADE_MINIMA, IDADE_MAXIMA,
    SCORE_MINIMO, SCORE_MAXIMO,
    SCORE_MINIMO_APROVACAO,
    SCORE_MINIMO_ANALISE_HUMANA,
    SCORE_EXCELENTE_MIN, SCORE_BOM_MIN, SCORE_REGULAR_MIN,
    TAXA_BASE_IMOBILIARIO, TAXA_BASE_ESTUDANTIL,
    DESCONTO_SCORE_EXCELENTE, DESCONTO_SCORE_BOM,
    ACRESCIMO_SCORE_REGULAR, ACRESCIMO_SCORE_BAIXO,
)


# ==============================================================================
# 1. BVA — Fronteira de Idade
# ==============================================================================

@pytest.mark.parametrize("idade, status_esperado", [
    (IDADE_MINIMA - 1, "RECUSADO"),   # 17 — abaixo do mínimo
    (IDADE_MINIMA,     "APROVADO"),   # 18 — exatamente no mínimo
    (IDADE_MINIMA + 1, "APROVADO"),   # 19 — acima do mínimo
    (IDADE_MAXIMA - 1, "APROVADO"),   # 74 — abaixo do máximo
    (IDADE_MAXIMA,     "APROVADO"),   # 75 — exatamente no máximo
    (IDADE_MAXIMA + 1, "RECUSADO"),   # 76 — acima do máximo
])
def test_bva_fronteiras_idade(idade, status_esperado):
    """BVA nas fronteiras de elegibilidade por idade (RN01)."""
    cliente = cliente_factory(idade=idade)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado, (
        f"Idade {idade}: esperado '{status_esperado}', "
        f"obtido '{resultado['status']}'. Motivo: {resultado['motivo']}"
    )


# ==============================================================================
# 2. BVA — Fronteira de Score (validade do dado)
# ==============================================================================

@pytest.mark.parametrize("score, status_esperado", [
    # Score inválido é rejeitado pelo Pydantic (ge=0, le=1000)
    # Score 0 é válido mas cai em recusa de crédito (score muito baixo)
    (SCORE_MINIMO,     "RECUSADO"),       # 0 — mínimo válido, mas sem crédito
    (SCORE_MINIMO + 1, "RECUSADO"),       # 1 — ainda sem crédito
    (SCORE_MAXIMO - 1, "APROVADO"),       # 999 — quase máximo, aprovado
    (SCORE_MAXIMO,     "APROVADO"),       # 1000 — máximo, aprovado
])
def test_bva_fronteiras_score_validade(score, status_esperado):
    """BVA nos limites de validade do score (0 e 1000)."""
    cliente = cliente_factory(score_credito=score)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


# ==============================================================================
# 3. BVA — Fronteira de Aprovação (score 600)
# ==============================================================================

@pytest.mark.parametrize("score, status_esperado", [
    (SCORE_MINIMO_APROVACAO - 1, "ANALISE_HUMANA"),  # 599 — não aprova
    (SCORE_MINIMO_APROVACAO,     "ANALISE_HUMANA"),  # 600 — não aprova (> 600 é o critério)
    (SCORE_MINIMO_APROVACAO + 1, "APROVADO"),        # 601 — aprova
])
def test_bva_fronteira_score_aprovacao(score, status_esperado):
    """
    BVA na fronteira crítica de aprovação automática (RN02).
    O critério é score > 600, não >= 600.
    Portanto 600 NÃO aprova — este é um ponto frequente de bug.
    """
    cliente = cliente_factory(renda_mensal=6000.0, score_credito=score)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


# ==============================================================================
# 4. BVA — Fronteira de Análise Humana (score 400)
# ==============================================================================

@pytest.mark.parametrize("score, status_esperado", [
    (SCORE_MINIMO_ANALISE_HUMANA - 1, "RECUSADO"),       # 399 — recusado
    (SCORE_MINIMO_ANALISE_HUMANA,     "RECUSADO"),        # 400 — não entra em análise (> 400)
    (SCORE_MINIMO_ANALISE_HUMANA + 1, "ANALISE_HUMANA"), # 401 — análise humana
])
def test_bva_fronteira_analise_humana(score, status_esperado):
    """
    BVA na fronteira de análise humana (RN02).
    Critério: score > 400. Portanto 400 é RECUSADO, não ANALISE_HUMANA.
    """
    cliente = cliente_factory(renda_mensal=2000.0, score_credito=score)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


# ==============================================================================
# 5. BVA — Fronteiras de Modificadores de Taxa (calcular_taxa_juros)
# ==============================================================================

@pytest.mark.parametrize("score, taxa_base, modificador_esperado", [
    # Fronteira Score Excelente: 800 → Bom, 801 → Excelente
    (SCORE_EXCELENTE_MIN - 1, TAXA_BASE_IMOBILIARIO, -DESCONTO_SCORE_BOM),      # 800: Bom
    (SCORE_EXCELENTE_MIN,     TAXA_BASE_IMOBILIARIO, -DESCONTO_SCORE_EXCELENTE), # 801: Excelente
    # Fronteira Score Bom: 600 → Regular, 601 → Bom
    (SCORE_BOM_MIN - 1, TAXA_BASE_IMOBILIARIO, ACRESCIMO_SCORE_REGULAR),         # 600: Regular
    (SCORE_BOM_MIN,     TAXA_BASE_IMOBILIARIO, -DESCONTO_SCORE_BOM),             # 601: Bom
    # Fronteira Score Regular: 400 → Baixo, 401 → Regular
    (SCORE_REGULAR_MIN - 1, TAXA_BASE_IMOBILIARIO, ACRESCIMO_SCORE_BAIXO),       # 400: Baixo
    (SCORE_REGULAR_MIN,     TAXA_BASE_IMOBILIARIO, ACRESCIMO_SCORE_REGULAR),     # 401: Regular
])
def test_bva_fronteiras_modificadores_taxa(score, taxa_base, modificador_esperado):
    """
    BVA nas fronteiras dos modificadores de taxa (RN04).
    Verifica que cada faixa aplica o modificador correto.
    """
    cliente = cliente_factory(score_credito=score, tipo_financiamento="IMOBILIARIO")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(taxa_base + modificador_esperado, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001), (
        f"Score {score}: taxa esperada {esperado:.4f}, obtida {taxa:.4f}"
    )
