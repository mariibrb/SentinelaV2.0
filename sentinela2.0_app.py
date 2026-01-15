import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela | Auditoria Fiscal", page_icon="🛡️", layout="wide")

# --- CSS NÍVEL "GARIMPEIRO" (FRONT-END AVANÇADO) ---
st.markdown("""
<style>
    /* Importando fonte moderna */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');

    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    .stApp { 
        background-color: #F4F7F9; 
        font-family: 'Inter', sans-serif;
    }

    /* SIDEBAR ESTILO DARK/SOFT */
    [data-testid="stSidebar"] {
        background-color: #1E1E2D !important; /* Escuro sofisticado */
        border-right: None;
        box-shadow: 10px 0 30px rgba(0,0,0,0.1);
    }
    
    [data-testid="stSidebar"] * { color: #FFFFFF !important; }

    /* O BOTÃO MAGNÉTICO (SIDEBAR) */
    div[data-testid="stSidebar"] .stDownloadButton button {
        background: linear-gradient(135deg, #FF6F00 0%, #FF9100 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.8rem 1.5rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 111, 0, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1) !important;
        width: 100% !important;
        position: relative;
        overflow: hidden;
    }

    div[data-testid="stSidebar"] .stDownloadButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(255, 111, 0, 0.5) !important;
        filter: brightness(1.1);
    }

    div[data-testid="stSidebar"] .stDownloadButton button:active {
        transform: translateY(1px);
    }

    /* TÍTULOS COM GRADIENTE */
    .titulo-principal {
        background: -webkit-linear-gradient(#FF6F00, #FF9100);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        letter-spacing: -1px;
    }

    .titulo-sub { color: #A0AEC0; font-weight: 400; font-size: 1.2rem; }

    .barra-laranja {
        height: 4px;
        background: linear-gradient(90deg, #FF6F00, transparent);
        border-radius: 10px;
        margin-bottom: 30px;
        width: 100px;
    }

    /* CARDS DE UPLOAD (GLASSMORPHISM) */
    section[data-testid="stFileUploadDropzone"] {
        background: #FFFFFF !important;
        border: 2px dashed #E2E8F0 !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        transition: 0.3s;
    }

    section[data-testid="stFileUploadDropzone"]:hover {
        border-color: #FF6F00 !important;
        background: #FFFBF7 !important;
    }

    /* BOTÃO DE ANÁLISE (BOTÃO DE AÇÃO) */
    .stButton > button {
        background-color: #1E1E2D !important; /* Dark Mode Button */
        color: white !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 10px 20px rgba(30, 30, 45, 0.2) !important;
        transition: 0.3s;
    }

    .stButton > button:hover {
        background-color: #FF6F00 !important;
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(255, 111, 0, 0.3) !important;
    }

    /* CONTAINER DE STATUS */
    .status-container {
        background: white;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #FF6F00;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES (PRESERVADAS) ---
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

# --- SIDEBAR DESIGN ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO', index=False)
        return output.getvalue()
    
    # O botão que agora tem o estilo "Garimpeiro"
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "gabarito.xlsx", use_container_width=True)

# --- CONTEÚDO PRINCIPAL ---
st.markdown("""
<div class='titulo-container'>
    <div class='titulo-principal'>SENTINELA</div>
    <div class='titulo-sub'>Inteligência e Auditoria Fiscal</div>
    <div class='barra-laranja'></div>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1], gap="large")

with col_a:
    st.markdown("### 🔍 01. Seleção")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha a empresa", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### ⚙️ 02. Parâmetros")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")

    st.markdown(f"<div class='status-container'><b>Empresa:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
            st.success("✅ Bases Conectadas")
        else: st.warning("⚠️ Bases Ausentes")
    
    with c_status2: # Corrigindo variável se necessário
        if is_ret:
            if verificar_arquivo_github(f"RET/{cod_cliente}-RET_MG.xlsx"):
                st.success("✅ Modelo RET OK")
            else: st.warning("⚠️ RET Ausente")

    st.markdown("<br>### 📥 03. Central de Arquivos", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### 📄 Notas XML")
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
        if st.button("🚀 PROCESSAR AUDITORIA"):
            if xmls and regime:
                with st.spinner("Analisando dados..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.download_button("💾 BAIXAR RELATÓRIO", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: st.error(f"Erro: {e}")
