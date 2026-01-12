import pandas as pd
import streamlit as st

def ler_gerencial_especifico(arquivo):
    """
    Lê o gerencial tratando as particularidades que você mapeou (AC, Valores, etc).
    """
    try:
        arquivo.seek(0)
        if arquivo.name.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(arquivo)
        else:
            # Uso de latin-1 para evitar erro em nomes de acumuladores com acento
            df = pd.read_csv(arquivo, sep=None, engine='python', on_bad_lines='skip', encoding='latin-1')
        
        # Limpeza básica: remove linhas totalmente vazias que gerenciais costumam ter no fim
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        st.error(f"Erro ao ler gerencial {arquivo.name}: {e}")
        return pd.DataFrame()

def gerar_abas_gerenciais(writer, ge, gs):
    """
    Consolida os gerenciais de Entrada e Saída.
    """
    # Processando Entradas
    if ge:
        list_ge = ge if isinstance(ge, list) else [ge]
        df_ent_final = pd.concat([ler_gerencial_especifico(f) for f in list_ge], ignore_index=True)
        if not df_ent_final.empty:
            df_ent_final.to_excel(writer, sheet_name='GERENCIAL_ENTRADA', index=False)

    # Processando Saídas
    if gs:
        list_gs = gs if isinstance(gs, list) else [gs]
        df_sai_final = pd.concat([ler_gerencial_especifico(f) for f in list_gs], ignore_index=True)
        if not df_sai_final.empty:
            df_sai_final.to_excel(writer, sheet_name='GERENCIAL_SAIDA', index=False)
