import pandas as pd
import streamlit as st
import requests
import io

def carregar_regras_ret(cod_cliente):
    token = st.secrets.get("GITHUB_TOKEN")
    repo = st.secrets.get("GITHUB_REPO")
    headers = {"Authorization": f"token {token}"}
    for ext in ['.xlsx', '.xls']:
        url = f"https://raw.githubusercontent.com/{repo}/main/Bases_Tributárias/{cod_cliente}-RET_MG{ext}"
        try:
            res = requests.get(url, headers=headers)
            if res.status_code == 200:
                return pd.read_excel(io.BytesIO(res.content), sheet_name=None)
        except: continue
    return None

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    regras = carregar_regras_ret(cod_cliente)
    if not regras:
        st.error(f"Regras não encontradas para o cliente {cod_cliente}")
        return

    # 1. Aba MAPA_RET
    for nome in regras.keys():
        if 'MAPA' in nome.upper():
            regras[nome].to_excel(writer, sheet_name='MAPA_RET', index=False)
            break

    # 2. Aba ENTRADAS_AC (Lógica de Estorno)
    if 'TES' in regras and ge:
        # Relemos o arquivo para garantir os nomes de colunas
        cols_ent = ["NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "codi_acu", "CFOP", "COD_PROD", "nome_acu", "NCM", "UNID", "VUNIT", "QTDE", "VPROD", "DESP", "vlr_cont", "CST-ICMS", "base_icms", "vlr_icms", "BC-ICMS-ST", "ICMS-ST", "vlr_ipi", "CST_PIS", "BC_PIS", "VLR_PIS", "CST_COF", "BC_COF", "VLR_COF"]
        
        f = ge[0] if isinstance(ge, list) else ge
        f.seek(0)
        df_ge = pd.read_csv(f, sep=';', header=None, names=cols_ent, engine='python', encoding='latin-1')
        
        # Limpeza de valores (remove espaços e acerta decimal)
        for c in ['vlr_cont', 'vlr_icms']:
            df_ge[c] = pd.to_numeric(df_ge[c].astype(str).str.replace('.', '').str.replace(',', '.').str.strip(), errors='coerce').fillna(0)

        mapa_regras = dict(zip(regras['TES']['ACUMULADOR'].astype(str).str.strip(), regras['TES']['REGRA_ESTORNO']))
        
        resumo = df_ge.groupby(['codi_acu', 'nome_acu']).agg({'vlr_cont': 'sum', 'vlr_icms': 'sum'}).reset_index()
        
        def aplicar_estorno(linha):
            ac = str(linha['codi_acu']).strip()
            regra = mapa_regras.get(ac, 'SEM REGRA')
            return pd.Series([linha['vlr_icms'], f"Regra: {regra}"] if regra == 'ESTORNA TUDO' else [0, f"Regra: {regra}"])

        resumo[['Estorno', 'Observação']] = resumo.apply(aplicar_estorno, axis=1)
        resumo.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)
        st.success(f"Motor RET processado para {cod_cliente}")
