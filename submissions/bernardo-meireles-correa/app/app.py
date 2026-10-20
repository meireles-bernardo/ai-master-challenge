"""Copiloto de Suporte: painel da operação, triagem com IA, fila por risco e validação.

Rodar: streamlit run app/app.py
"""
import streamlit as st

st.set_page_config(page_title="Dossiê 002 · Protótipo", page_icon=":material/support_agent:", layout="wide")
page = st.navigation([
    st.Page("views/painel.py", title="Painel da operação", icon=":material/dashboard:", default=True),
    st.Page("views/triagem.py", title="Triagem de tickets", icon=":material/bolt:"),
    st.Page("views/fila.py", title="Fila", icon=":material/list:"),
    st.Page("views/validacao.py", title="Método", icon=":material/fact_check:"),
], position="hidden")
page.run()
