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

def gerar_aba_entradas_ac(writer, df_ge, regras_tes):
    if df_ge is None or regras_tes is None: return
    
    mapa_regras = dict(zip(regras_tes['ACUMULADOR'].astype(str).str.strip(), regras_tes['REGRA_ESTORNO']))

    if 'codi_acu' in df_ge.columns:
        resumo = df_ge.groupby(['codi_acu', 'nome_acu']).agg({
            'vlr_cont': 'sum', 'base_icms': 'sum', 'vlr_icms': 'sum'
        }).reset_index()

        def aplicar_estorno(linha):
            ac = str(linha['codi_acu']).strip()
            regra = mapa_regras.get(ac, 'NÃO MAPEADO')
            if regra == 'ESTORNA TUDO':
                return pd.Series([linha['vlr_icms'], f"Estorno 100% (Regra: {regra})"])
            return pd.Series([0, f"Regra: {regra}"])

        resumo[['Estorno', 'Observação']] = resumo.apply(aplicar_estorno, axis=1)
        resumo.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    regras = carregar_regras_ret(cod_cliente)
    if regras:
        for nome in regras.keys():
            if 'MAPA' in nome.upper():
                regras[nome].to_excel(writer, sheet_name='MAPA_RET', index=False)
                break
        
        if 'TES' in regras and ge:
            from audit_gerencial import ler_arquivo_com_seguranca
            df_ge = ler_arquivo_com_seguranca(ge[0] if isinstance(ge, list) else ge)
            gerar_aba_entradas_ac(writer, df_ge, regras['TES'])
        st.success(f"🔺 RET Processado: {cod_cliente}")
    else:
        st.error(f"❌ Regras {cod_cliente}-RET_MG não encontradas.")
