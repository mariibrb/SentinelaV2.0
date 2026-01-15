import streamlit as st
import os, io, pandas as pd
import requests
from style import aplicar_estilo_sentinela
from sentinela_core import extrair_dados_xml_recursivo, gerar_excel_final

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sentinela 2.0 | Auditoria Fiscal", page_icon="🧡", layout="wide")

# --- INJEÇÃO DA APARÊNCIA PREMIUM ---
aplicar_estilo_sentinela()

# --- FUNÇÕES DE SUPORTE (CONEXÃO GITHUB E CLIENTES) ---
@st.cache_data(ttl=600)
def carregar_base_clientes():
    """Carrega a lista de clientes do arquivo local"""
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
    """Valida se o arquivo de impostos existe no repositório privado"""
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

# --- SIDEBAR (COM SUA FOTO E O BOTÃO PÍLULA) ---
with st.sidebar:
    # Sua foto do Sentinela
    if os.path.exists(".streamlit/Sentinela.png"):
        st.image(".streamlit/Sentinela.png", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Função para o Gabarito
    def criar_gabarito():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(columns=["NCM", "CST_ESPERADA", "ALQ_INTER", "CST_PC_ESPERADA", "CST_IPI_ESPERADA", "ALQ_IPI_ESPERADA"]).to_excel(writer, sheet_name='GABARITO', index=False)
        return output.getvalue()
    
    # Botão de Download estilizado pelo style.py
    st.download_button("📥 Modelo Bases Tributárias", criar_gabarito(), "modelo_gabarito.xlsx", use_container_width=True)

# --- CORPO PRINCIPAL ---
st.markdown("<div class='titulo-principal'>SENTINELA | Análise Tributária</div><div class='barra-laranja'></div>", unsafe_allow_html=True)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown("### 👣 Passo 1: Seleção da Empresa")
    if not df_clientes.empty:
        opcoes = [f"{l['CÓD']} - {l['RAZÃO SOCIAL']}" for _, l in df_clientes.iterrows()]
        selecao = st.selectbox("Escolha", [""] + opcoes, label_visibility="collapsed")
    else: 
        st.error("⚠️ Base de clientes não encontrada no diretório .streamlit")
        selecao = None

if selecao:
    # Extração de dados do cliente selecionado
    cod_cliente = selecao.split(" - ")[0].strip()
    dados_empresa = df_clientes[df_clientes['CÓD'] == cod_cliente].iloc[0]
    cnpj_auditado = str(dados_empresa['CNPJ']).strip()

    with col_b:
        st.markdown("### ⚖️ Passo 2: Configuração")
        regime = st.selectbox("Regime", ["", "Lucro Real", "Lucro Presumido", "Simples Nacional", "MEI"], label_visibility="collapsed")
        is_ret = st.toggle("Habilitar MG (RET)")

    # Status Bar
    st.markdown(f"<div class='status-container'>📍 <b>Analisando:</b> {dados_empresa['RAZÃO SOCIAL']} | <b>CNPJ:</b> {cnpj_auditado}</div>", unsafe_allow_html=True)
    
    # Validação GitHub (Blindagem contra erro de localização)
    c1_stat, c2_stat = st.columns(2)
    
    path_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    if verificar_arquivo_github(path_base):
        with c1_stat: st.success("✅ Base de Impostos Conectada")
    else:
        with c1_stat: st.warning("⚠️ Base de Impostos não localizada no GitHub")
    
    if is_ret:
        path_ret = f"RET/{cod_cliente}-RET_MG.xlsx"
        if verificar_arquivo_github(path_ret):
            with c2_stat: st.success("✅ Modelo RET Localizado")
        else:
            with c2_stat: st.warning("⚠️ Modelo RET não encontrado")

    # Uploads
    st.markdown("### 📥 Passo 3: Central de Arquivos")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**Notas XML**")
        xmls = st.file_uploader("X", type=['zip', 'xml'], accept_multiple_files=True, label_visibility="collapsed")

    with c2:
        st.markdown("**Entradas (G e A)**")
        ge = st.file_uploader("G", type=['csv', 'xlsx'], accept_multiple_files=True, key="ge", label_visibility="collapsed")
        ae = st.file_uploader("A", type=['xlsx', 'csv'], accept_multiple_files=True, key="ae", label_visibility="collapsed")

    with c3:
        st.markdown("**Saídas (S e F)**")
        gs = st.file_uploader("S", type=['csv', 'xlsx'], accept_multiple_files=True, key="gs", label_visibility="collapsed")
        as_f = st.file_uploader("F", type=['xlsx', 'csv'], accept_multiple_files=True, key="as", label_visibility="collapsed")

    # Botão de Ação
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_btn, _ = st.columns([1, 1, 1])
    with col_btn:
        if st.button("🚀 INICIAR ANÁLISE"):
            if xmls and regime:
                with st.spinner("O Sentinela está processando os arquivos..."):
                    try:
                        # Chamada ao Motor (Core)
                        df_xe, df_xs = extrair_dados_xml_recursivo(xmls, cnpj_auditado)
                        
                        if df_xe.empty and df_xs.empty:
                            st.error("Nenhum dado válido extraído dos XMLs.")
                        else:
                            # Geração do Excel Final
                            relat = gerar_excel_final(df_xe, df_xs, ae, as_f, ge, gs, cod_cliente, regime, is_ret)
                            st.balloons()
                            st.download_button("💾 BAIXAR RELATÓRIO AGORA", relat, f"Sentinela_{cod_cliente}.xlsx", use_container_width=True)
                    except Exception as e:
                        st.error(f"Ocorreu um erro no processamento: {e}")
            else:
                st.warning("⚠️ Selecione o Regime e carregue os XMLs para começar.")
