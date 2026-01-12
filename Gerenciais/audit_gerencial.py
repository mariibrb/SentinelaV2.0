import pandas as pd
import streamlit as st

def gerar_abas_gerenciais(writer, ge, gs):
    """
    Replica os dados do CSV no Excel inserindo o cabeçalho fornecido.
    """
    # Cabeçalho exato das ENTRADAS que você passou
    cols_ent = [
        "NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "codi_acu", 
        "CFOP", "COD_PROD", "nome_acu", "NCM", "UNID", "VUNIT", 
        "QTDE", "VPROD", "DESP", "vlr_cont", "CST-ICMS", "base_icms", 
        "vlr_icms", "BC-ICMS-ST", "ICMS-ST", "vlr_ipi", "CST_PIS", 
        "BC_PIS", "VLR_PIS", "CST_COF", "BC_COF", "VLR_COF"
    ]

    # Cabeçalho exato das SAÍDAS que você passou
    cols_sai = [
        "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC_TOTAL", "codi_acu", 
        "CFOP", "COD_ITEM", "nome_acu", "NCM", "UND", "VUNIT", 
        "QTDE", "VITEM", "DESC", "FRETE", "SEG", "OUTRAS", 
        "vlr_cont", "CST", "base_icms", "ALIQ_ICMS", "vlr_icms", 
        "BC_ICMSST", "ICMSST", "vlr_ipi", "CST_PIS", "BC_PIS", 
        "PIS", "CST_COF", "BC_COF", "COF"
    ]

    # Processamento ENTRADA
    if ge:
        arquivos_ge = ge if isinstance(ge, list) else [ge]
        dfs_e = []
        for f in arquivos_ge:
            f.seek(0)
            # Lê o CSV sem cabeçalho e aplica a lista de colunas
            df = pd.read_csv(f, sep=';', header=None, names=cols_ent, engine='python', encoding='latin-1')
            dfs_e.append(df)
        if dfs_e:
            pd.concat(dfs_e).to_excel(writer, sheet_name='GERENCIAL_ENTRADA', index=False)

    # Processamento SAÍDA
    if gs:
        arquivos_gs = gs if isinstance(gs, list) else [gs]
        dfs_s = []
        for f in arquivos_gs:
            f.seek(0)
            # Lê o CSV sem cabeçalho e aplica a lista de colunas
            df = pd.read_csv(f, sep=';', header=None, names=cols_sai, engine='python', encoding='latin-1')
            dfs_s.append(df)
        if dfs_s:
            pd.concat(dfs_s).to_excel(writer, sheet_name='GERENCIAL_SAIDA', index=False)
