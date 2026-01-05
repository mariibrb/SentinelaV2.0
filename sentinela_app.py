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
    u_base_unica = st.file_uploader("Subir Base de Auditoria (XLSX)", type=['xlsx'], key='base_unica_v4')
    
    st.markdown("---")
    st.subheader("📥 Gabaritos")
    
    def criar_gabarito_nascel():
        output = io.BytesIO()
        # Colunas exatamente como na imagem do usuário
        colunas = [
            "NCM", "BASE REDUZIDA", "CST", "ALÍQUOTA ICMS", ".", # Op Interna (Laranja Escuro)
            "BASE REDUZIDA2", "CST3", ",", "ALÍQUOTA ICMS5",    # Op Interestadual (Laranja Claro)
            "NCM_TIPI", "EX", "DESCRIÇÃO", "ALÍQUOTA (%)",     # IPI (Cinza Escuro)
            "NCM_PC", "Entrada", "Saída", "CFOP-CST", "Status" # PIS/COF (Cinza Claro)
        ]
        df = pd.DataFrame(columns=colunas)
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Base_Auditoria', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Base_Auditoria']
            
            # Formatos Nascel (Laranja e Cinza)
            fmt_laranja_esc = workbook.add_format({'bg_color': '#FF6F00', 'font_color': 'white', 'bold': True, 'border': 1})
            fmt_laranja_cla = workbook.add_format({'bg_color': '#FFB74D', 'bold': True, 'border': 1})
            fmt_cinza_esc = workbook.add_format({'bg_color': '#757575', 'font_color': 'white', 'bold': True, 'border': 1})
            fmt_cinza_cla = workbook.add_format({'bg_color': '#E0E0E0', 'bold': True, 'border': 1})

            for col_num, value in enumerate(colunas):
                if col_num <= 4: worksheet.write(0, col_num, value, fmt_laranja_esc)
                elif col_num <= 8: worksheet.write(0, col_num, value, fmt_laranja_cla)
                elif col_num <= 12: worksheet.write(0, col_num, value, fmt_cinza_esc)
                else: worksheet.write(0, col_num, value, fmt_cinza_cla)
        
        return output.getvalue()

    st.download_button("📥 Gabarito Base Nascel", criar_gabarito_nascel(), "base_auditoria_nascel.xlsx", use_container_width=True)

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
    xe = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True, key="xe_v4")
    ge = st.file_uploader("📊 Gerencial Entrada (CSV)", type=['csv'], key="ge_v4")

with col_s:
    st.subheader("📤 FLUXO SAÍDAS")
    xs = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True, key="xs_v4")
    gs = st.file_uploader("📊 Gerencial Saída (CSV)", type=['csv'], key="gs_v4")

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    if not xe and not xs:
        st.warning("Por favor, suba ao menos um arquivo XML.")
    else:
        with st.spinner("🧡 O Sentinela está cruzando os dados..."):
            try:
                df_xe = extrair_dados_xml(xe)
                df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, u_base_unica, ge, gs, cod_cliente)
                st.success("Auditoria concluída com sucesso! 🧡")
                st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
            except Exception as e:
                st.error(f"Erro: {e}")
