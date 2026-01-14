import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela | Auditoria Fiscal", page_icon="🧡", layout="wide")

# --- ESTILO CSS PREMIUM + BARRA FININHA LARANJA ---
st.markdown("""
<style>
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #F0F2F6; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 3px solid #FF6F00; }
    
    /* Título alinhado à esquerda com subtítulo cinza */
    .titulo-container { text-align: left; margin-bottom: 5px; padding-left: 10px; }
    .titulo-principal { color: #FF6F00; font-family: 'Segoe UI', sans-serif; font-weight: 800; font-size: 2.2rem; }
    .titulo-sub { color: #888888; font-weight: 300; font-size: 1.5rem; }

    /* A BARRA LARANJA FININHA (Como na imagem) */
    .barra-laranja {
        height: 2px;
        background: linear-gradient(to right, #FF6F00, #FF9100, transparent);
        border: none;
        margin: 5px 0 25px 0;
        width: 100%;
        border-radius: 10px;
    }

    /* Cards Brancos com Sombra */
    .card {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }

    /* Títulos de Passos Limpos */
    h3 { color: #444444 !important; font-size: 1.1rem; border: none !important; margin-bottom: 10px !important; }
    h4 { color: #FF6F00 !important; font-size: 1rem; margin-bottom: 10px; }

    /* Botão com Gradiente */
    .stButton > button {
        background: linear-gradient(90deg, #FF6F00 0%, #FF9100 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        height: 3.5rem !important;
        border: none !important;
        box-shadow: 0px 4px 10px rgba(255, 111, 0, 0.3) !important;
    }

    .status-container {
        padding: 15px;
        border-radius: 12px;
        border-left: 6px solid #FF6F00;
        background-color: #FFFFFF;
        margin-bottom: 20px;
    }

    /* Uploaders customizados */
    section[data-testid="stFileUploadDropzone"] {
        border: 2px dashed #FF6F00 !important;
        background-color: #FFF9F5 !important;
        border-radius: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DA BASE ---
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

def verificar_base_github(cod_cliente):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not repo: return False
    url = f"https://api.github.com/repos/{repo}/contents/Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    headers = {"Authorization": f"token {token}"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.status_code == 200
    except: return False

df_clientes = carregar_base_clientes()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO', index=False)
        return output.getvalue()
    st.download_button("📥 Baixar Gabarito NCM", criar_gabarito(), "gabarito.xlsx", use_container_width=True)

# --- CABEÇALHO ---
st.markdown("""
<div class='titulo-container'>
    <span class='titulo-principal'>SENTINELA</span> <span class='titulo-sub'>| Auditoria Digital</span>
    <div class='barra-laranja'></div>
</div>
""", unsafe_allow_html=True)

# SELEÇÃO E CONFIGURAÇÃO
col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 👣 Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha o cliente", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None
    st.markdown("</div>", unsafe_allow_html=True)

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### ⚖️ Passo 2: Configuração")
        regime = st.selectbox("Regime Tributário", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")
        st.markdown("</div>", unsafe_allow_html=True)

    # Status Bar
    st.markdown(f"<div class='status-container'>📍 <b>Auditando:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    if not verificar_base_github(cod_cliente):
        st.warning(f"⚠️ **Base de Impostos não encontrada:** A planilha será gerada, mas sem as análises correspondentes.")
    
    if is_ret and not os.path.exists(f"RET/{cod_cliente}-RET_MG.xlsx"):
        st.warning(f"⚠️ **Modelo RET não encontrado:** A planilha será gerada, mas sem as análises correspondentes.")

    # UPLOAD EM TRÊS COLUNAS
    st.markdown("### 📥 Passo 3: Central de Arquivos")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📄 XML")
        xmls = st.file_uploader("Upload", type=['zip', 'xml'], accept_multiple_files=True, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📥 Entradas")
        ge = st.file_uploader("Gerencial", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge")
        ae = st.file_uploader("Autenticidade", type=['xlsx', 'csv'], accept_multiple_files=True, key="ae")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📤 Saídas")
        gs = st.file_uploader("Gerencial ", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs")
        as_f = st.file_uploader("Autenticidade ", type=['xlsx', 'csv'], accept_multiple_files=True, key="as")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🚀 INICIAR AUDITORIA"):
            if xmls and regime:
                with st.spinner("Processando..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.download_button("💾 BAIXAR RELATÓRIO", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: st.error(f"Erro: {e}")
