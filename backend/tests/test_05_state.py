import pytest
from credit_engine.repository import InMemoryCreditRepository, SimulacaoRecord

def test_repository_fluxo_completo_e_100_coverage():
    """Testa todas as operações do repositório em memória para cravar 100%."""
    
    # 1. Instancia o repositório (Testa o __init__)
    repo = InMemoryCreditRepository()
    
    # 2. Testa o 'salvar_simulacao' e a criação da classe de dados SimulacaoRecord
    registro1 = repo.salvar_simulacao(
        nome_proponente="Renan Momo",
        status_proposta="APROVADO",
        taxa_juros_aplicada=4.5,
        motivo_decisao="Aprovado via critério padrão",
        hash_requisicao="hash_secreto_123"
    )
    
    assert registro1.id == 1
    assert registro1.nome_proponente == "Renan Momo"
    assert registro1.hash_requisicao == "hash_secreto_123"