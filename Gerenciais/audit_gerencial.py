import pandas as pd
import streamlit as st
import io

def gerar_abas_gerenciais(writer, ge, gs):
    """
    Replica os dados do CSV no Excel inserindo o cabeçalho fornecido e garantindo a gravação dos dados.
    """
    # Cabeçalho exato das ENTRADAS
    cols_ent = [
        "NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "codi_acu", 
        "CFOP", "COD_PROD", "nome_acu", "NCM", "UNID", "VUNIT", 
        "QTDE", "VPROD", "DESP", "vlr_cont", "CST-ICMS", "base_icms", 
        "vlr_icms", "BC-ICMS-ST", "ICMS-ST", "vlr_ipi", "CST_PIS", 
        "BC_PIS", "VLR_PIS", "CST_COF", "BC_COF", "VLR_COF"
    ]

    # Cabeçalho exato das SAÍDAS
    cols_sai = [
        "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC_TOTAL", "codi_acu", 
        "CFOP", "COD_ITEM", "nome_acu", "NCM", "UND", "VUNIT", 
        "QTDE", "VITEM", "DESC", "FRETE", "SEG", "OUTRAS", 
        "vlr_cont", "CST", "base_icms", "ALIQ_ICMS", "vlr_icms", 
        "BC_ICMSST", "ICMSST", "vlr_ipi", "CST_PIS", "BC_PIS", 
        "PIS", "CST_COF", "BC_COF", "COF"
    ]

    # --- PROCESSAMENTO ENTRADA ---
    if ge:
        arquivos_ge = ge if isinstance(ge, list) else [ge]
        dfs_e = []
        for f in arquivos_ge:
            try:
                f.seek(0)
                # Lê forçando todos como string e usando engine python para maior compatibilidade
                df = pd.read_csv(f, sep=';', header=None, names=cols_ent, engine='python', encoding='latin-1', dtype=str)
                dfs_e.append(df)
            except Exception as e:
                st.error(f"Erro ao processar arquivo de Entrada {f.name}: {e}")
        
        if dfs_e:
            df_final_e = pd.concat(dfs_e, ignore_index=True)
            df_final_e.to_excel(writer, sheet_name='GERENCIAL_ENTRADAS', index=False)

    # --- PROCESSAMENTO SAÍDA ---
    if gs:
        arquivos_gs = gs if isinstance(gs, list) else [gs]
        dfs_s = []
        for f in arquivos_gs:
            try:
                f.seek(0)
                df = pd.read_csv(f, sep=';', header=None, names=cols_sai, engine='python', encoding='latin-1', dtype=str)
                dfs_s.append(df)
            except Exception as e:
                st.error(f"Erro ao processar arquivo de Saída {f.name}: {e}")
        
        if dfs_s:
            df_final_s = pd.concat(dfs_s, ignore_index=True)
            df_final_s.to_excel(writer, sheet_name='GERENCIAL_SAIDAS', index=False)
