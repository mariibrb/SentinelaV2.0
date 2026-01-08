import pandas as pd
import requests, io, streamlit as st

ALIQUOTAS_UF = {'SP': 18.0, 'RJ': 20.0, 'MG': 18.0, 'PR': 19.5, 'SC': 17.0, 'RS': 17.0, 'ES': 17.0, 'GO': 19.0, 'MT': 17.0, 'MS': 17.0, 'DF': 20.0, 'BA': 20.5, 'PE': 20.5, 'CE': 20.0, 'RN': 20.0, 'PB': 20.0, 'AL': 19.0, 'SE': 19.0, 'MA': 22.0, 'PI': 21.0, 'PA': 19.0, 'AM': 20.0, 'TO': 20.0, 'AC': 19.0, 'RO': 19.5, 'RR': 20.0, 'AP': 18.0}

def processar_icms(df, writer, cod_cliente):
    df_i = df.copy()
    # Logica de busca de base do cliente omitida aqui para brevidade, mas deve ser inclusa
    def audit(r):
        if r['UF_EMIT'] != r['UF_DEST'] and str(r['ORIGEM']) in ['1','2','3','8']: alq_e = 4.0
        else: alq_e = ALIQUOTAS_UF.get(r['UF_DEST'], 18.0)
        diag = "✅ OK" if abs(r['ALQ-ICMS'] - alq_e) < 0.01 else f"❌ Erro: Esperado {alq_e}%"
        return pd.Series([diag, alq_e])
    
    df_i[['Diagnóstico', 'Alq Esperada']] = df_i.apply(audit, axis=1)
    cols = [c for c in df_i.columns if c not in ['Situação Nota', 'Diagnóstico']]
    df_i[cols + ['Situação Nota', 'Diagnóstico']].to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
