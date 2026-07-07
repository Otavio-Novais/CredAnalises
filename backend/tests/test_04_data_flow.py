import pytest
from tests.conftest import cliente_factory
from credit_engine.rules import calcular_taxa_juros
from credit_engine.constants import (
    TAXA_BASE_IMOBILIARIO, TAXA_BASE_ESTUDANTIL,
    DESCONTO_SCORE_EXCELENTE, DESCONTO_SCORE_BOM,
    ACRESCIMO_SCORE_REGULAR, ACRESCIMO_SCORE_BAIXO,
)


# ==============================================================================
# Caminhos Def-Use por faixa de score — Modalidade IMOBILIARIO
# ==============================================================================

def test_fluxo_taxa_base_imobiliario_score_excelente():
    """
    DEF → USE 1 (desconto excelente) → USE FINAL
    Score 900 → faixa Excelente → taxa = 10% - 1.5% = 8.5%
    """
    cliente = cliente_factory(score_credito=900, tipo_financiamento="IMOBILIARIO")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_IMOBILIARIO - DESCONTO_SCORE_EXCELENTE, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


def test_fluxo_taxa_base_imobiliario_score_bom():
    """
    DEF → USE 2 (desconto bom) → USE FINAL
    Score 700 → faixa Bom → taxa = 10% - 0.5% = 9.5%
    """
    cliente = cliente_factory(score_credito=700, tipo_financiamento="IMOBILIARIO")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_IMOBILIARIO - DESCONTO_SCORE_BOM, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


def test_fluxo_taxa_base_imobiliario_score_regular():
    """
    DEF → USE 3 (acréscimo regular) → USE FINAL
    Score 500 → faixa Regular → taxa = 10% + 1.0% = 11.0%
    """
    cliente = cliente_factory(score_credito=500, tipo_financiamento="IMOBILIARIO")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_IMOBILIARIO + ACRESCIMO_SCORE_REGULAR, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


def test_fluxo_taxa_base_imobiliario_score_baixo():
    """
    DEF → USE 4 (acréscimo baixo) → USE FINAL
    Score 200 → faixa Baixo → taxa = 10% + 3.0% = 13.0%
    """
    cliente = cliente_factory(score_credito=200, tipo_financiamento="IMOBILIARIO")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_IMOBILIARIO + ACRESCIMO_SCORE_BAIXO, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


# ==============================================================================
# Caminhos Def-Use — Modalidade ESTUDANTIL (taxa base diferente)
# ==============================================================================

def test_fluxo_taxa_base_estudantil_score_excelente():
    """
    DEF com taxa diferente → USE 1 → USE FINAL
    Score 900 + Estudantil → taxa = 6% - 1.5% = 4.5%
    Valida que a DEF correta foi usada (não a imobiliária).
    """
    cliente = cliente_factory(score_credito=900, tipo_financiamento="ESTUDANTIL")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_ESTUDANTIL - DESCONTO_SCORE_EXCELENTE, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


def test_fluxo_taxa_base_estudantil_score_baixo():
    """
    DEF Estudantil → USE 4 (pior modificador) → USE FINAL
    Score 200 + Estudantil → taxa = 6% + 3.0% = 9.0%
    """
    cliente = cliente_factory(score_credito=200, tipo_financiamento="ESTUDANTIL")
    taxa = calcular_taxa_juros(cliente)
    esperado = round(TAXA_BASE_ESTUDANTIL + ACRESCIMO_SCORE_BAIXO, 4)
    assert taxa == pytest.approx(esperado, abs=0.0001)


@pytest.mark.parametrize(
    "score,tipo,esperado",
    [
        (801, "IMOBILIARIO", round(TAXA_BASE_IMOBILIARIO - DESCONTO_SCORE_EXCELENTE, 4)),
        (601, "IMOBILIARIO", round(TAXA_BASE_IMOBILIARIO - DESCONTO_SCORE_BOM, 4)),
        (401, "IMOBILIARIO", round(TAXA_BASE_IMOBILIARIO + ACRESCIMO_SCORE_REGULAR, 4)),
        (400, "IMOBILIARIO", round(TAXA_BASE_IMOBILIARIO + ACRESCIMO_SCORE_BAIXO, 4)),
        (801, "ESTUDANTIL", round(TAXA_BASE_ESTUDANTIL - DESCONTO_SCORE_EXCELENTE, 4)),
        (601, "ESTUDANTIL", round(TAXA_BASE_ESTUDANTIL - DESCONTO_SCORE_BOM, 4)),
        (401, "ESTUDANTIL", round(TAXA_BASE_ESTUDANTIL + ACRESCIMO_SCORE_REGULAR, 4)),
        (400, "ESTUDANTIL", round(TAXA_BASE_ESTUDANTIL + ACRESCIMO_SCORE_BAIXO, 4)),
    ],
)
def test_fluxo_taxa_base_nas_fronteiras_exatas(score, tipo, esperado):
    cliente = cliente_factory(score_credito=score, tipo_financiamento=tipo)
    taxa = calcular_taxa_juros(cliente)
    assert taxa == pytest.approx(esperado, abs=0.0001)


# ==============================================================================
# Invariantes — garantias que SEMPRE devem se manter
# ==============================================================================

@pytest.mark.parametrize("score, tipo", [
    (900, "IMOBILIARIO"), (900, "ESTUDANTIL"),
    (700, "IMOBILIARIO"), (700, "ESTUDANTIL"),
    (500, "IMOBILIARIO"), (500, "ESTUDANTIL"),
    (200, "IMOBILIARIO"), (200, "ESTUDANTIL"),
])
def test_invariante_taxa_sempre_positiva(score, tipo):
    """
    Invariante crítica: a taxa NUNCA pode ser zero ou negativa.
    Mesmo com o maior desconto possível (score 1000, estudantil):
    6% - 1.5% = 4.5% — sempre positivo.
    """
    cliente = cliente_factory(score_credito=score, tipo_financiamento=tipo)
    taxa = calcular_taxa_juros(cliente)
    assert taxa > 0, f"Taxa negativa detectada: {taxa} para score={score}, tipo={tipo}"


def test_invariante_imobiliario_sempre_maior_estudantil():
    """
    Para o mesmo score, taxa imobiliária SEMPRE > taxa estudantil.
    Isso é garantido pelas taxas base (10% vs 6%) e modificadores idênticos.
    """
    for score in [900, 700, 500, 200]:
        cliente_imob = cliente_factory(score_credito=score, tipo_financiamento="IMOBILIARIO")
        cliente_estud = cliente_factory(score_credito=score, tipo_financiamento="ESTUDANTIL")
        taxa_imob = calcular_taxa_juros(cliente_imob)
        taxa_estud = calcular_taxa_juros(cliente_estud)
        assert taxa_imob > taxa_estud, (
            f"Score {score}: imobiliário ({taxa_imob}) deveria ser > estudantil ({taxa_estud})"
        )
