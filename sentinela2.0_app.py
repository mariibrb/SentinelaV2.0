import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela 2.0 | Auditoria Mágica", page_icon="🛡️", layout="wide")

# --- CSS: ESTÉTICA LÚDICA, MODERNA E FEMININA (Sem perder funcionalidade) ---
st.markdown("""
<style>
    /* Reset e Fundo Gradiente Místico */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d1b33 50%, #16213e 100%);
        color: #ffffff;
    }

    /* Sidebar Estilizada com Glassmorphism */
    [data-testid="stSidebar"] {
        background-color: rgba(20, 20, 35, 0.8) !important;
        border-right: 2px solid #ff4bb4;
        box-shadow: 5px 0 15px rgba(0,0,0,0.3);
    }

    /* Tipografia e Títulos */
    .titulo-container { 
        text-align: left; 
        padding: 20px 10px; 
        margin-bottom: 10px; 
    }
    .titulo-principal { 
        color: #ff4bb4; 
        font-family: 'Playfair Display', serif; 
        font-weight: 800; 
        font-size: 2.8rem;
        text-shadow: 0 0 10px rgba(255, 75, 180, 0.5);
    }
    .titulo-sub { 
        color: #a29bfe; 
        font-weight: 300; 
        font-size: 1.5rem; 
        letter-spacing: 2px;
    }

    .barra-magica {
        height: 3px;
        background: linear-gradient(to right, #ff4bb4, #a29bfe, transparent);
        margin: 10px 0 30px 0;
        border-radius: 10px;
    }

    /* Seções e Títulos de Passo */
    h3 { 
        color: #ff4bb4 !important; 
        font-size: 1.3rem !important; 
        margin-top: 20px !important;
        font-weight: 600 !important;
    }
    
    h4 { color: #a29bfe !important; font-size: 1rem !important; }

    /* Estilização dos Widgets (Inputs e Selects) */
    .stSelectbox div[data-baseweb="select"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 75, 180, 0.3) !important;
    }
    
    /* Toggle e Checkbox */
    .stCheckbox label p { color: #ffffff !important; font-weight: 500; }

    /* Dropzones de Upload (Estilo Gamer/Fantasia) */
    section[data-testid="stFileUploadDropzone"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 2px dashed #ff4bb4 !important;
        border-radius: 15px !important;
        padding: 20px !important;
        transition: 0.3s;
    }
    section[data-testid="stFileUploadDropzone"]:hover {
        background: rgba(255, 75, 180, 0.1) !important;
        border-color: #ffffff !important;
        transform: translateY(-2px);
    }

    /* Botão Principal com Glow */
    .stButton > button {
        background: linear-gradient(90deg, #ff4bb4 0%, #a29bfe 100%) !important;
        color: white !important;
        border-radius: 15px !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        height: 3.8rem !important;
        border: none !important;
        box-shadow: 0 0 20px rgba(255, 75, 180, 0.4) !important;
        transition: 0.4s !important;
    }
    .stButton > button:hover {
        box-shadow: 0 0 35px rgba(255, 75, 180, 0.7) !important;
        transform: scale(1.02) !important;
    }

    /* Status e Alertas */
    .status-container {
        padding: 15px;
        border-left: 5px solid #ff4bb4;
        background-color: rgba(162, 155, 254, 0.1);
        border-radius: 10px;
        margin: 20px 0;
        color: #ffffff;
    }
    
    .stSuccess, .stWarning, .stError {
        background-color: rgba(0, 0, 0, 0.2) !important;
        border-radius: 10px !important;
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

# --- SIDEBAR (COM O SEU SOLDADINHO) ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    
    st.markdown("<h3 style='text-align: center; color: #ff4bb4;'>Portal de Comando</h3>", unsafe_allow_html=True)
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO', index=False)
        return output.getvalue()
    
    st.download_button("✨ Baixar Gabarito Mestre", criar_gabarito(), "gabarito.xlsx", use_container_width=True)
    st.divider()

# --- CONTEÚDO PRINCIPAL ---
st.markdown(f"""
<div class='titulo-container'>
    <span class='titulo-principal'>SENTINELA</span> <span class='titulo-sub'>2.0</span>
    <div class='barra-magica'></div>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### 🏹 Passo 1: Identificar Alvo (Empresa)")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### 🔮 Passo 2: Configurações")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Ativar Magia MG (RET)")

    st.markdown(f"<div class='status-container'>📍 <b>Foco da Missão:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>ID:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub (Preservada)
    c1_status, c2_status = st.columns(2)
    with c1_status:
        if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
            st.success(f"💎 **Base de Impostos Conectada**")
        else:
            st.warning("🏮 **Base de Impostos não localizada**")
    
    with c2_status:
        if is_ret:
            if verificar_arquivo_github(f"RET/{cod_cliente}-RET_MG.xlsx"):
                st.success(f"💎 **Modelo RET Conectado**")
            else:
                st.warning(f"🏮 **Modelo RET não localizado**")

    st.markdown("### 📥 Passo 3: Central de Artefatos (Arquivos)")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("#### 📜 Fontes XML")
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
    _, col_btn, _ = st.columns([1, 1.5, 1])
    with col_btn:
        if st.button("🚀 INICIAR RITUAL DE ANÁLISE"):
            if xmls and regime:
                with st.spinner("Conjurando dados..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.download_button("💾 BAIXAR DIAGNÓSTICO FINAL", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: st.error(f"Ocorreu uma falha no feitiço: {e}")
            else:
                st.error("⚠️ Selecione o Regime e carregue os XMLs para começar.")

# Rodapé com Personalidade
st.markdown("<br><br><p style='text-align: center; color: #a29bfe; font-size: 0.8rem;'>Sentinela 2.0 • Created by Mari • 🛡️ Magic in Fiscal Analysis</p>", unsafe_allow_html=True)
