
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime, timezone


class SimulacaoRecord:
   
    def __init__(
        self,
        id: int,
        nome_proponente: str,
        status_proposta: str,
        taxa_juros_aplicada: Optional[float],
        motivo_decisao: str,
        data_processamento: datetime,
        hash_requisicao: str,
    ):
        self.id = id
        self.nome_proponente = nome_proponente
        self.status_proposta = status_proposta
        self.taxa_juros_aplicada = taxa_juros_aplicada
        self.motivo_decisao = motivo_decisao
        self.data_processamento = data_processamento
        self.hash_requisicao = hash_requisicao


class CreditRepository(ABC):

    @abstractmethod
    def salvar_simulacao(
        self,
        nome_proponente: str,
        status_proposta: str,
        taxa_juros_aplicada: Optional[float],
        motivo_decisao: str,
        hash_requisicao: str,
    ) -> SimulacaoRecord:
        """Salva uma simulação e retorna o registro com ID gerado."""
        ...

    @abstractmethod
    def buscar_por_hash(self, hash_requisicao: str) -> Optional[SimulacaoRecord]:
        
        ...

    @abstractmethod
    def listar_simulacoes(self, limite: int = 50) -> list[SimulacaoRecord]:
        ...



class InMemoryCreditRepository(CreditRepository):

    def __init__(self):
        self._storage: list[SimulacaoRecord] = []
        self._next_id: int = 1

    def salvar_simulacao(
        self,
        nome_proponente: str,
        status_proposta: str,
        taxa_juros_aplicada: Optional[float],
        motivo_decisao: str,
        hash_requisicao: str,
    ) -> SimulacaoRecord:
        registro = SimulacaoRecord(
            id=self._next_id,
            nome_proponente=nome_proponente,
            status_proposta=status_proposta,
            taxa_juros_aplicada=taxa_juros_aplicada,
            motivo_decisao=motivo_decisao,
            data_processamento=datetime.now(timezone.utc),
            hash_requisicao=hash_requisicao,
        )
        self._storage.append(registro)
        self._next_id += 1
        return registro

    def buscar_por_hash(self, hash_requisicao: str) -> Optional[SimulacaoRecord]:
        for registro in reversed(self._storage):
            if registro.hash_requisicao == hash_requisicao:
                return registro
        return None

    def listar_simulacoes(self, limite: int = 50) -> list[SimulacaoRecord]:
        return list(reversed(self._storage))[:limite]
