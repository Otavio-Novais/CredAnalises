"""
O que vai aqui: 
O teste do "Caminho Feliz" (todas as variáveis válidas) e as partições inválidas isoladas.

Tática: Usar @pytest.mark.parametrize para injetar os diferentes dicionários de erro (idade negativa, renda negativa, etc.) 
garantindo que o sistema rejeita de forma controlada.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/credit_engine')))

import pytest
from src.credit_engine.rules import avaliar_credito
from src.credit_engine.schemas import ClienteSchema

# ==============================================================================
# 1. CAMINHO FELIZ (Classe de Equivalência Válida)
# ==============================================================================
def test_caminho_feliz_sucesso():
    """
    Testa a 'Regra de Ouro': Combina apenas entradas perfeitamente válidas.
    Idade entre 18 e 75, score positivo e alto, renda excelente, sem nome sujo.
    O resultado esperado é 'Aprovado'.
    """
    cliente_valido = ClienteSchema(
        idade=30,
        score=850,
        renda_mensal=6000.0,
        valor_imovel=300000.0,
        nome_sujo=False,
        co_garantidor=False,
        anos_trabalho=6
    )
    assert avaliar_credito(cliente_valido) == "Aprovado"


# ==============================================================================
# 2. PARTIÇÕES INVÁLIDAS ISOLADAS (Tática: Parametrizar Erros Controlados)
# ==============================================================================
# Mudamos apenas UM campo inválido por vez, mantendo o resto do cliente "perfeito"
# para garantir que o sistema recusa estritamente por causa daquela partição.
@pytest.mark.parametrize(
    "idade, score, renda_mensal, nome_sujo",
    [
        (15, 850, 6000.0, False),    # Idade inválida: abaixo do mínimo (18)
        (80, 850, 6000.0, False),    # Idade inválida: acima do máximo (75)
        (30, -5, 6000.0, False),     # Score inválido: abaixo do mínimo (0)
        (30, 1050, 6000.0, False),   # Score inválido: acima do máximo (1000)
        (30, 850, 6000.0, True),     # Nome Sujo: restrição crítica automática
    ]
)
def test_particoes_invalidas_isoladas(idade, score, renda_mensal, nome_sujo):
    """
    Garante que o sistema rejeita de forma controlada ("Recusado")
    quando uma única variável entra em uma classe de equivalência inválida.
    """
    cliente_teste = ClienteSchema(
        idade=idade,
        score=score,
        renda_mensal=renda_mensal,
        valor_imovel=300000.0,
        nome_sujo=nome_sujo,
        co_garantidor=False,
        anos_trabalho=6
    )
    
    assert avaliar_credito(cliente_teste) == "Recusado"