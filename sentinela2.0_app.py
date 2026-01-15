import streamlit as st
import os, io, pandas as pd
import requests
from style import aplicar_estilo_sentinela
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sentinela 2.0", page_icon="🧡", layout="wide")
aplicar_estilo_sentinela()

# --- LOGICA DE CLIENTES (PODE FICAR AQUI OU NO CORE) ---
@st.cache_data(ttl=600)
def carregar_base_clientes():
    caminhos = [".streamlit/Clientes Ativos.xlsx - EMPRESAS.csv", ".streamlit/Clientes Ativos.xlsx"]
    for caminho in caminhos:
        if os.path.exists(caminho):
            try:
                df = pd.read_csv(caminho) if caminho.endswith('.csv') else pd.read_excel(caminho)
                df = df.dropna(subset=['CÓD', 'RAZÃO SOCIAL'])
                df['CÓD'] = df['CÓD'].apply(lambda x: str(int(float(x))))
                return df
            except: continue
    return pd.DataFrame()

df_clientes = carregar_base_clientes()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<div class='titulo-sentinela'>🛡️ Sentinela</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER"]).to_excel(writer, index=False)
        return output.getvalue()
    
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "modelo.xlsx")

# --- CORPO PRINCIPAL ---
st.markdown("<div class='titulo-sentinela'>⛏️ Painel de Auditoria</div>", unsafe_allow_html=True)

if not df_clientes.empty:
    st.markdown("<div class='label-custom'>Selecione a Empresa:</div>", unsafe_allow_html=True)
    opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
    selecao = st.selectbox("Empresa", [""] + opcoes, label_visibility="collapsed")

    if selecao:
        cod_cliente = selecao.split(" - ")[0].strip()
        regime = st.selectbox("Regime Fiscal", ["Lucro Real", "Lucro Presumido", "Simples"])
        
        # Central de Arquivos
        xmls = st.file_uploader("Carregar XMLs", type=['zip', 'xml'], accept_multiple_files=True)
        
        if st.button("🚀 INICIAR OPERAÇÃO"):
            with st.spinner("Extraindo dados..."):
                # Aqui você chama o cérebro (sentinela_core)
                # df_xe, df_xs = extrair_dados_xml_recursivo(xmls, ...)
                # relat = gerar_excel_final(...)
                st.success("Operação finalizada!")
