import pandas as pd
import streamlit as st
import requests
import io

def carregar_regras_ret(cod_cliente):
    """Busca o arquivo COD-RET_MG.xlsx no GitHub"""
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    # Tenta buscar tanto .xlsx quanto .xls para garantir
    url = f"https://raw.githubusercontent.com/{repo}/main/Bases_Tributárias/{cod_cliente}-RET_MG.xlsx"
    headers = {"Authorization": f"token {token}"}
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            return pd.read_excel(io.BytesIO(res.content), sheet_name=None)
        return None
    except:
        return None

def mapear_colunas(df):
    """Mapeia nomes de colunas variados para o padrão do motor"""
    dicionario_colunas = {
        'vlr_cont': ['Vlr Contábil', 'Valor Contábil', 'VLR_CONT', 'vlr_cont', 'Valor Total', 'Vlr. Contábil'],
        'vlr_icms': ['Vlr ICMS', 'Valor ICMS', 'VLR_ICMS', 'vlr_icms', 'Vlr. ICMS'],
        'base_icms': ['Base ICMS', 'BC ICMS', 'BASE_ICMS', 'base_icms', 'Base Calc. ICMS'],
        'codi_acu': ['Acumulador', 'Cod. Acu.', 'CODI_ACU', 'codi_acu', 'Código Acumulador'],
        'nome_acu': ['Descrição Acumulador', 'NOME_ACU', 'nome_acu', 'Nome Acumulador', 'Descrição']
    }
    
    mapeamento_final = {}
    for padrao, variacoes in dicionario_colunas.items():
        for var in variacoes:
            if var in df.columns:
                mapeamento_final[var] = padrao
                break
    return df.rename(columns=mapeamento_final)

def gerar_aba_entradas_ac(writer, ge, regras_tes):
    """Processa o Gerencial de Entradas e aplica regras de estorno"""
    if ge is None or regras_tes is None:
        return

    try:
        # Carregamento flexível
        if isinstance(ge, pd.DataFrame):
            df_ge = ge.copy()
        else:
            df_ge = pd.read_excel(ge) if ge.name.endswith(('.xlsx', '.xls')) else pd.read_csv(ge, sep=None, engine='python')
        
        # Padroniza as colunas do gerencial
        df_ge = mapear_colunas(df_ge)
        
        # Garante que as colunas numéricas sejam números
        cols_numericas = ['vlr_cont', 'base_icms', 'vlr_icms']
        for col in cols_numericas:
            if col in df_ge.columns:
                df_ge[col] = pd.to_numeric(df_ge[col], errors='coerce').fillna(0)

        # Mapeamento de regras do GitHub
        mapa_regras = dict(zip(regras_tes['ACUMULADOR'].astype(str).str.strip(), regras_tes['REGRA_ESTORNO']))

        # Agrupamento (Tabela Dinâmica)
        resumo = df_ge.groupby(['codi_acu', 'nome_acu']).agg({
            'vlr_cont': 'sum',
            'base_icms': 'sum',
            'vlr_icms': 'sum'
        }).reset_index()

        # Adiciona Estorno e Observação
        def aplicar_estorno(linha):
            ac = str(linha['codi_acu']).strip()
            regra = mapa_regras.get(ac, 'NÃO MAPEADO')
            if regra == 'ESTORNA TUDO':
                return pd.Series([linha['vlr_icms'], f"Estorno 100% (AC {ac})"])
            return pd.Series([0, f"Sem estorno (Regra: {regra})"])

        resumo[['Estorno', 'Observação']] = resumo.apply(aplicar_estorno, axis=1)
        resumo.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)
        
    except Exception as e:
        st.error(f"Erro ao processar aba Entradas AC: {e}")

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    regras = carregar_regras_ret(cod_cliente)
    
    if regras:
        # 1. Habilita a aba MAPA_RET (Espelho)
        aba_mapa = None
        for nome_aba in regras.keys():
            if 'MAPA' in nome_aba.upper():
                aba_mapa = regras[nome_aba]
                break
        
        if aba_mapa is not None:
            aba_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
        
        # 2. Habilita a aba ENTRADAS_AC
        if 'TES' in regras and ge:
            arquivo_ge = ge[0] if isinstance(ge, list) else ge
            gerar_aba_entradas_ac(writer, arquivo_ge, regras['TES'])
            
        st.success(f"🔺 Motor RET Minas processado para o cliente {cod_cliente}")
    else:
        st.error(f"❌ Base de regras {cod_cliente}-RET_MG.xlsx não encontrada no GitHub.")
