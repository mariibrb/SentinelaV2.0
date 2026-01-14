import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# Configuração da Página
st.set_page_config(page_title="Sentinela - Auditoria Fiscal", page_icon="🧡", layout="wide")

# Estilo CSS (Igual ao seu)
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

# --- CARREGAMENTO DA BASE DE CLIENTES ---
@st.cache_data
def carregar_base_clientes():
    # Carrega a planilha que você mandou (Coluna A: CÓD, B: RAZÃO SOCIAL, E: CNPJ)
    df = pd.read_csv('Clientes Ativos.xlsx - EMPRESAS.csv')
    return df

df_clientes = carregar_base_clientes()

with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)

# PASSO 1: Selecione a Empresa
st.markdown("<div class='passo-container'>👣 PASSO 1: Selecione a Empresa</div>", unsafe_allow_html=True)
opcoes_clientes = df_clientes.apply(lambda x: f"{x['CÓD']} - {x['RAZÃO SOCIAL']}", axis=1).tolist()
empresa_selecionada = st.selectbox("Empresa:", [""] + opcoes_clientes, label_visibility="collapsed")

if empresa_selecionada:
    cod_cliente = int(empresa_selecionada.split(" - ")[0])
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    st.info(f"Empresa: {dados_empresa['RAZÃO SOCIAL']} | CNPJ: {cnpj_auditado}")
    is_ret = st.toggle("Empresa utiliza RET (Minas Gerais)")

    # PASSO 2: Regime
    st.markdown("<div class='passo-container'>⚖️ PASSO 2: Defina o Regime Tributário</div>", unsafe_allow_html=True)
    regime = st.selectbox("Regime:", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional"], label_visibility="collapsed")

    if regime:
        # PASSO 3: Upload ÚNICO
        st.markdown("<div class='passo-container'>📥 PASSO 3: Upload dos Arquivos</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📁 XMLs (Tudo misturado)")
            xmls_misturados = st.file_uploader("Arraste todos os ZIPs e XMLs aqui", type=['zip', 'xml'], accept_multiple_files=True)
        
        with col2:
            st.subheader("📊 Gerenciais")
            ge = st.file_uploader("Gerenciais Entrada", type=['csv', 'xlsx'], accept_multiple_files=True)
            gs = st.file_uploader("Gerenciais Saída", type=['csv', 'xlsx'], accept_multiple_files=True)
            as_f = st.file_uploader("Autenticidade Saída", type=['xlsx', 'csv'], accept_multiple_files=True)

        st.markdown("---")
        if st.button("🚀 GERAR RELATÓRIO"):
            with st.spinner("🧡 Sentinela está separando e processando tudo..."):
                # O sistema separa sozinho entradas de saídas usando o CNPJ da planilha
                df_xe, df_xs = extrair_dados_xml_recursivo(xmls_misturados, cnpj_auditado)
                
                relat = gerar_excel_final(df_xe, df_xs, None, as_f, ge, gs, cod_cliente, regime, is_ret)
                
                st.success("Auditoria Concluída! 🧡")
                st.download_button("💾 BAIXAR RELATÓRIO", relat, f"Sentinela_{cod_cliente}.xlsx")
