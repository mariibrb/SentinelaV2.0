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

# --- SIDEBAR (COM A SUA IMAGEM DE VOLTA!) ---
with st.sidebar:
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER"]).to_excel(writer, index=False)
        return output.getvalue()
    
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "modelo_bases.xlsx", use_container_width=True)

# --- CONTEÚDO PRINCIPAL ---
st.markdown("<div class='titulo-principal'>SENTINELA | Análise Tributária</div><div class='barra-laranja'></div>", unsafe_allow_html=True)

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

    st.markdown(f"<div class='status-container'>📍 <b>Empresa:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub
    if verificar_arquivo_github(f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"):
        st.success("✅ Base de Impostos localizada")
    else: st.warning("⚠️ Base de Impostos não encontrada")

    st.markdown("### 📥 Passo 3: Central de Arquivos")
    c1, c2, c3 = st.columns(3)
    with c1:
        xmls = st.file_uploader("Notas XML", type=['zip', 'xml'], accept_multiple_files=True)
    with c2:
        ge = st.file_uploader("Entradas G", type=['csv', 'xlsx'], accept_multiple_files=True)
        ae = st.file_uploader("Entradas A", type=['xlsx', 'csv'], accept_multiple_files=True)
    with c3:
        gs = st.file_uploader("Saídas S", type=['csv', 'xlsx'], accept_multiple_files=True)
        as_f = st.file_uploader("Saídas F", type=['xlsx', 'csv'], accept_multiple_files=True)

    if st.button("🚀 INICIAR ANÁLISE"):
        if xmls and regime:
            with st.spinner("Processando..."):
                try:
                    df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                    relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                    st.balloons()
                    st.download_button("💾 BAIXAR RELATÓRIO", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                except Exception as e: st.error(f"Erro: {e}")
