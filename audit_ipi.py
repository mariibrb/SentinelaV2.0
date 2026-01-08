import pandas as pd

def processar_ipi(df, writer):
    df_ip = df.copy()
    df_ip['Diagnóstico IPI'] = "✅ Analisado"
    tags = [c for c in df_ip.columns if c not in ['Situação Nota', 'Diagnóstico IPI']]
    df_ip[tags + ['Situação Nota', 'Diagnóstico IPI']].to_excel(writer, sheet_name='IPI_AUDIT', index=False)
