import streamlit as st
import os, io, pandas as pd
import requests
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela | Auditoria Digital", page_icon="🛡️", layout="wide")

# --- INJECT CUSTOM CSS (Estética Lúdica, Suave e Acolhedora) ---
def inject_custom_css():
    st.markdown("""
    <style>
        /* Importando fontes elegantes */
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Quicksand:wght@300;400;500;600&display=swap');

        /* Reset e Fundo Pastel Suave */
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        
        .stApp {
            background-color: #FDFBF9; /* Creme muito suave */
            color: #5D5D5D;
            font-family: 'Quicksand', sans-serif;
        }

        /* Sidebar Elegante e Clara */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #F0E6EF;
            box-shadow: 2px 0 10px rgba(0,0,0,0.02);
        }

        /* Títulos com Serifa (Playfair) */
        .titulo-container { 
            text-align: left; 
            padding: 10px 0; 
            margin-bottom: 20px; 
        }
        .titulo-principal { 
            color: #D4A5A5; /* Rosa Antigo Pastel */
            font-family: 'Playfair Display', serif; 
            font-weight: 700; 
            font-size: 2.5rem;
        }
        .titulo-sub { 
            color: #B8C0FF; /* Lavanda Suave */
            font-weight: 300; 
            font-size: 1.4rem;
            font-family: 'Quicksand', sans-serif;
        }

        .barra-suave {
            height: 2px;
            background: linear-gradient(to right, #D4A5A5, #B8C0FF, transparent);
            margin: 10px 0 30px 0;
            width: 50%;
        }

        /* Cards e Containers com Bordas Arredondadas e Sombra Suave */
        div[data-testid="stVerticalBlock"] > div {
            border-radius: 20px;
        }

        /* Inputs e Selectboxes Arredondados */
        .stSelectbox div[data-baseweb="select"] {
            background-color: #FFFFFF !important;
            border-radius: 15px !important;
            border: 1px solid #F0E6EF !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        }

        /* Dropzones de Upload (Estética Clean) */
        section[data-testid="stFileUploadDropzone"] {
            background: #FFFFFF !important;
            border: 2px dashed #D4A5A5 !important;
            border-radius: 20px !important;
            padding: 30px !important;
            transition: all 0.3s ease;
        }
        section[data-testid="stFileUploadDropzone"]:hover {
            background: #FFF5F5 !important;
            transform: scale(1.01);
        }

        /* Botão com Bordas Arredondadas e Estilo Suave */
        .stButton > button {
            background: linear-gradient(135deg, #D4A5A5 0%, #E2BCBC 100%) !important;
            color: white !important;
            border-radius: 25px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            height: 3.5rem !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(212, 165, 165, 0.3) !important;
            padding: 0 30px !important;
        }
        .stButton > button:hover {
            box-shadow: 0 6px 20px rgba(212, 165, 165, 0.5) !important;
            transform: translateY(-2px);
        }

        /* Toggles Suaves */
        .stCheckbox label p { font-weight: 500; color: #7A7A7A !important; }

        /* Container de Status */
        .status-container {
            padding: 20px;
            border-radius: 15px;
            background-color: #F8F9FF; /* Lavanda clarinho */
            border: 1px solid #E0E7FF;
            margin: 20px 0;
            font-size: 0.95rem;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- FUNÇÕES (PRESERVADAS INTEGRALMENTE) ---
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

# --- SIDEBAR ELEGANTE ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    
    st.markdown("<div style='padding: 10px;'></div>", unsafe_allow_html=True)
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO', index=False)
        return output.getvalue()
    
    st.download_button("📖 Baixar Gabarito NCM", criar_gabarito(), "gabarito.xlsx", use_container_width=True)
    st.divider()

# --- CONTEÚDO PRINCIPAL ---
st.markdown(f"""
<div class='titulo-container'>
    <span class='titulo-principal'>Sentinela</span> <span class='titulo-sub'>| Auditoria Digital</span>
    <div class='barra-suave'></div>
</div>
""", unsafe_allow_html=True)

# Layout com espaçamento generoso
col_a, col_b = st.columns([2, 1], gap="large")

with col_a:
    st.markdown("### ☁️ Seleção de Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: selecao = None

if selecao:
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### 🌸 Configurações")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar RET MG")

    st.markdown(f"<div class='status-container'>✨ <b>Analisando agora:</b> {dados_empresa['RAZÃO SOCIAL']} <br> <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub
    st.markdown("#### 🔗 Conexão com Repositório")
    c1_stat, c2_stat = st.columns(2)
    with c1_stat:
        if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
            st.success(f"Base de Impostos OK")
        else:
            st.warning("Base não encontrada")
    
    with c2_stat:
        if is_ret:
            if verificar_arquivo_github(f"RET/{cod_cliente}-RET_MG.xlsx"):
                st.success(f"Modelo RET OK")
            else:
                st.warning(f"RET não encontrado")

    st.markdown("<br>### 📎 Central de Uploads", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="medium")
    
    with c1:
        st.markdown("#### 📂 Notas XML")
        xmls = st.file_uploader("Upload XML", type=['zip', 'xml'], accept_multiple_files=True, label_visibility="collapsed")

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
        if st.button("✨ INICIAR ANÁLISE"):
            if xmls and regime:
                with st.spinner("Organizando dados com carinho..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e: st.error(f"Poxa, algo deu errado: {e}")
            else:
                st.error("Por favor, selecione o regime e carregue os arquivos.")

# Rodapé Delicado
st.markdown("<br><br><p style='text-align: center; color: #D4A5A5; font-size: 0.9rem; font-style: italic;'>Feito com dedicação por Mari • Sentinela 2.0</p>", unsafe_allow_html=True)
