
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
 
 
class ClienteSchema(BaseModel):
   
    model_config = ConfigDict(populate_by_name=True)
 
    nome: str = Field(..., min_length=2, description="Nome completo do proponente")
 
    idade: int = Field(..., ge=0, le=130, description="Idade do cliente em anos")
 
    renda_mensal: float = Field(..., ge=0, description="Renda mensal líquida em reais",
                                alias="rendaMensal")
 
    score_credito: int = Field(
        ..., ge=0, le=1000,
        description="Score de crédito de 0 a 1000",
        alias="scoreCredito"
    )
 
    possui_nome_sujo: bool = Field(
        ...,
        description="True se o cliente possui restrições cadastrais",
        alias="possuiNomeSujo"
    )
 
    possui_co_garantidor: bool = Field(
        ...,
        description="True se há um co-garantidor no contrato",
        alias="possuiCoGarantidor"
    )
 
    tipo_financiamento: str = Field(
        ...,
        description="IMOBILIARIO ou ESTUDANTIL",
        alias="tipoFinanciamento"
    )
 
 
class RespostaSchema(BaseModel):
    """
    Formato da resposta da API.
    """
    status_proposta: str = Field(..., description="APROVADO, ANALISE_HUMANA ou RECUSADO")
    taxa_juros_aplicada: Optional[float] = Field(
        None,
        description="Taxa em decimal. None se recusado."
    )
    motivo_decisao: str = Field(..., description="Explicação auditável da decisão")
    data_processamento: datetime = Field(..., description="Timestamp UTC do processamento")
 
 
class SimulacaoRegistradaSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    nome_proponente: str
    status_proposta: str
    taxa_juros_aplicada: Optional[float]
    motivo_decisao: str
    data_processamento: datetime

 # Schema de entrada para cadastro de usuário.
class UsuarioCreateSchema(BaseModel):
    nome: str = Field(..., min_length=2)
    email: str
    senha: str = Field(..., min_length=6)


# Schema de entrada para login de usuário.
class UsuarioLoginSchema(BaseModel):
    email: str
    senha: str


# Schema público de saída com dados do usuário.
class UsuarioPublicSchema(BaseModel):
    id: int
    nome: str
    email: str

    model_config = ConfigDict(from_attributes=True)


# Schema de resposta do login com token e usuário.
class UsuarioLoginResponseSchema(BaseModel):
    token: str
    usuario: UsuarioPublicSchema