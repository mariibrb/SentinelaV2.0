import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela Nascel 🧡", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# Estilo Nascel
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    logo_path = ".streamlit/nascel sem fundo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    st.markdown("---")
    st.subheader("🔄 Bases de Referência")
    u_icms = st.file_uploader("Subir Base ICMS (XLSX)", type=['xlsx'], key='s_icms')
    u_pc = st.file_uploader("Subir Base PIS/COFINS (XLSX)", type=['xlsx'], key='s_pc')

# Tela Principal
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    soldado = ".streamlit/Sentinela.png"
    if os.path.exists(soldado):
        st.image(soldado, use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL 🧡")

st.markdown("---")

col_e, col_s = st.columns(2, gap="large")

with col_e:
    st.subheader("📥 FLUXO ENTRADAS")
    xe = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="xe")
    ge = st.file_uploader("📊 Gerencial Entrada (CSV)", type=['csv'], key="ge")
    ae = st.file_uploader("🔍 Autenticidade Entrada (XLSX)", type=['xlsx'], key="ae")

with col_s:
    st.subheader("📤 FLUXO SAÍDAS")
    xs = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="xs")
    gs = st.file_uploader("📊 Gerencial Saída (CSV)", type=['csv'], key="gs")
    as_f = st.file_uploader("🔍 Autenticidade Saída (XLSX)", type=['xlsx'], key="as")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 O Sentinela está processando tudo..."):
        try:
            df_xe = extrair_dados_xml(xe)
            df_xs = extrair_dados_xml(xs)
            relat = gerar_excel_final(df_xe, df_xs, u_icms, u_pc, ae, as_f, ge, gs)
            st.success("Auditoria concluída! 🧡")
            st.download_button("💾 BAIXAR RELATÓRIO", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
