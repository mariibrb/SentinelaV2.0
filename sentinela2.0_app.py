import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela | Auditoria Digital", page_icon="🛡️", layout="wide")

# --- CSS: ESTÉTICA SUAVE, MODERNA E ARREDONDADA ---
st.markdown("""
<style>
    /* Esconde elementos padrão */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* Fundo e Fonte Principal */
    .stApp { 
        background-color: #FDFBFB; 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Sidebar com borda suave e arredondada no topo */
    [data-testid="stSidebar"] { 
        background-color: #FFFFFF !important; 
        border-right: 1px solid #F3E5F5;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }

    /* Títulos e Identidade Visual */
    .titulo-container { text-align: left; padding-left: 10px; margin-bottom: 5px; }
    .titulo-principal { 
        color: #D81B60; /* Rosa mais sofisticado, não infantil */
        font-weight: 800; 
        font-size: 2.2rem; 
        letter-spacing: -1px;
    }
    .titulo-sub { color: #9E9E9E; font-weight: 300; font-size: 1.5rem; }

    .barra-estilizada {
        height: 3px;
        background: linear-gradient(to right, #D81B60, #F48FB1, transparent);
        border: none;
        margin: 5px 0 25px 0;
        border-radius: 50px;
        width: 100%;
    }

    /* Deixando tudo MUITO redondo */
    .stButton > button {
        background: linear-gradient(90deg, #D81B60 0%, #F48FB1 100%) !important;
        color: white !important;
        border-radius: 30px !important; /* Super arredondado */
        font-weight: bold !important;
        height: 3.5rem !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(216, 27, 96, 0.2) !important;
        transition: 0.3s !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(216, 27, 96, 0.3) !important;
    }

    /* Cards e Inputs Arredondados */
    [data-baseweb="select"], [data-testid="stFileUploadDropzone"], .status-container {
        border-radius: 20px !important;
        border: 1px solid #F1F1F1 !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
    }

    .status-container {
        padding: 15px;
        border-left: 6px solid #D81B60 !important;
        margin: 15px 0;
        color: #444;
    }

    /* Ajuste de Respiro e Espaçamento */
    h3 { 
        color: #555555 !important; 
        font-size: 1.1rem; 
        margin-top: 20px !important; 
        font-weight: 600 !important;
    }

    /* Remove excesso de quadrados do Streamlit */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: transparent !important;
        border: none !important;
    }
    
    /* Tooltip e Checkbox */
    .stTooltipIcon { color: #D81B60 !important; }
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

# --- CONTEÚDO PRINCIPAL ---
st.markdown(f"""
<div class='titulo-container'>
    <span class='titulo-principal'>SENTINELA</span> <span class='titulo-sub'>| Auditoria Digital</span>
    <div class='barra-estilizada'></div>
</div>
""", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### ✨ Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### ⚙️ Passo 2: Configuração")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")

    st.markdown(f"<div class='status-container'>📍 <b>Empresa ativa:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub
    c_status1, c_status2 = st.columns(2)
    with c_status1:
        if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
            st.success(f"✅ **Bases Localizadas**")
        else:
            st.warning("⚠️ **Bases não encontradas**")
    
    with c_status2:
        if is_ret:
            if verificar_arquivo_github(f"RET/{cod_cliente}-RET_MG.xlsx"):
                st.success(f"✅ **Modelo RET OK**")
            else:
                st.warning(f"⚠️ **RET não localizado**")

    st.markdown("### 📥 Passo 3: Central de Arquivos")
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
    _, col_btn, _ = st.columns([1, 1.2, 1])
    with col_btn:
        if st.button("🚀 INICIAR ANÁLISE"):
            if xmls and regime:
                with st.spinner("Analisando com precisão..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.download_button("💾 BAIXAR RELATÓRIO AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: st.error(f"Erro: {e}")
