import pandas as pd
import streamlit as st
import io

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Motor de processamento exclusivo para RET (Minas Gerais).
    Utiliza as colunas específicas fornecidas pelo usuário.
    """
    st.info("Iniciando processamento do Módulo RET (MG) com colunas customizadas...")

    # Lista de colunas fornecida por você
    colunas_gerencial = [
        "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC", "AC", "CFOP", "COD_ITEM", 
        "DESC_ITEM", "NCM", "UND", "VUNIT", "QTDE", "VITEM", "DESC", "FRETE", 
        "SEG", "OUTRAS", "VC_ITEM", "CST", "BC_ICMS", "ALIQ_ICMS", "ICMS", 
        "BC_ICMSST", "ICMSST", "IPI", "CST_PIS", "BC_PIS", "PIS", "CST_COF", 
        "BC_COF", "COF"
    ]

    try:
        def ler_gerencial_especifico(input_arquivos):
            if input_arquivos is None:
                return pd.DataFrame()
            
            lista_arquivos = input_arquivos if isinstance(input_arquivos, list) else [input_arquivos]
            dfs = []
            
            for arq in lista_arquivos:
                try:
                    arq.seek(0)
                    # Forçamos o separador ';' (comum em sistemas) e ignore_errors
                    # Se o erro persistir, o 'on_bad_lines' pula as linhas com problema (como a 61)
                    temp_df = pd.read_csv(
                        arq, 
                        sep=None, 
                        engine='python', 
                        encoding='latin1',
                        on_bad_lines='skip' 
                    )
                    
                    # Se o arquivo lido tiver número de colunas diferente, tentamos reajustar
                    if len(temp_df.columns) == len(colunas_gerencial):
                        temp_df.columns = colunas_gerencial
                    
                    dfs.append(temp_df)
                except Exception as e:
                    st.warning(f"Erro ao ler {arq.name}: {e}")
            
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        # 1. LEITURA DOS GERENCIAIS
        df_ger_e = ler_gerencial_especifico(ge)
        df_ger_s = ler_gerencial_especifico(gs)

        # 2. CRUZAMENTO PELA COLUNA 'NF'
        # Como não há Chave de Acesso, cruzamos pelo número da Nota Fiscal
        if not df_xs.empty and not df_ger_s.empty:
            # Padronizando NF no XML e no Gerencial para garantir o merge
            df_xs['NUM_NF'] = df_xs['NUM_NF'].astype(str).str.lstrip('0')
            df_ger_s['NF'] = df_ger_s['NF'].astype(str).str.lstrip('0')
            
            df_mapa = pd.merge(
                df_xs, 
                df_ger_s, 
                left_on='NUM_NF', 
                right_on='NF', 
                how='left'
            )
        else:
            df_mapa = df_xs.copy()

        # 3. GRAVAÇÃO DAS ABAS
        if not df_mapa.empty:
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
            
            # Formatação
            workbook = writer.book
            worksheet = writer.sheets['MAPA_RET']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df_mapa.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Aba de Entradas AC (Cruzando também pela NF se necessário)
        if not df_xe.empty:
            df_xe['NUM_NF'] = df_xe['NUM_NF'].astype(str).str.lstrip('0')
            if not df_ger_e.empty:
                df_ger_e['NF'] = df_ger_e['NF'].astype(str).str.lstrip('0')
                df_ent = pd.merge(df_xe, df_ger_e, left_on='NUM_NF', right_on='NF', how='left')
            else:
                df_ent = df_xe
            df_ent.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

        st.success("Módulo RET (MG) processado pela coluna NF!")

    except Exception as e:
        st.error(f"Erro no Motor RET: {str(e)}")
        pd.DataFrame({"Erro": [str(e)]}).to_excel(writer, sheet_name='ERRO_RET')
