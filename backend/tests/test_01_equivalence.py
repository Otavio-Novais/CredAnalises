"""
Classes identificadas para este sistema:
  Idade: [< 18] [18–75] [> 75]
  Score: [< 0] [0–1000] [> 1000]
  Nome sujo: [True] [False]
  Renda: [> 5000] [3001–5000] [≤ 3000]
"""

import pytest
from tests.conftest import cliente_factory
from credit_engine.rules import avaliar_credito


# ==============================================================================
# 1. Caminho Feliz — Classe Válida Completa
# ==============================================================================

def test_caminho_feliz_aprovado():
    """
    Todas as variáveis na classe válida ótima.
    Garante que o motor aprova quando tudo está correto.
    """
    cliente = cliente_factory()  # defaults perfeitos
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == "APROVADO"


# ==============================================================================
# 2. Partições Inválidas — Uma variável inválida por vez
# ==============================================================================

@pytest.mark.parametrize("campo, valor, status_esperado", [
    # Classe inválida: idade abaixo do mínimo
    ("idade", 15, "RECUSADO"),
    # Classe inválida: idade acima do máximo
    ("idade", 80, "RECUSADO"),
    # Classe inválida: nome sujo
    ("possui_nome_sujo", True, "RECUSADO"),
    # Classe inválida: tipo de financiamento inexistente
    ("tipo_financiamento", "AUTOMOVEL", "RECUSADO"),
])
def test_particoes_invalidas_impeditivas(campo, valor, status_esperado):
    """
    Garante que cada classe impeditiva individualmente causa recusa.
    Padrão: só um campo inválido por vez — isolamento da causa.
    """
    cliente = cliente_factory(**{campo: valor})
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


@pytest.mark.parametrize("campo, valor, esperado", [
    (
        "idade",
        15,
        {
            "status": "RECUSADO",
            "motivo": "Idade 15 fora do intervalo permitido (18–75 anos).",
        },
    ),
    (
        "idade",
        80,
        {
            "status": "RECUSADO",
            "motivo": "Idade 80 fora do intervalo permitido (18–75 anos).",
        },
    ),
    (
        "possui_nome_sujo",
        True,
        {
            "status": "RECUSADO",
            "motivo": "Proponente possui restrição cadastral (nome sujo). Análise bloqueada automaticamente.",
        },
    ),
    (
        "tipo_financiamento",
        "AUTOMOVEL",
        {
            "status": "RECUSADO",
            "motivo_prefix": "Tipo de financiamento inválido: 'AUTOMOVEL'. Valores aceitos: ",
        },
    ),
])
def test_particoes_invalidas_retorno_exato(campo, valor, esperado):
    cliente = cliente_factory(**{campo: valor})
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == esperado["status"]
    if "motivo_prefix" in esperado:
        assert resultado["motivo"].startswith(esperado["motivo_prefix"])
        assert "IMOBILIARIO" in resultado["motivo"]
        assert "ESTUDANTIL" in resultado["motivo"]
    else:
        assert resultado["motivo"] == esperado["motivo"]


@pytest.mark.parametrize("renda, score, co_garantidor, status_esperado", [
    # Classe válida ótima: renda alta + score alto
    (6000.0, 700, False, "APROVADO"),
    # Classe limiar: renda suficiente + score baixo → análise humana
    (6000.0, 500, False, "ANALISE_HUMANA"),
    # Classe válida alternativa: co-garantidor + renda mínima
    (3500.0, 450, True, "APROVADO"),
    # Classe inválida de crédito: sem garantidor + renda baixa + score baixo
    (2000.0, 300, False, "RECUSADO"),
])
def test_classes_de_veredito(renda, score, co_garantidor, status_esperado):
    """
    Testa as classes que determinam o veredito de crédito (RN02).
    Cada linha representa uma classe de equivalência distinta.
    """
    cliente = cliente_factory(
        renda_mensal=renda,
        score_credito=score,
        possui_co_garantidor=co_garantidor,
    )
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


@pytest.mark.parametrize("renda, score, co_garantidor, esperado", [
    (
        6000.0,
        700,
        False,
        {
            "status": "APROVADO",
            "motivo": "Aprovado por critério padrão: renda R\\$ 6,000.00 (mínimo R\\$ 5,000.00) e score 700 (mínimo 600). Modalidade: Imobiliário.",
        },
    ),
    (
        3500.0,
        450,
        True,
        {
            "status": "APROVADO",
            "motivo": "Aprovado com co-garantidor: renda R\\$ 3,500.00 (mínimo com garantidor R$ 3,000.00). Modalidade: Imobiliário.",
        },
    ),
    (
        6000.0,
        500,
        False,
        {
            "status": "ANALISE_HUMANA",
            "motivo": "Proponente não atingiu critérios de aprovação automática, mas possui score 500 (acima de 400). Encaminhado para análise de risco.",
        },
    ),
    (
        2000.0,
        300,
        False,
        {
            "status": "RECUSADO",
            "motivo": "Score 300 abaixo do mínimo para análise (400). Proposta recusada automaticamente.",
        },
    ),
])
def test_classes_de_veredito_retorno_exato(renda, score, co_garantidor, esperado):
    cliente = cliente_factory(
        renda_mensal=renda,
        score_credito=score,
        possui_co_garantidor=co_garantidor,
    )
    assert avaliar_credito(cliente) == esperado


def test_classes_de_veredito_retorno_exato_estudantil():
    cliente = cliente_factory(
        renda_mensal=3500.0,
        score_credito=450,
        possui_co_garantidor=True,
        tipo_financiamento="ESTUDANTIL",
    )

    esperado = {
        "status": "APROVADO",
        "motivo": "Aprovado com co-garantidor: renda R\\$ 3,500.00 (mínimo com garantidor R$ 3,000.00). Modalidade: Estudantil.",
    }

    assert avaliar_credito(cliente) == esperado


@pytest.mark.parametrize("renda, score, co_garantidor, status_esperado", [
    (5000.0, 601, False, "ANALISE_HUMANA"),
    (3000.0, 550, True, "ANALISE_HUMANA"),
])
def test_classes_de_veredito_nas_fronteiras_críticas(renda, score, co_garantidor, status_esperado):
    cliente = cliente_factory(
        renda_mensal=renda,
        score_credito=score,
        possui_co_garantidor=co_garantidor,
    )
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == status_esperado


# ==============================================================================
# 3. Classes por Tipo de Financiamento
# ==============================================================================

@pytest.mark.parametrize("tipo", ["IMOBILIARIO", "ESTUDANTIL"])
def test_tipos_financiamento_validos(tipo):
    """Ambos os tipos válidos devem passar pela análise sem recusa por tipo."""
    cliente = cliente_factory(tipo_financiamento=tipo)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == "APROVADO"
