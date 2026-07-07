"""
Telas de autenticação em Streamlit (login, cadastro, sessão).
==============================================================

Como o estado de login funciona no Streamlit:
-----------------------------------------------
O Streamlit reexecuta o script a cada interação. Para "lembrar" que o
usuário está logado, guardamos o token e os dados dele no st.session_state
— que persiste entre as reexecuções enquanto a aba estiver aberta.

    st.session_state["auth_token"]    → token do usuário logado (None se deslogado)
    st.session_state["auth_usuario"]  → dados do usuário {id, nome, email}

Fluxo:
  1. Usuário não logado → mostra telas de login/cadastro
  2. Login bem-sucedido → salva token no session_state
  3. Próximas execuções → detecta token → mostra app normal
  4. Logout → limpa o session_state
"""

import streamlit as st
from auth import auth_api


# ══════════════════════════════════════════════════════════════════
# GESTÃO DE ESTADO DA SESSÃO
# ══════════════════════════════════════════════════════════════════

def init_auth_state():
    """Inicializa as chaves de autenticação no session_state (uma vez)."""
    if "auth_token" not in st.session_state:
        st.session_state["auth_token"] = None
    if "auth_usuario" not in st.session_state:
        st.session_state["auth_usuario"] = None


def esta_logado() -> bool:
    """True se há um usuário logado na sessão."""
    return st.session_state.get("auth_token") is not None


def get_token() -> str | None:
    """Retorna o token do usuário logado (ou None)."""
    return st.session_state.get("auth_token")


def get_usuario() -> dict | None:
    """Retorna os dados do usuário logado (ou None)."""
    return st.session_state.get("auth_usuario")


def fazer_logout():
    """Limpa a sessão — desloga o usuário."""
    st.session_state["auth_token"] = None
    st.session_state["auth_usuario"] = None


# ══════════════════════════════════════════════════════════════════
# TELAS
# ══════════════════════════════════════════════════════════════════

def tela_login_cadastro():
    """
    Renderiza as abas de Login e Cadastro.
    Chamada quando o usuário NÃO está logado.

    Usa st.tabs para separar Login e Cadastro em duas abas.
    """
    st.title("🔐 Acesso ao CERASA")
    st.caption("Faça login para salvar e consultar suas simulações rapidamente.")

    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    # ── ABA LOGIN ─────────────────────────────────────────────────
    with aba_login:
        with st.form("form_login"):
            st.subheader("Entrar")
            email = st.text_input("Email", key="login_email", placeholder="voce@email.com")
            senha = st.text_input("Senha", key="login_senha", type="password")
            submit_login = st.form_submit_button("Entrar", use_container_width=True, type="primary")

        if submit_login:
            if not email or not senha:
                st.error("Preencha email e senha.")
            else:
                with st.spinner("Entrando..."):
                    resultado = auth_api.login(email, senha)

                if resultado["ok"]:
                    # Salva a sessão — o usuário agora está logado
                    st.session_state["auth_token"] = resultado["token"]
                    st.session_state["auth_usuario"] = resultado["usuario"]
                    st.success(f"Bem-vindo, {resultado['usuario']['nome']}!")
                    st.rerun()  # recarrega para mostrar o app logado
                else:
                    st.error(resultado["erro"])

    # ── ABA CADASTRO ──────────────────────────────────────────────
    with aba_cadastro:
        with st.form("form_cadastro"):
            st.subheader("Criar conta")
            nome = st.text_input("Nome", key="cad_nome", placeholder="Seu nome")
            email_cad = st.text_input("Email", key="cad_email", placeholder="voce@email.com")
            senha_cad = st.text_input(
                "Senha", key="cad_senha", type="password",
                help="Mínimo 6 caracteres",
            )
            senha_conf = st.text_input(
                "Confirmar senha", key="cad_senha_conf", type="password",
            )
            submit_cad = st.form_submit_button("Criar conta", use_container_width=True, type="primary")

        if submit_cad:
            # Validações no frontend antes de chamar a API
            if not nome or not email_cad or not senha_cad:
                st.error("Preencha todos os campos.")
            elif len(senha_cad) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif senha_cad != senha_conf:
                st.error("As senhas não coincidem.")
            else:
                with st.spinner("Criando conta..."):
                    resultado = auth_api.registrar(nome, email_cad, senha_cad)

                if resultado["ok"]:
                    st.success("Conta criada com sucesso! Agora faça login na aba 'Entrar'.")
                else:
                    st.error(resultado["erro"])


def widget_usuario_sidebar():
    """
    Widget que mostra o usuário logado na sidebar, com botão de logout.
    Chamado dentro da sidebar quando o usuário está logado.
    """
    usuario = get_usuario()
    if usuario:
        st.success(f"👤 {usuario['nome']}")
        st.caption(usuario["email"])
        if st.button("Sair", use_container_width=True):
            fazer_logout()
            st.rerun()
