"""
app.py — Interface web do GoodWe ChargeOps Agent (Streamlit).

Uso:
    streamlit run src/app.py

A interface expõe o que a arquitetura da Sprint 3 trouxe de novo: o seletor de
modelo, o identificador de sessão e o painel que mostra, a cada turno, a
latência, os tokens, as ferramentas acionadas e os guardrails disparados.
"""

import uuid

import streamlit as st

from src.agent import AgenteChargeOps
from src.config import MODELO_ALTERNATIVO, MODELO_PRINCIPAL

st.set_page_config(page_title="GoodWe ChargeOps Agent", page_icon="🔌", layout="centered")

st.title("GoodWe ChargeOps Agent")
st.caption("EV Challenge 2026 — Sprint 3 · arquitetura de agentes com LangGraph")

# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Configuração")

    modelo = st.selectbox("Modelo", [MODELO_PRINCIPAL, MODELO_ALTERNATIVO])

    if "sessao_id" not in st.session_state:
        st.session_state.sessao_id = f"web_{uuid.uuid4().hex[:8]}"
    st.text_input("Sessão", value=st.session_state.sessao_id, disabled=True)

    if st.button("Nova sessão"):
        st.session_state.sessao_id = f"web_{uuid.uuid4().hex[:8]}"
        st.session_state.mensagens = []
        st.session_state.pop("agente", None)
        st.rerun()

    st.divider()
    st.header("Último turno")
    painel = st.empty()

    st.divider()
    st.caption(
        "A memória é mantida pelo checkpointer do LangGraph, indexada pelo id da "
        "sessão. Sessões diferentes não compartilham histórico."
    )

# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

if "agente" not in st.session_state or st.session_state.get("modelo_ativo") != modelo:
    try:
        st.session_state.agente = AgenteChargeOps(modelo=modelo)
        st.session_state.modelo_ativo = modelo
    except Exception as erro:  # noqa: BLE001
        st.error(f"Não foi possível iniciar o agente: {erro}")
        st.stop()

# ---------------------------------------------------------------------------
# Conversa
# ---------------------------------------------------------------------------

for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["papel"]):
        st.markdown(mensagem["texto"])

pergunta = st.chat_input("Pergunte sobre a operação dos carregadores do condomínio...")

if pergunta:
    st.session_state.mensagens.append({"papel": "user", "texto": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Processando..."):
            try:
                resultado = st.session_state.agente.responder(
                    pergunta, sessao_id=st.session_state.sessao_id
                )
            except Exception as erro:  # noqa: BLE001
                st.error(f"{type(erro).__name__}: {erro}")
                st.stop()

        st.markdown(resultado["texto"])

    st.session_state.mensagens.append({"papel": "assistant", "texto": resultado["texto"]})

    with painel.container():
        st.metric("Latência", f"{resultado['latencia_s']} s")
        st.metric("Tokens do turno", resultado["tokens_total"])
        st.caption(
            f"{resultado['tokens_entrada']} de entrada + "
            f"{resultado['tokens_saida']} de saída"
        )
        if resultado["ferramentas"]:
            st.success(f"Ferramenta: {', '.join(resultado['ferramentas'])}")
        if resultado["bloqueio_entrada"]:
            st.warning(f"Guardrail de entrada: {resultado['bloqueio_entrada']}")
        if resultado["evento_saida"]:
            st.warning(f"Guardrail de saída: {resultado['evento_saida']}")
