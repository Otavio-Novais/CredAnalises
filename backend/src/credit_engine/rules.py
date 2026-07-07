from credit_engine.schemas import ClienteSchema
from credit_engine.constants import *

def avaliar_credito(cliente: ClienteSchema) -> str:
    # 1. Validações de Fronteira Críticas (Alvos ideais para BVA)
    
    if cliente.tipo_financiamento not in TIPOS_FINANCIAMENTO_VALIDOS:
        return {
            "status": "RECUSADO",
            "motivo": f"Tipo de financiamento inválido: '{cliente.tipo_financiamento}'. "
                      f"Valores aceitos: {TIPOS_FINANCIAMENTO_VALIDOS}."
        }

    if cliente.idade < IDADE_MINIMA or cliente.idade > IDADE_MAXIMA:
        return {
            "status": "RECUSADO",
            "motivo": f"Idade {cliente.idade} fora do intervalo permitido "
                      f"({IDADE_MINIMA}–{IDADE_MAXIMA} anos)."
        }

    if cliente.possui_nome_sujo:
        return {
            "status": "RECUSADO",
            "motivo": "Proponente possui restrição cadastral (nome sujo). "
                      "Análise bloqueada automaticamente."
        }

    # 2. Regra de Decisão Complexa (Alvo do critério MC/DC)
    # Expressão: (A E B) OU (C E D)
    # Onde:  A = Renda > 5000 | B = Score > 600 | C = Co-garantidor | D = Renda > 3000

    
    aprovacao_padrao = (
        cliente.renda_mensal > RENDA_MINIMA_APROVACAO
        and cliente.score_credito > SCORE_MINIMO_APROVACAO
    )

    aprovacao_com_garantidor = (
        cliente.possui_co_garantidor
        and cliente.renda_mensal > RENDA_MINIMA_COM_GARANTIDOR
    )

    if aprovacao_padrao or aprovacao_com_garantidor:
        return {
            "status": "APROVADO",
            "motivo": _motivo_aprovacao(cliente, aprovacao_padrao, aprovacao_com_garantidor)
        }
    # 3. Ramificação para Decision/Branch Coverage
    # Se não foi recusado pelas regras iniciais e não atingiu a pré-aprovação automática
    
    if cliente.score_credito > SCORE_MINIMO_ANALISE_HUMANA:
        return {
            "status": "ANALISE_HUMANA",
            "motivo": f"Proponente não atingiu critérios de aprovação automática, "
                      f"mas possui score {cliente.score_credito} (acima de {SCORE_MINIMO_ANALISE_HUMANA}). "
                      f"Encaminhado para análise de risco."
        }

    return {
        "status": "RECUSADO",
        "motivo": f"Score {cliente.score_credito} abaixo do mínimo para análise "
                  f"({SCORE_MINIMO_ANALISE_HUMANA}). Proposta recusada automaticamente."
    }

def calcular_taxa_juros(cliente: ClienteSchema) -> float:
    """
    Calcula a taxa de juros final utilizando um fluxo de dados incremental (Def-Clear).
    Mapeia o ciclo de vida da variável taxa_juros_base da definição ao uso.
    """
    if cliente.tipo_financiamento == "IMOBILIARIO":
        taxa = TAXA_BASE_IMOBILIARIO   # 10%
    else:
        taxa = TAXA_BASE_ESTUDANTIL    # 6%

    # USE: modificadores de score (RN04)
    # As faixas são mutuamente exclusivas — apenas um bloco executa.
    # Isso é importante para o teste de Fluxo de Dados: sem sobreposição.
    if cliente.score_credito >= SCORE_EXCELENTE_MIN:          # 801–1000
        taxa -= DESCONTO_SCORE_EXCELENTE                       # −1.5%

    elif cliente.score_credito >= SCORE_BOM_MIN:              # 601–800
        taxa -= DESCONTO_SCORE_BOM                             # −0.5%

    elif cliente.score_credito >= SCORE_REGULAR_MIN:          # 401–600
        taxa += ACRESCIMO_SCORE_REGULAR                        # +1.0%

    else:                                                      # 0–400
        taxa += ACRESCIMO_SCORE_BAIXO                          # +3.0%

    # USE FINAL: retorno arredondado para 4 casas (0.0850 = 8.50%)
    return round(taxa, 4)



def _motivo_aprovacao(cliente: ClienteSchema, padrao: bool, garantidor: bool) -> str:
    """Monta o texto de motivo para propostas aprovadas."""
    tipo = "Imobiliário" if cliente.tipo_financiamento == "IMOBILIARIO" else "Estudantil"

    if padrao and garantidor:
        return (f"Aprovado por critério padrão (renda R\$ {cliente.renda_mensal:,.2f} "
                f"e score {cliente.score_credito}) com co-garantidor adicional. "
                f"Modalidade: {tipo}.")
    elif padrao:
        return (f"Aprovado por critério padrão: renda R\$ {cliente.renda_mensal:,.2f} "
                f"(mínimo R\$ {RENDA_MINIMA_APROVACAO:,.2f}) e score {cliente.score_credito} "
                f"(mínimo {SCORE_MINIMO_APROVACAO}). Modalidade: {tipo}.")
    else:
        return (f"Aprovado com co-garantidor: renda R\$ {cliente.renda_mensal:,.2f} "
                f"(mínimo com garantidor R$ {RENDA_MINIMA_COM_GARANTIDOR:,.2f}). "
                f"Modalidade: {tipo}.")
