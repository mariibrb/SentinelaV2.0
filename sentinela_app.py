import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela Nascel 🧡", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# CSS Nascel
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
</style>
""", unsafe_allow_html=True)

# Sidebar - Onde você sobe as Bases ICMS e PIS/COFINS
with st.sidebar:
    if os.path.exists(".streamlit/nascel sem fundo.png"):
        st.image(".streamlit/nascel sem fundo.png", use_container_width=True)
    st.markdown("---")
    st.subheader("🔄 Bases de Dados")
    up_icms = st.file_uploader("Subir Base ICMS", type=['xlsx'], key='base_icms_side')
    up_pc = st.file_uploader("Subir Base PIS/COFINS", type=['xlsx'], key='base_pc_side')
    st.markdown("---")
    st.subheader("📥 Gabaritos")
    m_buf = io.BytesIO()
    pd.DataFrame(columns=["NCM", "DESCRICAO", "ALIQUOTA_ICMS"]).to_excel(m_buf, index=False)
    st.download_button("Gabarito de Base", m_buf.getvalue(), "modelo_base.xlsx", use_container_width=True)

# Tela Principal
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    else:
        st.title("🚀 SENTINELA NASCEL 🧡")

st.markdown("---")
col_e, col_s = st.columns(2, gap="large")
with col_e:
    st.subheader("📥 ENTRADAS 🧡")
    xe = st.file_uploader("📂 XMLs Entrada", type='xml', accept_multiple_files=True, key="xe_m")
    ge = st.file_uploader("📊 Gerencial Entrada", type=['csv'], key="ge_m")
    ae = st.file_uploader("🔍 Autenticidade Entrada", type=['xlsx'], key="ae_m")

with col_s:
    st.subheader("📤 SAÍDAS 🧡")
    xs = st.file_uploader("📂 XMLs Saída", type='xml', accept_multiple_files=True, key="xs_m")
    gs = st.file_uploader("📊 Gerencial Saída", type=['csv'], key="gs_m")
    as_f = st.file_uploader("🔍 Autenticidade Saída", type=['xlsx'], key="as_m")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    with st.spinner("🧡 Cruzando XML com Bases Tributárias..."):
        try:
            df_xe = extrair_dados_xml(xe)
            df_xs = extrair_dados_xml(xs)
            
            # AGORA PASSAMOS AS BASES DA SIDEBAR PARA O MOTOR
            relat = gerar_excel_final(df_xe, df_xs, up_icms, up_pc, ae, as_f)
            
            st.success("Auditoria concluída com sucesso! 🧡")
            st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
        except Exception as e:
            st.error(f"Erro: {e}")
