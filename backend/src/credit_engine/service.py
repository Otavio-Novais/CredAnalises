
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from credit_engine.schemas import ClienteSchema, RespostaSchema
from credit_engine.repository import CreditRepository
from credit_engine import rules


# Janela de idempotência: 60 segundos (RNF02)
JANELA_IDEMPOTENCIA_SEGUNDOS = 60


class CreditService:
    """
    Serviço principal de análise de crédito.

    Recebe um repositório via construtor (Dependency Injection).
    Isso é o que permite trocar o repositório nos testes:
        service = CreditService(InMemoryCreditRepository())  # testes
        service = CreditService(SqlCreditRepository(db))    # produção
    """

    def __init__(self, repositorio: CreditRepository):
        self.repositorio = repositorio

    def avaliar_credito(self, cliente: ClienteSchema) -> RespostaSchema:
        """
        Caso de uso principal: avaliar uma proposta de crédito.
        Retorna sempre um RespostaSchema — seja do cache ou recém-calculado.
        """
        hash_req = self._gerar_hash(cliente)

        # --- Idempotência ---
        resultado_cacheado = self._verificar_idempotencia(hash_req)
        if resultado_cacheado:
            return resultado_cacheado

        # --- Processamento ---
        veredito = rules.avaliar_credito(cliente)

        taxa: Optional[float] = None
        if veredito["status"] in ("APROVADO", "ANALISE_HUMANA"):
            taxa = rules.calcular_taxa_juros(cliente)

        # --- Persistência ---
        registro = self.repositorio.salvar_simulacao(
            nome_proponente=cliente.nome,
            status_proposta=veredito["status"],
            taxa_juros_aplicada=taxa,
            motivo_decisao=veredito["motivo"],
            hash_requisicao=hash_req,
        )

        return RespostaSchema(
            status_proposta=veredito["status"],
            taxa_juros_aplicada=taxa,
            motivo_decisao=veredito["motivo"],
            data_processamento=registro.data_processamento,
        )

    def listar_historico(self, limite: int = 50) -> list:
        """Retorna as últimas N simulações para o endpoint de histórico."""
        return self.repositorio.listar_simulacoes(limite=limite)

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _gerar_hash(self, cliente: ClienteSchema) -> str:
        """
        Gera um hash MD5 determinístico dos campos relevantes.

        Por que MD5 aqui e não SHA256?
        Não é contexto de segurança criptográfica — é só um fingerprint
        para identificar requisições iguais. MD5 é suficiente e mais rápido.

        Os campos usados no hash devem ser TODOS os campos que determinam
        o resultado. Se mudar qualquer campo, o hash muda, e uma nova
        análise é feita.
        """
        dados = {
            "nome": cliente.nome,
            "idade": cliente.idade,
            "renda_mensal": cliente.renda_mensal,
            "score_credito": cliente.score_credito,
            "possui_nome_sujo": cliente.possui_nome_sujo,
            "possui_co_garantidor": cliente.possui_co_garantidor,
            "tipo_financiamento": cliente.tipo_financiamento,
        }
        payload = json.dumps(dados, sort_keys=True)
        return hashlib.md5(payload.encode()).hexdigest()

    def _verificar_idempotencia(self, hash_req: str) -> Optional[RespostaSchema]:
        """
        Verifica se existe um resultado recente para este hash.
        Se sim, retorna o RespostaSchema montado a partir do cache.
        Se não, retorna None (processamento normal deve ocorrer).
        """
        registro = self.repositorio.buscar_por_hash(hash_req)
        if registro is None:
            return None

        agora = datetime.now(timezone.utc)
        data_proc = registro.data_processamento

        # Garante que ambos os datetimes têm timezone para comparação
        if data_proc.tzinfo is None:
            data_proc = data_proc.replace(tzinfo=timezone.utc)

        diferenca = agora - data_proc
        if diferenca <= timedelta(seconds=JANELA_IDEMPOTENCIA_SEGUNDOS):
            return RespostaSchema(
                status_proposta=registro.status_proposta,
                taxa_juros_aplicada=registro.taxa_juros_aplicada,
                motivo_decisao=f"[CACHE] {registro.motivo_decisao}",
                data_processamento=registro.data_processamento,
            )

        return None
