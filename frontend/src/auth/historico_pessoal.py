"""
Tela de histórico pessoal do usuário logado.
=============================================

Este é o "consultar mais rápido" que foi pedido: o usuário logado
vê APENAS as simulações dele, sem misturar com as de outros.

Chama GET /api/v1/users/me/history com o token no header.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from auth import auth_api, auth_ui

TZ_BRASIL = ZoneInfo("America/Sao_Paulo")


def badge_status(status: str) -> str:
    return {"APROVADO": "✅", "ANALISE_HUMANA": "⏳", "RECUSADO": "❌"}.get(status, "❓")


def tela_meu_historico():
    """
    Renderiza o histórico pessoal do usuário logado.
    Só funciona se houver token na sessão.
    """
    st.title("📁 Minhas Simulações")

    usuario = auth_ui.get_usuario()
    st.caption(f"Histórico de análises de {usuario['nome']}")

    token = auth_ui.get_token()

    col_limite, col_refresh = st.columns([3, 1])
    with col_limite:
        limite = st.slider("Quantidade de registros", 5, 100, 20, key="hist_pessoal_limite")
    with col_refresh:
        st.write("")
        atualizar = st.button("🔄 Atualizar", use_container_width=True, key="hist_pessoal_refresh")

    # Carrega o histórico pessoal
    if atualizar or "meu_historico" not in st.session_state:
        with st.spinner("Carregando suas simulações..."):
            resultado = auth_api.buscar_meu_historico(token, limite=limite)
        if resultado["ok"]:
            st.session_state["meu_historico"] = resultado["dados"]
        else:
            st.error(resultado["erro"])
            return

    dados = st.session_state.get("meu_historico", [])

    if not dados:
        st.info("Você ainda não fez nenhuma simulação. Vá para a aba Simulação para começar.")
        return

    # Métricas resumidas
    total = len(dados)
    aprovados = sum(1 for d in dados if d["status_proposta"] == "APROVADO")
    analise = sum(1 for d in dados if d["status_proposta"] == "ANALISE_HUMANA")
    recusados = sum(1 for d in dados if d["status_proposta"] == "RECUSADO")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("✅ Aprovados", aprovados)
    c3.metric("⏳ Em Análise", analise)
    c4.metric("❌ Recusados", recusados)

    st.divider()

    # Tabela
    df = pd.DataFrame(dados)
    df["status"] = df["status_proposta"].apply(lambda s: f"{badge_status(s)} {s}")
    df["taxa_%"] = df["taxa_juros_aplicada"].apply(
        lambda t: f"{t*100:.2f}%" if t is not None else "—"
    )
    df["data"] = pd.to_datetime(
        df["data_processamento"], utc=True
    ).dt.tz_convert("America/Sao_Paulo").dt.strftime("%d/%m/%Y %H:%M")

    df_exibir = df[["id", "nome_proponente", "status", "taxa_%", "data"]].rename(columns={
        "id": "ID",
        "nome_proponente": "Proponente",
        "status": "Status",
        "taxa_%": "Taxa a.a.",
        "data": "Data",
    })

    st.dataframe(df_exibir, use_container_width=True, hide_index=True)
