import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela | Auditoria Fiscal", page_icon="🧡", layout="wide")

# --- CSS TOTALMENTE LIMPO E BOTÃO SIDEBAR ESTILIZADO ---
st.markdown("""
<style>
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #F0F2F6; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 3px solid #FF6F00; }
    
    /* Remove balões e barras brancas automáticas */
    [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stVerticalBlock"],
    [data-testid="stVerticalBlock"] > div,
    .stColumn > div,
    .element-container {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    .titulo-container { text-align: left; padding-left: 10px; margin-bottom: 5px; }
    .titulo-principal { color: #FF6F00; font-family: 'Segoe UI', sans-serif; font-weight: 800; font-size: 2.2rem; }
    .titulo-sub { color: #888888; font-weight: 300; font-size: 1.5rem; }

    .barra-laranja-fina {
        height: 2px;
        background: linear-gradient(to right, #FF6F00, #FF9100, transparent);
        border: none;
        margin: 5px 0 20px 0;
        width: 100%;
    }

    /* Estilização do Botão de Download no Sidebar */
    [data-testid="stSidebar"] .stButton > button {
        background: #ffffff !important;
        color: #FF6F00 !important;
        border: 2px solid #FF6F00 !important;
        border-radius: 20px !important;
        font-weight: 600 !important;
        height: 3rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 6px rgba(255, 111, 0, 0.1) !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: #FF6F00 !important;
        color: #ffffff !important;
        box-shadow: 0 6px 12px rgba(255, 111, 0, 0.2) !important;
        transform: translateY(-2px);
    }

    /* Botão Principal do Conteúdo (Iniciar Análise) */
    .stButton > button {
        background: linear-gradient(90deg, #FF6F00 0%, #FF9100 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        height: 3.5rem !important;
        border: none !important;
    }

    .status-container {
        padding: 12px;
        border-left: 5px solid #FF6F00;
        background-color: #E8EAEE;
        border-radius: 5px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
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

def verificar_arquivo_github(caminho_relativo):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not repo: return False
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_relativo}"
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
    
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "gabarito.xlsx", use_container_width=True)

# --- CONTEÚDO PRINCIPAL ---
st.markdown(f"""
<div class='titulo-container'>
    <span class='titulo-principal'>SENTINELA</span> <span class='titulo-sub'>| Análise Tributária</span>
    <div class='barra-laranja-fina'></div>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### 👣 Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### ⚖️ Passo 2: Configuração")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")

    st.markdown(f"<div class='status-container'>📍 <b>Empresa selecionada:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub
    if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
        st.success(f"✅ **Base de Impostos localizada com sucesso!**")
    else:
        st.warning("⚠️ **Base de Impostos não encontrada.**")
    
    if is_ret:
        if verificar_arquivo_github(f"RET/{cod_cliente}-RET_MG.xlsx"):
            st.success(f"✅ **Modelo RET localizado com sucesso!**")
        else:
            st.warning(f"⚠️ **Modelo RET não encontrado.**")

    st.markdown("### 📥 Passo 3: Central de Arquivos")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### 📄 XML")
        xmls = st.file_uploader("X", type=['zip', 'xml'], accept_multiple_files=True, label_visibility="collapsed")

    with c2:
        st.markdown("#### 📥 Entradas")
        ge = st.file_uploader("G", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge", label_visibility="collapsed")
        ae = st.file_uploader("A", type=['xlsx', 'csv'], accept_multiple_files=True, key="ae", label_visibility="collapsed")

    with c3:
        st.markdown("#### 📤 Saídas")
        gs = st.file_uploader("S", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs", label_visibility="collapsed")
        as_f = st.file_uploader("F", type=['xlsx', 'csv'], accept_multiple_files=True, key="as", label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🚀 INICIAR ANÁLISE"):
            if xmls and regime:
                with st.spinner("Processando..."):
                    try:
                        # Chamada das funções core do Sentinela
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        
                        st.balloons()
                        st.success("Análise concluída com sucesso!")
                        st.download_button("💾 BAIXAR RELATÓRIO AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: 
                        st.error(f"Erro durante o processamento: {e}")
            else:
                st.warning("Certifique-se de carregar os XMLs e selecionar o Regime.")
