import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml, gerar_excel_final

st.set_page_config(page_title="Sentinela Nascel", page_icon="🧡", layout="wide")

# CSS Nascel
st.markdown("""
<style>
    .stApp { background-color: #F7F7F7; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #FF6F00; }
    h1, h2, h3 { color: #FF6F00 !important; font-weight: 700; text-align: center; }
    .stButton>button { background-color: #FF6F00; color: white; border-radius: 20px; font-weight: bold; width: 100%; height: 50px; border: none; }
    .stFileUploader { border: 1px dashed #FF6F00; border-radius: 10px; }
    .block-container { padding-top: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists(".streamlit/nascel sem fundo.png"):
        st.image(".streamlit/nascel sem fundo.png", use_container_width=True)
    st.markdown("---")
    cod_cliente = st.text_input("Código do Cliente (ex: 394)")
    u_base_unica = st.file_uploader("Subir Base de Auditoria (XLSX)", type=['xlsx'])
    
    st.markdown("---")
    def criar_gabarito_nascel():
        output = io.BytesIO()
        colunas = [
            "NCM", "BASE REDUZIDA", "CST", "ALÍQUOTA ICMS", ".", 
            "BASE REDUZIDA2", "CST3", ",", "ALÍQUOTA ICMS5",    
            "NCM_TIPI", "EX", "DESCRIÇÃO", "ALÍQUOTA (%)",     
            "NCM_PC", "Entrada", "Saída", "CFOP-CST", "Status" 
        ]
        df = pd.DataFrame(columns=colunas)
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Base_Auditoria', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Base_Auditoria']
            f_lar_e = workbook.add_format({'bg_color': '#FF6F00', 'font_color': 'white', 'bold': True})
            f_lar_c = workbook.add_format({'bg_color': '#FFB74D', 'bold': True})
            f_cin_e = workbook.add_format({'bg_color': '#757575', 'font_color': 'white', 'bold': True})
            f_cin_c = workbook.add_format({'bg_color': '#E0E0E0', 'bold': True})
            for c, v in enumerate(colunas):
                if c <= 4: worksheet.write(0, c, v, f_lar_e)
                elif c <= 8: worksheet.write(0, c, v, f_lar_c)
                elif c <= 12: worksheet.write(0, c, v, f_cin_e)
                else: worksheet.write(0, c, v, f_cin_c)
        return output.getvalue()

    st.download_button("📥 Gabarito Base Nascel", criar_gabarito_nascel(), "base_auditoria_nascel.xlsx", use_container_width=True)

c1, c2, c3 = st.columns([1.2, 1, 1.2]) 
with c2:
    if os.path.exists(".streamlit/Sentinela.png"): st.image(".streamlit/Sentinela.png", use_container_width=True)

st.markdown("---")
col_e, col_s = st.columns(2, gap="large")
with col_e:
    st.subheader("📥 FLUXO ENTRADAS")
    xe = st.file_uploader("📂 XMLs de Entrada", type='xml', accept_multiple_files=True)
    ge = st.file_uploader("📊 Gerencial Entrada (CSV)", type=['csv'])
with col_s:
    st.subheader("📤 FLUXO SAÍDAS")
    xs = st.file_uploader("📂 XMLs de Saída", type='xml', accept_multiple_files=True)
    gs = st.file_uploader("📊 Gerencial Saída (CSV)", type=['csv'])

if st.button("🚀 EXECUTAR AUDITORIA COMPLETA", type="primary"):
    if not xe and not xs: st.warning("Suba ao menos um XML.")
    else:
        with st.spinner("🧡 Auditando..."):
            try:
                df_xe = extrair_dados_xml(xe); df_xs = extrair_dados_xml(xs)
                relat = gerar_excel_final(df_xe, df_xs, u_base_unica, ge, gs, cod_cliente)
                st.success("Concluído! 🧡")
                st.download_button("💾 BAIXAR RELATÓRIO", relat, "Auditoria_Sentinela.xlsx", use_container_width=True)
            except Exception as e: st.error(f"Erro: {e}")
