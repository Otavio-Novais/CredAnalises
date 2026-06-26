
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from credit_engine.schemas import ClienteSchema, RespostaSchema, SimulacaoRegistradaSchema
from credit_engine.service import CreditService
from credit_engine.database import get_db, criar_tabelas, SqlCreditRepository



app = FastAPI(
    title="Credit Engine API",
    description=(
        "Motor de análise de crédito para os módulos Estudantil e estudantil da CrediTech. "
        "Avalia propostas com base em regras de negócio determinísticas."),
    version="0.1.0"
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, você pode trocar pelo link do seu frontend Heroku
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Cria as tabelas no banco ao iniciar a aplicação."""
    criar_tabelas()


def get_credit_service(db: Session = Depends(get_db)) -> CreditService:
    repo = SqlCreditRepository(db)
    return CreditService(repo)

@app.get("/")
def read_root():
    return {"message": "Credit Engine API está rodando!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}



@app.post(
    "/api/v1/credit/evaluate",
    response_model=RespostaSchema,
    summary="Avaliar proposta de crédito",
    description=(
        "Recebe os dados do proponente e retorna o veredito da análise de crédito. "
        "Requisições idênticas em menos de 60s retornam resultado cacheado (idempotência)."
    ),
)
def avaliar_credito(
    cliente: ClienteSchema,
    service: CreditService = Depends(get_credit_service),
):
    """
    RF01 — Processar Análise de Crédito
    RF02 — Calcular Taxa de Juros
    RF03 — Registrar Histórico
    RF04 — Registrar Logs de Caminho Lógico
    RNF02 — Idempotência
    """
    try:
        return service.avaliar_credito(cliente)
    except ValueError as e:
        # Erros de validação de regra de negócio (ex: tipo_financiamento inválido
        # que passou pelo Pydantic mas falhou na regra)
        raise HTTPException(status_code=422, detail=str(e))


@app.get(
    "/api/v1/history",
    response_model=list[SimulacaoRegistradaSchema],
    summary="Consultar histórico de simulações",
    description="RF05 — Retorna as últimas simulações para auditoria.",
)
def consultar_historico(
    limite: int = 50,
    service: CreditService = Depends(get_credit_service),
):
    registros = service.listar_historico(limite=limite)
    return [
        SimulacaoRegistradaSchema(
            id=r.id,
            nome_proponente=r.nome_proponente,
            status_proposta=r.status_proposta,
            taxa_juros_aplicada=r.taxa_juros_aplicada,
            motivo_decisao=r.motivo_decisao,
            data_processamento=r.data_processamento,
        )
        for r in registros
    ]
