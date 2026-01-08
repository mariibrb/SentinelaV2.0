import pandas as pd

def gerar_aba_resumo(writer):
    man = [
        ["MANUAL DE DIAGNÓSTICOS SENTINELA"], [""],
        ["[ICMS_AUDIT] - Valida Trava de 4%, Gabarito e Alíquotas Internas."],
        ["[IPI_AUDIT] - Confronto com TIPI.csv federal."],
        ["[PIS_COFINS_AUDIT] - Valida CST Saída vs Base Cliente."],
        ["[DIFAL_AUDIT] - Analisa obrigatoriedade para não-contribuinte."],
        ["[DIFAL_ST_FECP] - Somatória autorizada UF/IE (Ignora Canceladas)."]
    ]
    pd.DataFrame(man).to_excel(writer, sheet_name='RESUMO', index=False, header=False)
