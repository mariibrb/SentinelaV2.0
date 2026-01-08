import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml, gerar_excel_final

# Configuração da Página - Visual Sentinela
st.set_page_config(page_title="Sentinela - Auditoria Fiscal", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# Estilo CSS Sentinela - Restaurado integralmente
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
    .passo-container {
        background-color: #FFFFFF; padding: 10px 15px; border-radius: 10px; border-left: 5px solid #FF6F00;
        margin: 10px auto 15px auto; max-width: 600px; text-align: center;
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
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST (INTERNA)", "ALIQ (INTERNA)", "CST (ESTADUAL)"]).to_excel(writer, sheet_name='ICMS', index=False)
            pd.DataFrame(columns=["NCM", "CST Entrada", "CST Saída"]).to_excel(writer, sheet_name='PIS_COFINS', index=False)
        return output.getvalue()
    st.download_button("📥 Baixar Gabarito", criar_gabarito(), "gabarito_sentinela.xlsx", use_container_width=True)

st.markdown("<div class='passo-container'>👣 PASSO 1: Selecione a Empresa</div>", unsafe_allow_html=True)
cod_cliente = st.selectbox("Empresa:", [""] + listar_empresas(), label_visibility="collapsed")

if cod_cliente:
    st.markdown("<div class='passo-container'>PASSO 2: Carregar ZIP e Planilhas</div>", unsafe_allow_html=True)
    c_e, c_s = st.columns(2, gap="large")
    with c_e:
        st.subheader("📥 ENTRADAS")
        xe = st.file_uploader("ZIP Entradas", type=['zip'], key="xe_v_master_8")
        ge = st.file_uploader("Gerencial Entrada", type=['csv', 'xlsx'], key="ge_v_master_8")
        ae = st.file_uploader("Autenticidade Entrada", type=['xlsx', 'csv'], key="ae_v_master_8")
    with c_s:
        st.subheader("📤 SAÍDAS")
        xs = st.file_uploader("ZIP Saídas", type=['zip'], key="xs_v_master_8")
        gs = st.file_uploader("Gerencial Saída", type=['csv', 'xlsx'], key="gs_v_master_8")
        as_f = st.file_uploader("Autenticidade Saída", type=['xlsx', 'csv'], key="as_v_master_8")

    if st.button("🚀 GERAR RELATÓRIO"):
        with st.spinner("🧡 Sentinela processando o motor maximalista..."):
            try:
                df_xe = extrair_dados_xml(xe); df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente)
                st.success("Auditoria Concluída! 🧡")
                st.download_button("💾 BAIXAR AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
            except Exception as e: st.error(f"Erro Crítico: {e}")
