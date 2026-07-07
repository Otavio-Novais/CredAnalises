import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from credit_engine.schemas import ClienteSchema, RespostaSchema
from credit_engine.repository import CreditRepository
from credit_engine import rules


# Define a janela máxima para reaproveitar uma resposta cacheada.
JANELA_IDEMPOTENCIA_SEGUNDOS = 60


# Implementa os casos de uso da análise de crédito.
class CreditService:
    

    # Inicializa o serviço com o repositório de simulações.
    def __init__(self, repositorio: CreditRepository):
        self.repositorio = repositorio

    # Avalia uma proposta de crédito com usuário opcional.
    def avaliar_credito(self, cliente: ClienteSchema, usuario_id: Optional[int] = None) -> RespostaSchema:
        hash_req = self._gerar_hash(cliente, usuario_id=usuario_id)

        # Verifica se existe resultado recente equivalente para o mesmo escopo.
        resultado_cacheado = self._verificar_idempotencia(hash_req)
        if resultado_cacheado:
            return resultado_cacheado

        # Executa a regra principal de análise de crédito.
        veredito = rules.avaliar_credito(cliente)

        # Calcula a taxa apenas para propostas não recusadas.
        taxa: Optional[float] = None
        if veredito["status"] in ("APROVADO", "ANALISE_HUMANA"):
            taxa = rules.calcular_taxa_juros(cliente)

        # Persiste a simulação com vínculo opcional ao usuário.
        if usuario_id is None:
            registro = self.repositorio.salvar_simulacao(
                nome_proponente=cliente.nome,
                status_proposta=veredito["status"],
                taxa_juros_aplicada=taxa,
                motivo_decisao=veredito["motivo"],
                hash_requisicao=hash_req,
            )
        else:
            registro = self.repositorio.salvar_simulacao(
                nome_proponente=cliente.nome,
                status_proposta=veredito["status"],
                taxa_juros_aplicada=taxa,
                motivo_decisao=veredito["motivo"],
                hash_requisicao=hash_req,
                usuario_id=usuario_id,
            )

        return RespostaSchema(
            status_proposta=veredito["status"],
            taxa_juros_aplicada=taxa,
            motivo_decisao=veredito["motivo"],
            data_processamento=registro.data_processamento,
        )

    # Lista o histórico geral ou filtrado por usuário.
    def listar_historico(self, limite: int = 50, usuario_id: Optional[int] = None) -> list:
        if usuario_id is None:
            return self.repositorio.listar_simulacoes(limite=limite)
        return self.repositorio.listar_simulacoes_por_usuario(usuario_id=usuario_id, limite=limite)

    # Gera um hash determinístico para a requisição no escopo correto.
    def _gerar_hash(self, cliente: ClienteSchema, usuario_id: Optional[int] = None) -> str:
        dados = {
            "nome": cliente.nome,
            "idade": cliente.idade,
            "renda_mensal": cliente.renda_mensal,
            "score_credito": cliente.score_credito,
            "possui_nome_sujo": cliente.possui_nome_sujo,
            "possui_co_garantidor": cliente.possui_co_garantidor,
            "tipo_financiamento": cliente.tipo_financiamento,
        }

        if usuario_id is not None:
            dados["usuario_id"] = usuario_id

        payload = json.dumps(dados, sort_keys=True)
        return hashlib.md5(payload.encode()).hexdigest()

    # Verifica se existe uma resposta recente em cache para o hash.
    def _verificar_idempotencia(self, hash_req: str) -> Optional[RespostaSchema]:
        registro = self.repositorio.buscar_por_hash(hash_req)
        if registro is None:
            return None

        agora = datetime.now(timezone.utc)
        data_proc = registro.data_processamento

        # Garante timezone consistente para comparação.
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