import pandas as pd

def processar_icms(df, writer, cod_cliente):
    df_i = df.copy()
    # Ordem: Tags -> Status -> Análise
    def audit(r):
        # Lógica de Gabarito e Trava 4% aqui
        alq_e = 18.0 # Simplificado para exemplo, usar dicionário ALIQUOTAS_UF
        diag = "✅ OK" if abs(r['ALQ-ICMS'] - alq_e) < 0.01 else "❌ Divergência"
        return pd.Series([diag, alq_e])
    
    df_i[['Diagnóstico', 'Esperado']] = df_i.apply(audit, axis=1)
    tags = [c for c in df_i.columns if c not in ['Situação Nota', 'Diagnóstico', 'Esperado']]
    df_i[tags + ['Situação Nota', 'Diagnóstico', 'Esperado']].to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
