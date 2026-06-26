"""
Constantes e parâmetros do motor de regras de crédito.
Centralizar esses valores facilita a manutenção e a criação 
de testes dinâmicos (como Análise de Valor Limite).
"""

# ==========================================
# LIMITES GERAIS (Foco: BVA e Particionamento)
# ==========================================
IDADE_MINIMA = 18
IDADE_MAXIMA = 75

SCORE_MINIMO = 0
SCORE_MAXIMO = 1000

# ==========================================
# REGRAS DE PRÉ-APROVAÇÃO (Foco: MC/DC)
# ==========================================
RENDA_MINIMA_APROVACAO = 5000.0
SCORE_MINIMO_APROVACAO = 600
RENDA_MINIMA_COM_GARANTIDOR = 3000.0
SCORE_MINIMO_ANALISE_HUMANA = 400
# ==========================================
# TAXAS E MODIFICADORES DE JUROS (Foco: Fluxo de Dados)
# ==========================================
TAXA_BASE_IMOBILIARIO = 0.10   # 10% ao ano
TAXA_BASE_ESTUDANTIL = 0.06   # 6% ao ano

TIPOS_FINANCIAMENTO_VALIDOS = {"IMOBILIARIO", "ESTUDANTIL"}
# ============================================================
# MODIFICADORES DE SCORE 
# ============================================================
SCORE_EXCELENTE_MIN = 801   # Score >= 801 é considerado Excelente
SCORE_BOM_MIN = 601         # Score entre 601 e 800 é Bom
SCORE_REGULAR_MIN = 401     # Score entre 401 e 600 é Regular
                            # Score entre 0 e 400 é Baixo

# Valores dos modificadores — usados para CÁLCULO
DESCONTO_SCORE_EXCELENTE = 0.015   # -1.5%
DESCONTO_SCORE_BOM = 0.005         # -0.5%
ACRESCIMO_SCORE_REGULAR = 0.010    # +1.0%
ACRESCIMO_SCORE_BAIXO = 0.030      # +3.0%
