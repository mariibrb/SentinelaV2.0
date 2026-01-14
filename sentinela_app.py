import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# Configuração da Página - Visual Sentinela
st.set_page_config(page_title="Sentinela - Auditoria Fiscal", page_icon="🧡", layout="wide", initial_sidebar_state="expanded")

# Estilo CSS Sentinela
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

# --- CARREGAMENTO DA BASE DE CLIENTES ATIVOS ---
@st.cache_data(ttl=600)
def carregar_base_clientes():
    # Tentamos os caminhos mais prováveis conforme o que você subiu
    caminhos_possiveis = [
        ".streamlit/Clientes Ativos.xlsx - EMPRESAS.csv",
        ".streamlit/Clientes Ativos.xlsx",
        "Clientes Ativos.xlsx - EMPRESAS.csv"
    ]
    
    for caminho in caminhos_possiveis:
        if os.path.exists(caminho):
            try:
                if caminho.endswith('.csv'):
                    return pd.read_csv(caminho)
                else:
                    return pd.read_excel(caminho)
            except Exception as e:
                continue
    
    st.error("Arquivo de Clientes não encontrado no GitHub. Verifique a pasta .streamlit")
    return pd.DataFrame()

df_clientes = carregar_base_clientes()

with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    st.markdown("---")
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO_SENTINELA', index=False)
        return output.getvalue()
    st.download_button("📥 Baixar Gabarito", criar_gabarito(), "gabarito_sentinela.xlsx", use_container_width=True)

# --- FLUXO DE PASSOS ---

# PASSO 1: Seleção da Empresa
st.markdown("<div class='passo-container'>👣 PASSO 1: Selecione a Empresa</div>", unsafe_allow_html=True)

if not df_clientes.empty:
    # Ajuste para garantir que as colunas existam (CÓD e RAZÃO SOCIAL)
    try:
        opcoes = df_clientes.apply(lambda x: f"{int(x['CÓD'])} - {x['RAZÃO SOCIAL']}", axis=1).tolist()
        selecao = st.selectbox("Empresa:", [""] + opcoes, label_visibility="collapsed")
    except Exception as e:
        st.error(f"Erro ao processar colunas da planilha: {e}")
        selecao = None
else:
    selecao = None

if selecao:
    cod_cliente = int(selecao.split(" - ")[0])
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    st.info(f"🧡 Auditando: {dados_empresa['RAZÃO SOCIAL']} | CNPJ: {cnpj_auditado}")
    is_ret = st.toggle("Empresa utiliza RET (Minas Gerais)")

    # PASSO 2: Regime Tributário
    st.markdown("<div class='passo-container'>⚖️ PASSO 2: Defina o Regime Tributário</div>", unsafe_allow_html=True)
    regime = st.selectbox("Regime:", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")

    if regime:
        # PASSO 3: Upload dos Arquivos
        st.markdown("<div class='passo-container'>📥 PASSO 3: Upload dos Arquivos</div>", unsafe_allow_html=True)
        c_xml, c_ger = st.columns(2, gap="large")
        
        with c_xml:
            st.subheader("📁 XMLs / ZIPs")
            xmls = st.file_uploader("Upload de todos os XMLs (Entradas e Saídas)", type=['zip', 'xml'], accept_multiple_files=True, key="xml_u")
        
        with c_ger:
            st.subheader("📊 GERENCIAIS")
            ge = st.file_uploader("Gerencial Entrada", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge_u")
            gs = st.file_uploader("Gerencial Saída", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs_u")
            as_f = st.file_uploader("Autenticidade Saída", type=['xlsx', 'csv'], accept_multiple_files=True, key="as_u")

        st.markdown("---")
        
        col_btn_2 = st.columns([1,2,1])[1]
        with col_btn_2:
            if st.button("🚀 GERAR RELATÓRIO"):
                if not xmls:
                    st.error("Por favor, carregue os arquivos XML/ZIP.")
                else:
                    with st.spinner("🧡 Sentinela está separando e processando tudo..."):
                        try:
                            df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                            relat = gerar_excel_final(df_xe, df_xs, None, as_f, ge, gs, cod_cliente, regime, is_ret)
                            st.success("Auditoria Concluída! 🧡")
                            st.download_button("💾 BAIXAR AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                        except Exception as e: 
                            st.error(f"Erro Crítico no Motor: {e}")
