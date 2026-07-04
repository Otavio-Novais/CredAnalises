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
    assert registro1.status_proposta == "APROVADO"
    assert registro1.taxa_juros_aplicada == 4.5
    assert registro1.motivo_decisao == "Aprovado via critério padrão"
    assert registro1.hash_requisicao == "hash_secreto_123"

# Salva um segundo registro para testar o incremento do ID e listagem
    registro2 = repo.salvar_simulacao(
        nome_proponente="Otavio Padin",
        status_proposta="ANALISE_HUMANA",
        taxa_juros_aplicada=9.0,
        motivo_decisao="Score regular",
        hash_requisicao="hash_secreto_456"
    )
    
    assert registro2.id == 2
    assert registro2.status_proposta == "ANALISE_HUMANA"
    assert registro2.taxa_juros_aplicada == 9.0
    assert registro2.motivo_decisao == "Score regular"
    assert registro2.hash_requisicao == "hash_secreto_456"

# 3. Testa o 'buscar_por_hash' (Caminho Positivo)
    busca_sucesso = repo.buscar_por_hash("hash_secreto_123")
    assert busca_sucesso is not None
    assert busca_sucesso.nome_proponente == "Renan Momo"

    # 4. Testa o 'buscar_por_hash' (Caminho Negativo / Retorno None)
    busca_falha = repo.buscar_por_hash("hash_inexistente")
    assert busca_falha is None

    # 5. Testa o 'listar_simulacoes' (Garante ordem reversa e limite)
    lista_completa = repo.listar_simulacoes(limite=50)
    assert len(lista_completa) == 2
    # O mais recente deve vir primeiro devido ao reversed() no código original
    assert lista_completa[0].id == 2 
    
    # Testa o limite de paginação
    lista_com_limite = repo.listar_simulacoes(limite=1)
    assert len(lista_com_limite) == 1

    lista_padrao = repo.listar_simulacoes()
    assert len(lista_padrao) == 2


def test_repository_lista_padrao_limita_em_50_registros():
    repo = InMemoryCreditRepository()

    for indice in range(51):
        repo.salvar_simulacao(
            nome_proponente=f"Cliente {indice}",
            status_proposta="APROVADO",
            taxa_juros_aplicada=4.5,
            motivo_decisao=f"Registro {indice}",
            hash_requisicao=f"hash-{indice}",
        )

    lista_padrao = repo.listar_simulacoes()

    assert len(lista_padrao) == 50
    assert lista_padrao[0].id == 51
    assert lista_padrao[-1].id == 2