import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela - Auditoria Fiscal", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton > button {
        background-color: #FF6F00 !important; color: white !important; border-radius: 25px !important;
        font-weight: bold !important; width: 300px !important; height: 50px !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def listar_empresas():
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not repo: return []
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias"
    headers = {"Authorization": f"token {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            return sorted(list(set([f['name'].split('-')[0] for f in res.json() if f['name'].endswith('.xlsx') and 'TIPI' not in f['name'].upper()])))
    except: pass
    return []

with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    st.markdown("---")

st.markdown("### 🧡 SENTINELA - AUDITORIA 4.0")
cod_cliente = st.selectbox("Selecione a Empresa:", [""] + listar_empresas())

if cod_cliente:
    c_e, c_s = st.columns(2, gap="large")
    with c_e:
        st.subheader("📥 ENTRADAS")
        xe = st.file_uploader("ZIP Entradas", type=['zip'], key="xe_final")
        ge = st.file_uploader("Gerencial Entrada", type=['csv', 'xlsx'], key="ge_final")
        ae = st.file_uploader("Autenticidade Entrada", type=['xlsx', 'csv'], key="ae_final")
    with c_s:
        st.subheader("📤 SAÍDAS")
        xs = st.file_uploader("ZIP Saídas", type=['zip'], key="xs_final")
        gs = st.file_uploader("Gerencial Saída", type=['csv', 'xlsx'], key="gs_final")
        as_f = st.file_uploader("Autenticidade Saída", type=['xlsx', 'csv'], key="as_final")

    if st.button("🚀 GERAR AUDITORIA COMPLETA"):
        with st.spinner("🧡 Sentinela executando auditoria maximalista..."):
            try:
                df_xe = extrair_dados_xml(xe); df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente)
                st.success("Auditoria Concluída! 🧡")
                st.download_button("💾 BAIXAR AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
            except Exception as e: st.error(f"Erro Crítico: {e}")
