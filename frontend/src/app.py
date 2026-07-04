import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ_BRAZIL = ZoneInfo("America/Sao_Paulo")
# ── Configuração global da página ────────────────────────────────
# Deve ser a PRIMEIRA chamada Streamlit do script — antes de qualquer st.*
st.set_page_config(
    page_title="CreditCalc Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── URL base da API ───────────────────────────────────────────────
# Em desenvolvimento: backend rodando localmente
API_URL = os.environ.get("API_URL", "http://localhost:8000")


# ══════════════════════════════════════════════════════════════════
# FUNÇÕES DE COMUNICAÇÃO COM A API
# ══════════════════════════════════════════════════════════════════

def chamar_api_avaliar(dados: dict) -> dict:
    """
    Chama POST /api/v1/credit/evaluate e retorna o resultado.

    Retorna um dict com:
        {"ok": True,  "dados": {...}}   → sucesso
        {"ok": False, "erro": "..."}    → falha de regra ou conexão

    Por que separar a chamada HTTP da lógica de exibição?
    Porque nos testes de integração você pode mockar esta função
    sem precisar de um servidor real. Também centraliza o tratamento
    de erros HTTP em um único lugar.
    """
    try:
        response = requests.post(
            f"{API_URL}/api/v1/credit/evaluate",
            json=dados,
            timeout=10,
        )
        if response.status_code == 200:
            return {"ok": True, "dados": response.json()}
        elif response.status_code == 422:
            # Erro de validação Pydantic — detalha quais campos falharam
            detalhes = response.json().get("detail", [])
            msgs = [f"Campo '{e.get('loc',['?'])[-1]}': {e.get('msg','')}" for e in detalhes]
            return {"ok": False, "erro": "Dados inválidos:\n" + "\n".join(msgs)}
        else:
            return {"ok": False, "erro": f"Erro {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "erro": (
                "Não foi possível conectar à API.\n"
                f"Verifique se o backend está rodando em {API_URL}\n"
                "Comando: uvicorn credit_engine.main:app --reload --app-dir src"
            )
        }
    except requests.exceptions.Timeout:
        return {"ok": False, "erro": "A API demorou demais para responder (timeout 10s)."}


def chamar_api_historico(limite: int = 50) -> dict:
    """Chama GET /api/v1/history e retorna a lista de simulações."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/history",
            params={"limite": limite},
            timeout=10,
        )
        if response.status_code == 200:
            return {"ok": True, "dados": response.json()}
        else:
            return {"ok": False, "erro": f"Erro {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "erro": "API offline."}


def checar_saude_api() -> bool:
    """Chama GET /health para verificar se o backend está rodando."""
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def exibir_resultado(resultado: dict):
    status = resultado.get("status_proposta", "")
    taxa   = resultado.get("taxa_juros_aplicada")
    motivo = resultado.get("motivo_decisao", "")
    data   = resultado.get("data_processamento", "")

    st.divider()
    st.subheader("📋 Resultado da Análise")

    # Card de status colorido
    if status == "APROVADO":
        st.success(f"✅  **{status}**")
    elif status == "ANALISE_HUMANA":
        st.warning(f"⏳  **{status}** — Encaminhado para análise manual")
    else:
        st.error(f"❌  **{status}**")

    # Métricas em colunas
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Status",
            value=status,
        )
    with col2:
        if taxa is not None:
            st.metric(
                label="Taxa de Juros Anual",
                value=f"{taxa * 100:.2f}%",
                help="Taxa calculada com base no score e tipo de financiamento",
            )
        else:
            st.metric(label="Taxa de Juros", value="N/A")

    with col3:
        if data:
            try:
                dt = datetime.fromisoformat(data.replace("Z", "+00:00"))
                st.metric(label="Processado em", value=dt.strftime("%d/%m/%Y %H:%M"))
            except Exception:
                st.metric(label="Processado em", value=data[:19])

    # Motivo auditável (RF04)
    st.info(f"**Motivo da decisão:** {motivo}")

    if motivo.startswith("[CACHE]"):
        st.caption(
            "🔄 *Resultado retornado do cache — requisição idêntica enviada nos últimos 60s.*"
        )


def badge_status(status: str) -> str:
    """Retorna emoji para colorir a tabela de histórico."""
    return {"APROVADO": "✅", "ANALISE_HUMANA": "⏳", "RECUSADO": "❌"}.get(status, "❓")



def pagina_simulacao():
    st.title("🏦 Análise de Crédito")
    st.caption("Preencha os dados do proponente para obter o veredito automático.")

    with st.form("form_credito", clear_on_submit=False):

        # ── Dados pessoais ────────────────────────────────────────
        st.subheader("Dados Pessoais")
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input(
                "Nome completo",
                placeholder="Ex: João da Silva",
                help="Mínimo 2 caracteres",
            )
            idade = st.number_input(
                "Idade",
                min_value=0, max_value=130,
                value=30,
                help="Elegível entre 18 e 75 anos (RN01)",
            )

        with col2:
            renda_mensal = st.number_input(
                "Renda Mensal (R$)",
                min_value=0.0,
                value=5500.0,
                step=500.0,
                format="%.2f",
                help="Renda líquida mensal do proponente",
            )
            score_credito = st.number_input(
                "Score de Crédito",
                min_value=0, max_value=1000,
                value=720,
                help="0 = Baixo risco de aprovação · 1000 = Excelente",
            )

        # ── Flags booleanas ───────────────────────────────────────
        st.subheader("Situação Cadastral")
        col3, col4 = st.columns(2)

        with col3:
            possui_nome_sujo = st.checkbox(
                "⚠️  Possui restrição cadastral (nome sujo)",
                value=False,
                help="Se marcado, a proposta é recusada automaticamente (RN01)",
            )

        with col4:
            possui_co_garantidor = st.checkbox(
                "🤝  Possui co-garantidor",
                value=False,
                help="Co-garantidor permite aprovação com renda a partir de R$ 3.000",
            )

        # ── Tipo de financiamento ─────────────────────────────────
        st.subheader("Tipo de Financiamento")
        tipo_financiamento = st.radio(
            "Modalidade",
            options=["IMOBILIARIO", "ESTUDANTIL"],
            format_func=lambda x: "🏠 Imobiliário (CasaTech) — taxa base 10% a.a."
                                  if x == "IMOBILIARIO"
                                  else "🎓 Estudantil (FiesTech) — taxa base 6% a.a.",
            horizontal=True,
        )

        # ── Botão de envio ────────────────────────────────────────
        submitted = st.form_submit_button(
            "🔍 Analisar Proposta",
            use_container_width=True,
            type="primary",
        )

    # ── Processamento após submit ─────────────────────────────────
    # Este bloco roda FORA do form, depois que o botão foi clicado.
    # O "if submitted" é True apenas no ciclo de execução imediatamente
    # após o clique — nas execuções seguintes volta a ser False.
    if submitted:
        if not nome or len(nome.strip()) < 2:
            st.error("⚠️ Nome deve ter pelo menos 2 caracteres.")
        else:
            # Monta o payload no formato camelCase do contrato da API
            payload = {
                "nome": nome.strip(),
                "idade": int(idade),
                "rendaMensal": float(renda_mensal),
                "scoreCredito": int(score_credito),
                "possuiNomeSujo": possui_nome_sujo,
                "possuiCoGarantidor": possui_co_garantidor,
                "tipoFinanciamento": tipo_financiamento,
            }

            with st.spinner("Consultando motor de crédito..."):
                resposta = chamar_api_avaliar(payload)

            if resposta["ok"]:
                # Salva no session_state para persistir ao navegar entre páginas
                st.session_state["ultimo_resultado"] = resposta["dados"]
                st.session_state["ultimo_payload"]   = payload
            else:
                st.error(resposta["erro"])

    # Exibe resultado salvo (persiste entre re-execuções)
    if "ultimo_resultado" in st.session_state:
        exibir_resultado(st.session_state["ultimo_resultado"])

        # Expander com o JSON bruto — útil para entender o contrato da API
        with st.expander("🔧 Ver JSON enviado e recebido"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption("**Request (enviado)**")
                st.json(st.session_state.get("ultimo_payload", {}))
            with col_b:
                st.caption("**Response (recebido)**")
                st.json(st.session_state["ultimo_resultado"])


def pagina_historico():
    st.title("📊 Histórico de Simulações")
    st.caption("Últimas análises processadas pelo motor de crédito (RF05).")

    col_limite, col_refresh = st.columns([3, 1])
    with col_limite:
        limite = st.slider("Quantidade de registros", 5, 100, 20)
    with col_refresh:
        st.write("")  # espaçamento
        atualizar = st.button("🔄 Atualizar", use_container_width=True)

    # Chama a API (sempre que a página carrega ou o botão é clicado)
    if atualizar or "historico_dados" not in st.session_state:
        with st.spinner("Carregando histórico..."):
            resposta = chamar_api_historico(limite=limite)
        if resposta["ok"]:
            st.session_state["historico_dados"] = resposta["dados"]
        else:
            st.error(resposta["erro"])
            return

    dados = st.session_state.get("historico_dados", [])

    if not dados:
        st.info("Nenhuma simulação encontrada. Faça uma análise na aba Simulação.")
        return

    # ── Métricas resumidas ────────────────────────────────────────
    total      = len(dados)
    aprovados  = sum(1 for d in dados if d["status_proposta"] == "APROVADO")
    analise    = sum(1 for d in dados if d["status_proposta"] == "ANALISE_HUMANA")
    recusados  = sum(1 for d in dados if d["status_proposta"] == "RECUSADO")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total",          total)
    c2.metric("✅ Aprovados",   aprovados)
    c3.metric("⏳ Em Análise",  analise)
    c4.metric("❌ Recusados",   recusados)

    st.divider()

    # ── Tabela interativa ─────────────────────────────────────────
    df = pd.DataFrame(dados)

    # Formata colunas para exibição
    df["status"] = df["status_proposta"].apply(
        lambda s: f"{badge_status(s)} {s}"
    )
    df["taxa_%"] = df["taxa_juros_aplicada"].apply(
        lambda t: f"{t*100:.2f}%" if t is not None else "—"
    )
    df["data"] = pd.to_datetime(df["data_processamento"]).dt.strftime("%d/%m/%Y %H:%M")

    # Seleciona e renomeia colunas para exibição
    df_exibir = df[["id","nome_proponente","status","taxa_%","data","motivo_decisao"]].rename(columns={
        "id":               "ID",
        "nome_proponente":  "Proponente",
        "status":           "Status",
        "taxa_%":           "Taxa a.a.",
        "data":             "Data",
        "motivo_decisao":   "Motivo",
    })

    st.dataframe(
        df_exibir,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Motivo": st.column_config.TextColumn(width="large"),
        }
    )

    # Expander com JSON bruto para debug/auditoria
    with st.expander("🔧 Ver dados brutos (JSON)"):
        st.json(dados)


def pagina_sobre():
    """
    Tela informativa: documenta as regras de negócio implementadas.
    Serve como referência rápida durante os testes.
    """
    st.title("📖 Regras de Negócio")
    st.caption("Documentação das regras implementadas no motor de crédito.")

    st.subheader("RN01 — Restrições Impeditivas")
    st.markdown("""
    A proposta é **recusada imediatamente** (antes de qualquer cálculo) se:
    - Idade **menor que 18** ou **maior que 75** anos
    - Proponente com **nome sujo** (restrição cadastral)
    """)

    st.subheader("RN02 — Política de Veredito")
    col1, col2, col3 = st.columns(3)
    col1.success("✅ **APROVADO**\nRenda > R$ 5.000 **E** Score > 600\n\n*OU*\n\nCo-garantidor **E** Renda > R$ 3.000")
    col2.warning("⏳ **ANÁLISE HUMANA**\nNão atingiu aprovação automática mas Score > 400")
    col3.error("❌ **RECUSADO**\nScore ≤ 400 ou condições impeditivas")

    st.subheader("RN03 — Taxas Base por Modalidade")
    c1, c2 = st.columns(2)
    c1.info("🏠 **Imobiliário (CasaTech)**\nTaxa base: **10,0% a.a.**")
    c2.info("🎓 **Estudantil (FiesTech)**\nTaxa base: **6,0% a.a.**")

    st.subheader("RN04 — Modificadores de Score")
    dados_taxa = {
        "Faixa":        ["Excelente (801–1000)", "Bom (601–800)", "Regular (401–600)", "Baixo (0–400)"],
        "Modificador":  ["−1,5%", "−0,5%", "+1,0%", "+3,0%"],
        "Ex. Imobiliário": ["8,5% a.a.", "9,5% a.a.", "11,0% a.a.", "13,0% a.a."],
        "Ex. Estudantil":  ["4,5% a.a.", "5,5% a.a.", "7,0% a.a.", "9,0% a.a."],
    }
    st.dataframe(pd.DataFrame(dados_taxa), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════
# NAVEGAÇÃO E LAYOUT PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def sidebar():
    """
    Painel lateral fixo com navegação e status da API.

    st.sidebar.* funciona igual aos componentes normais mas
    renderiza no painel lateral em vez do conteúdo principal.
    """
    with st.sidebar:
        st.title("CreditCalc")
        st.caption("Motor de Análise de Crédito")
        st.divider()

        # Status da API — checa o /health
        api_ok = checar_saude_api()
        if api_ok:
            st.success("🟢 API Online")
        else:
            st.error("🔴 API Offline")
            st.caption(f"Esperando em: `{API_URL}`")

        st.divider()

        # Navegação
        # st.radio como menu de navegação é o padrão mais simples no Streamlit.
        # Alternativa mais elaborada: st.navigation (Streamlit >= 1.31)
        pagina = st.radio(
            "Navegação",
            options=["🔍 Simulação", "📊 Histórico", "📖 Regras"],
            label_visibility="collapsed",
        )
    return pagina


def main():
    pagina = sidebar()

    if pagina == "🔍 Simulação":
        pagina_simulacao()
    elif pagina == "📊 Histórico":
        pagina_historico()
    elif pagina == "📖 Regras":
        pagina_sobre()



main()