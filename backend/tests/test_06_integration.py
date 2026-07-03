import pytest
import time
from datetime import datetime, timezone, timedelta
from credit_engine.service import CreditService
from credit_engine.repository import InMemoryCreditRepository
from credit_engine.schemas import ClienteSchema

def test_service_fluxo_completo_e_idempotencia():
    # 1. Configura as dependências reais em memória (Injeção de Dependência)
    repo = InMemoryCreditRepository()
    service = CreditService(repositorio=repo)
    
    # 2. Define o cliente padrão (Cenário de Aprovação -> Gera Taxa)
    cliente_aprovado = ClienteSchema(
        nome="Renan Momo",
        idade=30,
        renda_mensal=8000.0,
        score_credito=800,
        possui_nome_sujo=False,
        possui_co_garantidor=False,
        tipo_financiamento="IMOBILIARIO"
    )

# --- CENÁRIO 1: Primeiro Processamento (Fluxo Feliz com Taxa) ---
    resposta_1 = service.avaliar_credito(cliente_aprovado)
    assert resposta_1.status_proposta == "APROVADO"
    assert resposta_1.taxa_juros_aplicada is not None
    assert "[CACHE]" not in resposta_1.motivo_decisao
    
    # --- CENÁRIO 2: Idempotência Ativa (Mesmo cliente dentro da janela de 60s) ---
    resposta_2 = service.avaliar_credito(cliente_aprovado)
    assert resposta_2.status_proposta == "APROVADO"
    # Garante que passou pelo bloco de cache das linhas 115-120
    assert "[CACHE]" in resposta_2.motivo_decisao 
    assert resposta_2.taxa_juros_aplicada == resposta_1.taxa_juros_aplicada

    # --- CENÁRIO 3: Histórico de Simulações ---
    historico = service.listar_historico(limite=50)
    assert len(historico) == 1  # Apenas 1 foi salva de verdade, a outra veio do cache


def test_service_cliente_reprovado_sem_taxa():
    repo = InMemoryCreditRepository()
    service = CreditService(repositorio=repo)
    
    # Cliente que vai direto para REPROVADO (Não entra no cálculo de taxa da linha 46)
    cliente_reprovado = ClienteSchema(
        nome="Inimigo do Crédito",
        idade=25,
        renda_mensal=1000.0,
        score_credito=200,
        possui_nome_sujo=True,
        possui_co_garantidor=False,
        tipo_financiamento="VEICULO"
    )
    
    resposta = service.avaliar_credito(cliente_reprovado)
    assert resposta.status_proposta == "RECUSADO"
    assert resposta.taxa_juros_aplicada is None

def test_service_idempotencia_expirada(monkeypatch):
    repo = InMemoryCreditRepository()
    service = CreditService(repositorio=repo)
    
    cliente = ClienteSchema(
        nome="Otavio Padin",
        idade=28,
        renda_mensal=6000.0,
        score_credito=700,
        possui_nome_sujo=False,
        possui_co_garantidor=False,
        tipo_financiamento="VEICULO"
    )
    
    # Primeiro processamento normal
    service.avaliar_credito(cliente)
    
    # Força a simulação do tempo passando (avança o relógio em 61 segundos)
    # Isso simula o vencimento da constante JANELA_IDEMPOTENCIA_SEGUNDOS
    futuro = datetime.now(timezone.utc) + timedelta(seconds=61)
    
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            return futuro
            
    # Altera temporariamente o comportamento do datetime interno do Python
    monkeypatch.setattr("credit_engine.service.datetime", MockDatetime)
    
    # Executa novamente. Como passou de 60s, deve ignorar o cache e reprocessar (linha 122)
    resposta_expirada = service.avaliar_credito(cliente)
    assert "[CACHE]" not in resposta_expirada.motivo_decisao
    assert len(repo.listar_simulacoes()) == 2  # Salvou um novo registro

def test_service_idempotencia_com_data_sem_timezone():
    """Força o sistema a passar pela linha 110 para garantir 100% de cobertura."""
    repo = InMemoryCreditRepository()
    service = CreditService(repositorio=repo)
    
    # 1. Salva um registro diretamente no repositório com data SEM TIMEZONE (naive)
    registro_sem_tz = repo.salvar_simulacao(
        nome_proponente="Renan Momo",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.5,
        motivo_decisao="Aprovado",
        hash_requisicao="hash_teste_tz_123"
    )
    
    # Remove o timezone da data manualmente para simular um dado "sujo" no banco
    registro_sem_tz.data_processamento = registro_sem_tz.data_processamento.replace(tzinfo=None)
    
    # 2. Cria o schema com o mesmo hash para acionar o cache de idempotência
    cliente = ClienteSchema(
        nome="Dante Alighieri",
        idade=30,
        renda_mensal=8000.0,
        score_credito=800,
        possui_nome_sujo=False,
        possui_co_garantidor=False,
        tipo_financiamento="IMOBILIARIO"
    )
    
    # Injeta o mesmo hash gerado para o teste bater no registro alterado
    # (O service vai gerar o hash interno, então garantimos que seja o mesmo do cliente)
    hash_real = service._gerar_hash(cliente)
    registro_sem_tz.hash_requisicao = hash_real

    # 3. Executa a avaliação. O service vai ler a data sem tz, entrar no IF da linha 110 e corrigir!
    resposta = service.avaliar_credito(cliente)
    
    assert "[CACHE]" in resposta.motivo_decisao