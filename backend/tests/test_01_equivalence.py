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


# ==============================================================================
# 3. Classes por Tipo de Financiamento
# ==============================================================================

@pytest.mark.parametrize("tipo", ["IMOBILIARIO", "ESTUDANTIL"])
def test_tipos_financiamento_validos(tipo):
    """Ambos os tipos válidos devem passar pela análise sem recusa por tipo."""
    cliente = cliente_factory(tipo_financiamento=tipo)
    resultado = avaliar_credito(cliente)
    assert resultado["status"] == "APROVADO"
