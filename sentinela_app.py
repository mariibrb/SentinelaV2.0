import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml, gerar_excel_final

# 1. Configuração da Página
st.set_page_config(page_title="Sentinela - Auditoria Fiscal", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# 2. Estilo CSS Sentinela (BOTÃO FULL WIDTH CORRIGIDO)
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }

    /* Centralização da Logo Sentinela na Sidebar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(img) {
        display: flex !important;
        justify-content: center !important;
        width: 100% !important;
    }

    /* FORÇAR BOTÃO A OCUPAR TODA A LARGURA INFERIOR */
    div.stButton {
        width: 100%;
        display: flex;
        justify-content: center;
    }
    
    div.stButton > button {
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        height: 60px !important;
        background-color: #FF6F00 !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        font-size: 1.3rem !important;
        margin-top: 30px !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(255, 111, 0, 0.3) !important;
        transition: 0.3s;
    }
    
    div.stButton > button:hover { 
        background-color: #E65100 !important; 
        box-shadow: 0 6px 20px rgba(255, 111, 0, 0.5) !important;
        transform: translateY(-2px);
    }
    
    /* Passos com Pesinhos Cinzas */
    .passo-container {
        background-color: #FFFFFF;
        padding: 10px 15px;
        border-radius: 10px;
        border-left: 5px solid #FF6F00;
        margin: 10px auto 15px auto;
        max-width: 600px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        text-align: center;
    }
    .passinho { color: #808080 !important; font-size: 1.2rem; margin-right: 10px; }
    .passo-texto { color: #FF6F00; font-size: 1.1rem; font-weight: 700; }

    .stFileUploader section { background-color: #FFFFFF; border: 1px dashed #FF6F00 !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

def listar_empresas_no_github():
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not repo: return []
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias"
    headers = {"Authorization": f"token {token}"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            arquivos = response.json()
            return sorted(list(set([f['name'].split('-')[0] for f in arquivos if f['name'].endswith('.xlsx')])))
    except: pass
    return []

# --- 3. SIDEBAR (Apenas Sentinela) ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    
    st.markdown("---")
    st.subheader("📥 Materiais de Apoio")
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            f_ncm = workbook.add_format({'bg_color': '#444444', 'font_color': 'white', 'bold': True, 'border': 1})
            f_lar_e = workbook.add_format({'bg_color': '#FF6F00', 'font_color': 'white', 'bold': True, 'border': 1})
            f_lar_c = workbook.add_format({'bg_color': '#FFB74D', 'bold': True, 'border': 1})
            f_cin_c = workbook.add_format({'bg_color': '#E0E0E0', 'bold': True, 'border': 1})
            
            cols_icms = ["NCM", "CST (INTERNA)", "ALIQ (INTERNA)", "CST (ESTADUAL)"]
            pd.DataFrame(columns=cols_icms).to_excel(writer, sheet_name='ICMS', index=False)
            for c, v in enumerate(cols_icms): writer.sheets['ICMS'].write(0, c, v, f_ncm if c == 0 else (f_lar_e if c <= 2 else f_lar_c))
            
            cols_pc = ["NCM", "CST Entrada", "CST Saída"]
            pd.DataFrame(columns=cols_pc).to_excel(writer, sheet_name='PIS_COFINS', index=False)
            for c, v in enumerate(cols_pc): writer.sheets['PIS_COFINS'].write(0, c, v, f_ncm if c == 0 else f_cin_c)
        return output.getvalue()

    st.download_button("📥 Baixar Gabarito de Base", criar_gabarito(), "gabarito_base.xlsx", use_container_width=True)
    st.markdown("---")
    st.subheader("🔄 Ferramentas")
    if st.file_uploader("Importar Base Complementar", type=['xlsx'], key='base_construcao'): 
        st.error("🚧 Recurso em desenvolvimento.")

# --- 4. TELA PRINCIPAL ---

# PASSO 1
st.markdown("<div class='passo-container'><span class='passinho'>👣</span><span class='passo-texto'>PASSO 1: Selecionar Empresa</span></div>", unsafe_allow_html=True)
col_c = st.columns([1, 1.5, 1])
with col_c[1]:
    cod_cliente = st.selectbox("Selecione o código do cliente:", [""] + listar_empresas_no_github(), label_visibility="collapsed")

if cod_cliente:
    # PASSO 2
    st.markdown("<div class='passo-container'><span class='passinho'>👣</span><span class='passo-texto'>PASSO 2: Carregar Documentos</span></div>", unsafe_allow_html=True)
    
    c_ent, c_sai = st.columns(2, gap="large")
    with c_ent:
        st.subheader("📥 ENTRADAS")
        xe = st.file_uploader("Notas Fiscais (XML)", type='xml', accept_multiple_files=True, key="xe_v29")
        ge = st.file_uploader("Relatório Gerencial (CSV)", type=['csv'], key="ge_v29")
        ae = st.file_uploader("Protocolos Autenticidade", type=['xlsx'], key="ae_v29")
    with c_sai:
        st.subheader("📤 SAÍDAS")
        xs = st.file_uploader("Notas Fiscais (XML)", type='xml', accept_multiple_files=True, key="xs_v29")
        gs = st.file_uploader("Relatório Gerencial (CSV)", type=['csv'], key="gs_v29")
        as_f = st.file_uploader("Protocolos Autenticidade", type=['xlsx'], key="as_v29")

    # BOTÃO LARGO (FULL WIDTH)
    if st.button("🚀 GERAR RELATÓRIO"):
        with st.spinner("🧡 O Sentinela está auditando os dados..."):
            try:
                df_xe = extrair_dados_xml(xe); df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, None, ae, as_f, ge, gs, cod_cliente)
                st.success("Auditoria finalizada com sucesso! 🧡")
                st.download_button("💾 BAIXAR AGORA", relat, f"Auditoria_{cod_cliente}.xlsx", use_container_width=True)
            except Exception as e: st.error(f"Erro no processamento: {e}")
