import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml, gerar_excel_final

# 1. Configuração da Página
st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# 2. Estilo CSS Nascel
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    [data-testid="stVerticalBlock"] > div:first-child { margin-top: -20px; }
    [data-testid="stImage"] { text-align: center; margin-bottom: -20px; }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    if os.path.exists(".streamlit/nascel sem fundo.png"):
        st.image(".streamlit/nascel sem fundo.png", use_container_width=True)
    
    st.markdown("---")
    st.subheader("🏢 Identificação")
    cod_cliente = st.text_input("Código do Cliente (ex: 394)", key="cod_cli")

    st.subheader("🔄 Bases de Referência")
    st.info("O sistema buscará na pasta 'Bases_Tributárias' se o código for preenchido.")
    u_icms = st.file_uploader("Subir Base ICMS (Manual)", type=['xlsx'], key='base_icms_v3')
    u_ipi = st.file_uploader("Subir Base IPI (Manual)", type=['xlsx'], key='base_ipi_v3')
    u_pc = st.file_uploader("Subir Base PIS/COFINS (Manual)", type=['xlsx'], key='base_pc_v3')
    
    st.markdown("---")
    st.subheader("📥 Gabaritos (Padrão Mirão)")
    
    def criar_gabarito(colunas):
        buf = io.BytesIO()
        pd.DataFrame(columns=colunas).to_excel(buf, index=False)
        return buf.getvalue()

    # Gabaritos no formato exato da Tabela Mirão
    st.download_button("📥 Gabarito PIS/COFINS (Mirão)", criar_gabarito(["NCM", "DESCRIÇÃO", "CST_ENTRADA", "CST_SAIDA", "ALIQ_PIS", "ALIQ_COFINS", "NATUREZA_RECEITA"]), "gabarito_pis_cofins_mirao.xlsx", use_container_width=True)
    st.download_button("📥 Gabarito ICMS (Mirão)", criar_gabarito(["NCM", "DESCRIÇÃO", "CST_ICMS", "CFOP_PADRAO", "ALIQ_ICMS", "REDUCAO_BC", "MVA_ST"]), "gabarito_icms_mirao.xlsx", use_container_width=True)
    st.download_button("📥 Gabarito IPI (TIPI/Mirão)", criar_gabarito(["NCM", "DESCRIÇÃO", "CST_IPI", "ALIQ_IPI", "CENQ", "EX"]), "gabarito_ipi_mirao.xlsx", use_container_width=True)
    
    # Base Completa Mirão (Tudo em uma linha por NCM)
    st.download_button("📥 Gabarito Base Completa (Mirão)", criar_gabarito([
        "NCM", "DESCRIÇÃO", 
        "CST_ICMS", "ALIQ_ICMS", "REDUCAO_BC", "MVA_ST",
        "CST_IPI", "ALIQ_IPI", "CENQ", "EX",
        "CST_PIS_COFINS", "ALIQ_PIS", "ALIQ_COFINS", "NAT_RECEITA"
    ]), "gabarito_completo_mirao.xlsx", use_container_width=True)

# --- 4. TELA PRINCIPAL ---
c1, c2, c3 = st.columns([1.2, 1, 1.2]) 
with c2:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    else:
        st.title("🚀 SENTINELA")

st.markdown("---")
col_e, col_s = st.columns(2, gap="large")

with col_e:
    st.subheader("📥 FLUXO ENTRADAS")
    xe = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="xe_v3")
    ge = st.file_uploader("📊 Gerencial Entrada (CSV)", type=['csv'], key="ge_v3")
    ae = st.file_uploader("🔍 Autenticidade Entrada (XLSX)", type=['xlsx'], key="ae_v3")

with col_s:
    st.subheader("📤 FLUXO SAÍDAS")
    xs = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="xs_v3")
    gs = st.file_uploader("📊 Gerencial Saída (CSV)", type=['csv'], key="gs_v3")
    as_f = st.file_uploader("🔍 Autenticidade Saída (XLSX)", type=['xlsx'], key="as_v3")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    if not xe and not xs:
        st.warning("Por favor, suba ao menos um arquivo XML.")
    else:
        with st.spinner("🧡 O Sentinela está cruzando os dados..."):
            try:
                df_xe = extrair_dados_xml(xe)
                df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, u_icms, u_pc, ae, as_f, ge, gs, u_ipi, cod_cliente)
                st.success("Auditoria concluída com sucesso! 🧡")
                st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")
