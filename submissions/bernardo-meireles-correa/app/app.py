"""Copiloto de Suporte: diagnóstico, triagem com IA e fila priorizada.

Rodar: streamlit run app/app.py
"""
import streamlit as st

st.set_page_config(page_title="Copiloto de Suporte", page_icon="🎧", layout="wide")
st.navigation([
    st.Page("views/diretor.py", title="Resposta ao diretor", default=True),
    st.Page("views/triagem.py", title="Triagem ao vivo"),
    st.Page("views/fila.py", title="Fila priorizada"),
    st.Page("views/evidencias.py", title="Evidências"),
    st.Page("views/retorno.py", title="ROI"),
    st.Page("views/revisao.py", title="Revisão humana"),
]).run()
