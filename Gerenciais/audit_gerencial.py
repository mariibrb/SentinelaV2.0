import pandas as pd
import streamlit as st
import io

def ler_arquivo_com_seguranca(arquivo):
    """
    Lê o gerencial sem cabeçalho e aplica o mapeamento exato fornecido pelo usuário.
    """
    try:
        arquivo.seek(0)
        if arquivo.name.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(arquivo)
        else:
            # Lê o CSV com ponto-e-vírgula e sem cabeçalho
            df = pd.read_csv(
                arquivo, 
                sep=';', 
                header=None, 
                engine='python', 
                encoding='latin-1',
                decimal=','
            )
            
            # Mapeamento exato baseado na sua lista de colunas
            if "entradas" in arquivo.name.lower():
                colunas = [
                    "NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "codi_acu", 
                    "CFOP", "COD_PROD", "nome_acu", "NCM", "UNID", "VUNIT", 
                    "QTDE", "vlr_cont", "DESP", "VC", "CST-ICMS", "base_icms", 
                    "vlr_icms", "BC-ICMS-ST", "ICMS-ST", "vlr_ipi", "CST_PIS", 
                    "BC_PIS", "VLR_PIS", "CST_COF", "BC_COF", "VLR_COF"
                ]
            else: # Saídas
                colunas = [
                    "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC", "codi_acu", 
                    "CFOP", "COD_ITEM", "nome_acu", "NCM", "UND", "VUNIT", 
                    "QTDE", "VITEM", "DESC", "FRETE", "SEG", "OUTRAS", 
                    "vlr_cont", "CST", "base_icms", "ALIQ_ICMS", "vlr_icms", 
                    "BC_ICMSST", "ICMSST", "vlr_ipi", "CST_PIS", "BC_PIS", 
                    "PIS", "CST_COF", "BC_COF", "COF"
                ]
            
            # Atribui os nomes se a quantidade de colunas bater, senão mapeia por posição
            if len(df.columns) == len(colunas):
                df.columns = colunas
            else:
                # Fallback caso o arquivo venha com colunas extras/faltantes
                df = df.rename(columns={5: 'codi_acu', 8: 'nome_acu', 13: 'vlr_cont', 20: 'base_icms', 22: 'vlr_icms'})

            # Converte valores para número
            for col in ['vlr_cont', 'base_icms', 'vlr_icms', 'vlr_ipi']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce').fillna(0)
        
        return df.dropna(how='all')
    except Exception as e:
        st.error(f"Erro ao processar o arquivo {arquivo.name}: {e}")
        return pd.DataFrame()

def gerar_abas_gerenciais(writer, ge, gs):
    if ge:
        lista_ge = ge if isinstance(ge, list) else [ge]
        df_ent = pd.concat([ler_arquivo_com_seguranca(f) for f in lista_ge], ignore_index=True)
        if not df_ent.empty:
            df_ent.to_excel(writer, sheet_name='GERENCIAL_ENTRADA', index=False)

    if gs:
        lista_gs = gs if isinstance(gs, list) else [gs]
        df_sai = pd.concat([ler_arquivo_com_seguranca(f) for f in lista_gs], ignore_index=True)
        if not df_sai.empty:
            df_sai.to_excel(writer, sheet_name='GERENCIAL_SAIDA', index=False)
