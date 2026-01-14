import streamlit as st
import os, io, pandas as pd
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sentinela | Auditoria Fiscal",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO CSS AVANÇADO ---
st.markdown("""
<style>
    /* Esconder menus padrão */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    
    /* Fundo e Fonte */
    .stApp { background-color: #F0F2F6; }
    
    /* Sidebar Customizada */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 3px solid #FF6F00;
    }
    
    /* Títulos e Textos */
    h1 { color: #FF6F00 !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-weight: 800; }
    h3 { color: #444444 !important; font-size: 1.2rem; border-bottom: 2px solid #FF6F00; padding-bottom: 5px; }
    
    /* Botão Principal */
    .stButton > button {
        background: linear-gradient(90deg, #FF6F00 0%, #FF9100 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        font-weight: bold !important;
        width: 100% !important;
        height: 3.5rem !important;
        border: none !important;
        box-shadow: 0px 4px 15px rgba(255, 111, 0, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0px 6px 20px rgba(255, 111, 0, 0.5) !important;
    }

    /* Containers de Passo */
    .card {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Ajuste de File Uploader */
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
                df['CÓD'] = df['CÓD'].astype(int)
                return df
            except: continue
    return pd.DataFrame()

df_clientes = carregar_base_clientes()

# --- SIDEBAR ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    st.markdown("### 🛠️ Suporte Técnico")
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO_SENTINELA', index=False)
        return output.getvalue()
    st.download_button("📥 Baixar Gabarito NCM", criar_gabarito(), "gabarito_sentinela.xlsx", use_container_width=True)

# --- CORPO PRINCIPAL ---
st.markdown("<h1>SENTINELA <span style='color:#444'>| Auditoria Digital</span></h1>", unsafe_allow_html=True)

# PASSO 1 E 2 EM UMA LINHA (HEADER)
col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 👣 Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{int(l['CÓD'])} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Selecione o cliente para auditoria", [""] + opcoes)
    else:
        st.error("⚠️ Base de clientes não encontrada!")
        selecao = None
    st.markdown("</div>", unsafe_allow_html=True)

if selecao:
    cod_cliente = int(selecao.split(" - ")[0])
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### ⚖️ Passo 2: Configuração")
        regime = st.selectbox("Regime Tributário", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"])
        is_ret = st.toggle("Habilitar MG (RET)", help="Ativa a mesclagem das abas de base para clientes de MG")
        st.markdown("</div>", unsafe_allow_html=True)

    # RESUMO DA EMPRESA SELECIONADA
    st.success(f"📌 **Auditando:** {dados_empresa['RAZÃO SOCIAL']} | **CNPJ:** {cnpj_auditado}")

    # PASSO 3: UPLOAD EM CARDS
    st.markdown("### 📥 Passo 3: Central de Arquivos")
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📁 XMLs & ZIPs")
        xmls = st.file_uploader("Todas as Notas (Triagem Automática)", type=['zip', 'xml'], accept_multiple_files=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📥 Entradas (Terceiros)")
        ge = st.file_uploader("Relatório Gerencial", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge")
        ae = st.file_uploader("Lista de Autenticidade", type=['xlsx', 'csv'], accept_multiple_files=True, key="ae")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("#### 📤 Saídas (Próprias)")
        gs = st.file_uploader("Relatório Gerencial ", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs")
        as_f = st.file_uploader("Lista de Autenticidade ", type=['xlsx', 'csv'], accept_multiple_files=True, key="as")
        st.markdown("</div>", unsafe_allow_html=True)

    # BOTÃO DE AÇÃO
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([1, 1, 1])
    
    with col_btn:
        if st.button("🚀 INICIAR AUDITORIA"):
            if not xmls:
                st.warning("⚠️ Você precisa carregar os arquivos XML.")
            elif not regime:
                st.warning("⚠️ Selecione o regime tributário.")
            else:
                with st.spinner("🧡 O Sentinela está cruzando os dados..."):
                    try:
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        st.balloons()
                        st.success("🏁 Auditoria Finalizada com Sucesso!")
                        st.download_button("💾 BAIXAR RELATÓRIO EXCEL", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e:
                        st.error(f"❌ Erro no Processamento: {e}")
