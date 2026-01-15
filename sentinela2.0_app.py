import streamlit as st
import os, io, pandas as pd
import requests
from style import aplicar_estilo_sentinela
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Sentinela 2.0", page_icon="🧡", layout="wide")
aplicar_estilo_sentinela()

# --- FUNÇÕES DE CARREGAMENTO ---
@st.cache_data(ttl=600)
def carregar_base_clientes():
    # Tenta carregar de múltiplos locais possíveis
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
    """Verifica se o arquivo existe no repositório privado do GitHub"""
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    if not token or not repo: 
        return False
    
    url = f"https://api.github.com/repos/{repo}/contents/{caminho_relativo}"
    headers = {"Authorization": f"token {token}"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.status_code == 200
    except: 
        return False

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
    
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "modelo_gabarito.xlsx", use_container_width=True)

# --- CONTEÚDO PRINCIPAL ---
st.markdown("<div class='titulo-principal'>SENTINELA | Análise Tributária</div><div class='barra-laranja'></div>", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### 👣 Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: 
        st.error("Erro ao carregar base de clientes local.")
        selecao = None

if selecao:
    # Extrai código e dados
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = dados_empresa['CNPJ']

    with col_b:
        st.markdown("### ⚖️ Passo 2: Configuração")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")

    st.markdown(f"<div class='status-container'>📍 <b>Empresa:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # --- VALIDAÇÃO DE ARQUIVOS NO GITHUB ---
    c_stat1, c_stat2 = st.columns(2)
    
    # Validação Base Tributária
    path_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    existe_base = verificar_arquivo_github(path_base)
    
    with c_stat1:
        if existe_base:
            st.success("✅ Base de Impostos Conectada")
        else:
            st.warning("⚠️ Base de Impostos não localizada")

    # Validação RET MG
    if is_ret:
        path_ret = f"RET/{cod_cliente}-RET_MG.xlsx"
        existe_ret = verificar_arquivo_github(path_ret)
        with c_stat2:
            if existe_ret:
                st.success("✅ Modelo RET localizado")
            else:
                st.warning("⚠️ Modelo RET não encontrado")

    st.markdown("### 📥 Passo 3: Central de Arquivos")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**Notas XML**")
        xmls = st.file_uploader("X", type=['zip', 'xml'], accept_multiple_files=True, label_visibility="collapsed")
    with c2:
        st.markdown("**Entradas G e A**")
        ge = st.file_uploader("G", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge", label_visibility="collapsed")
        ae = st.file_uploader("A", type=['xlsx', 'csv'], accept_multiple_files=True, key="ae", label_visibility="collapsed")
    with c3:
        st.markdown("**Saídas S e F**")
        gs = st.file_uploader("S", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs", label_visibility="collapsed")
        as_f = st.file_uploader("F", type=['xlsx', 'csv'], accept_multiple_files=True, key="as", label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🚀 INICIAR ANÁLISE"):
            if not regime:
                st.error("Selecione o Regime Fiscal!")
            elif not xmls:
                st.error("Carregue os arquivos XML!")
            else:
                with st.spinner("O Sentinela está processando os dados..."):
                    try:
                        # Chama o cérebro (sentinela_core)
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                        
                        st.balloons()
                        st.download_button("💾 BAIXAR RELATÓRIO FINAL", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e:
                        st.error(f"Erro no processamento: {e}")
