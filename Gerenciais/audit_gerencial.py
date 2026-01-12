import pandas as pd
import streamlit as st
import io

def ler_gerencial_puro(arquivo):
    """
    Lê o CSV sem cabeçalho e força a estrutura de colunas exata.
    """
    try:
        arquivo.seek(0)
        # Se for Excel, lê normal
        if arquivo.name.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(arquivo)
            # Padronização mínima para Excel
            mapeamento = {'AC': 'codi_acu', 'DESCR': 'nome_acu', 'DESC_ITEM': 'nome_acu', 
                         'VC': 'vlr_cont', 'VC_ITEM': 'vlr_cont', 'BC-ICMS': 'base_icms', 
                         'BC_ICMS': 'base_icms', 'VLR-ICMS': 'vlr_icms', 'ICMS': 'vlr_icms'}
            return df.rename(columns=mapeamento)

        # Se for CSV (como os que enviou), lê sem cabeçalho (header=None)
        df = pd.read_csv(
            arquivo, 
            sep=';', 
            header=None, 
            engine='python', 
            encoding='latin-1'
        )

        # Identifica se é Entrada ou Saída pela quantidade de colunas ou nome
        is_entrada = "entrada" in arquivo.name.lower() or len(df.columns) == 28
        
        if is_entrada:
            # Colunas da Entrada (Baseado na sua lista de 28 colunas)
            colunas_e = [
                "NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "codi_acu", 
                "CFOP", "COD_PROD", "nome_acu", "NCM", "UNID", "VUNIT", 
                "QTDE", "VPROD", "DESP", "vlr_cont", "CST-ICMS", "base_icms", 
                "vlr_icms", "BC-ICMS-ST", "ICMS-ST", "vlr_ipi", "CST_PIS", 
                "BC_PIS", "VLR_PIS", "CST_COF", "BC_COF", "VLR_COF"
            ]
            df.columns = colunas_e[:len(df.columns)]
        else:
            # Colunas da Saída (Baseado na sua lista de 32 colunas)
            colunas_s = [
                "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "vlr_cont_total", "codi_acu", 
                "CFOP", "COD_ITEM", "nome_acu", "NCM", "UND", "VUNIT", 
                "QTDE", "VITEM", "DESC", "FRETE", "SEG", "OUTRAS", 
                "vlr_cont", "CST", "base_icms", "ALIQ_ICMS", "vlr_icms", 
                "BC_ICMSST", "ICMSST", "vlr_ipi", "CST_PIS", "BC_PIS", 
                "PIS", "CST_COF", "BC_COF", "COF"
            ]
            df.columns = colunas_s[:len(df.columns)]

        # --- LIMPEZA DE NÚMEROS (O segredo para os valores aparecerem) ---
        def limpar_valor(valor):
            if pd.isna(valor): return 0.0
            s = str(valor).strip().replace('.', '').replace(',', '.')
            try:
                return float(s)
            except:
                return 0.0

        cols_financeiras = ['vlr_cont', 'base_icms', 'vlr_icms', 'vlr_ipi']
        for col in cols_financeiras:
            if col in df.columns:
                df[col] = df[col].apply(limpar_valor)
        
        return df

    except Exception as e:
        st.error(f"Erro ao ler {arquivo.name}: {e}")
        return pd.DataFrame()

def gerar_abas_gerenciais(writer, ge, gs):
    """Consolida e salva no Excel"""
    if ge:
        lista_ge = ge if isinstance(ge, list) else [ge]
        df_ent = pd.concat([ler_gerencial_puro(f) for f in lista_ge], ignore_index=True)
        if not df_ent.empty:
            df_ent.to_excel(writer, sheet_name='GERENCIAL_ENTRADA', index=False)

    if gs:
        lista_gs = gs if isinstance(gs, list) else [gs]
        df_sai = pd.concat([ler_gerencial_puro(f) for f in lista_gs], ignore_index=True)
        if not df_sai.empty:
            df_sai.to_excel(writer, sheet_name='GERENCIAL_SAIDA', index=False)
