from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi import Header

from credit_engine.schemas import ClienteSchema, RespostaSchema, SimulacaoRegistradaSchema
from credit_engine.service import CreditService
from credit_engine.database import get_db, criar_tabelas, SqlCreditRepository
from credit_engine.user_service import UserService
from credit_engine.repository import InMemoryUserRepository
from credit_engine.schemas import (
    UsuarioCreateSchema,
    UsuarioLoginSchema,
    UsuarioPublicSchema,
    UsuarioLoginResponseSchema,
)

# Cria a aplicação principal da API.
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
    allow_origins=[
        "https://credanalises-frontend.onrender.com",  # URL que o Render vai gerar
        "http://localhost:8501",  # Streamlit local
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Cria as tabelas no banco ao iniciar a aplicação."""
    criar_tabelas()

# Cria o repositório em memória para a feature de usuários.
user_repo = InMemoryUserRepository()

# Cria o serviço de usuários usando o repositório em memória.
user_service = UserService(user_repo)

# Retorna o serviço de crédito com repositório SQL.
def get_credit_service(db: Session = Depends(get_db)) -> CreditService:
    repo = SqlCreditRepository(db)
    return CreditService(repo)

# Retorna a instância do serviço de usuários.
def get_user_service() -> UserService:
    return user_service

# Recupera o usuário autenticado a partir do token enviado no header.
def get_current_user(
    authorization: str | None = Header(default=None),
    service: UserService = Depends(get_user_service),
):
    if authorization is None:
        raise HTTPException(status_code=401, detail="nao autenticado")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="token invalido")

    token = authorization.replace("Bearer ", "")
    usuario = service.buscar_usuario_por_token(token)

    if usuario is None:
        raise HTTPException(status_code=401, detail="nao autenticado")

    return usuario

# Recupera o usuário autenticado quando houver token, mas também aceita acesso anônimo.
def get_optional_current_user(
    authorization: str | None = Header(default=None),
    service: UserService = Depends(get_user_service),
):
    if authorization is None:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="token invalido")

    token = authorization.replace("Bearer ", "")
    usuario = service.buscar_usuario_por_token(token)

    if usuario is None:
        raise HTTPException(status_code=401, detail="nao autenticado")

    return usuario

@app.get("/")
def read_root():
    return {"message": "Credit Engine API está rodando!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Cadastra um novo usuário.
@app.post("/api/v1/users/register", response_model=UsuarioPublicSchema, status_code=201)
def register_user(
    payload: UsuarioCreateSchema,
    service: UserService = Depends(get_user_service),
):
    try:
        usuario = service.registrar_usuario(
            nome=payload.nome,
            email=payload.email,
            senha=payload.senha,
        )
        return usuario
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Realiza login e retorna token de acesso.
@app.post("/api/v1/users/login", response_model=UsuarioLoginResponseSchema)
def login_user(
    payload: UsuarioLoginSchema,
    service: UserService = Depends(get_user_service),
):
    try:
        return service.login(
            email=payload.email,
            senha=payload.senha,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

# Retorna os dados do usuário autenticado.
@app.get("/api/v1/users/me", response_model=UsuarioPublicSchema)
def me(usuario=Depends(get_current_user)):
    return usuario

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
    usuario=Depends(get_optional_current_user),
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
        if usuario is None:
            return service.avaliar_credito(cliente)
        return service.avaliar_credito(
            cliente,
            usuario_id=usuario.id,
        )
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

# Retorna o histórico de simulações do usuário autenticado.
@app.get(
    "/api/v1/users/me/history",
    response_model=list[SimulacaoRegistradaSchema],
    summary="Consultar histórico do usuário autenticado",
    description="Retorna apenas as simulações associadas ao usuário logado.",
)
def consultar_meu_historico(
    limite: int = 50,
    usuario=Depends(get_current_user),
    service: CreditService = Depends(get_credit_service),
):
    registros = service.listar_historico(limite=limite, usuario_id=usuario.id)
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