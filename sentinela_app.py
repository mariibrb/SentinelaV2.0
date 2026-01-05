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
    u_base_unica = st.file_uploader("Subir Base de Auditoria (XLSX)", type=['xlsx'], key='base_unica_v3')
    
    st.markdown("---")
    st.subheader("📥 Gabaritos")
    
    def criar_gabarito(colunas):
        buf = io.BytesIO()
        pd.DataFrame(columns=colunas).to_excel(buf, index=False)
        return buf.getvalue()

    # Estrutura A-P conforme sua explicação
    colunas_auditoria = [
        # ICMS (A-I)
        "NCM", "TEM_REDUCAO_ICMS", "CST_ICMS_ESPERADO", "ALIQ_ICMS_ESPERADA", "PERC_REDUCAO_ESPERADO", 
        "BASE_REDUZIDA_EST", "CST_EST", "ALIQ_ICMS_EST", "OP_INTERNA_CHECK",
        # IPI (J-M)
        "NCM_TIPI", "DESCRIÇÃO_TIPI", "ALIQ_IPI_TIPI", "EX_TIPI",
        # PIS e COFINS (N-P)
        "NCM_PC", "CST_PIS_COFINS_ENTRADA", "CST_PIS_COFINS_SAIDA"
    ]
    
    st.download_button("📥 Gabarito Base de Auditoria", criar_gabarito(colunas_auditoria), "base_auditoria_nascel.xlsx", use_container_width=True)

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
                # No motor, u_base_unica entra no lugar das bases separadas
                relat = gerar_excel_final(df_xe, df_xs, u_base_unica, ae, as_f, ge, gs, cod_cliente)
                st.success("Auditoria concluída com sucesso! 🧡")
                st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")
