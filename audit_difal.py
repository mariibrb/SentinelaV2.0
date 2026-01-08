import pandas as pd

def processar_difal(df, writer):
    df_dif = df.copy()
    df_dif['Análise DIFAL'] = "✅ Analisado"
    tags = [c for c in df_dif.columns if c not in ['Situação Nota', 'Análise DIFAL']]
    df_dif[tags + ['Situação Nota', 'Análise DIFAL']].to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)
