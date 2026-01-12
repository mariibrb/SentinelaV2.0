import pandas as pd
import streamlit as st
import io

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Motor RET (MG) - Versão Especialista Domínio Sistemas.
    Layouts: Entradas (31 colunas) | Saídas (32 colunas).
    """
    st.info("Processando Módulo RET: Aplicando layouts específicos da Domínio Sistemas...")

    # Layout de SAÍDAS (32 Colunas conforme sua lista vertical)
    cols_saida = [
        "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC", "AC", "CFOP", "COD_ITEM", 
        "DESC_ITEM", "NCM", "UND", "VUNIT", "QTDE", "VITEM", "DESC", "FRETE", 
        "SEG", "OUTRAS", "VC_ITEM", "CST", "BC_ICMS", "ALIQ_ICMS", "ICMS", 
        "BC_ICMSST", "ICMSST", "IPI", "CST_PIS", "BC_PIS", "PIS", "CST_COF", 
        "BC_COF", "COF"
    ]

    # Layout de ENTRADAS (31 Colunas conforme sua lista vertical)
    cols_entrada = [
        "NUM_NF", "DATA_EMISSAO", "CNPJ", "UF", "VLR_NF", "AC", "CFOP", "COD_PROD", 
        "DESCR", "NCM", "UNID", "VUNIT", "QTDE", "VPROD", "DESC", "FRETE", 
        "SEG", "DESP", "VC", "CST-ICMS", "BC-ICMS", "VLR-ICMS", "BC-ICMS-ST", 
        "ICMS-ST", "VLR_IPI", "CST_PIS", "BC_PIS", "VLR_PIS", "CST_COF", 
        "BC_COF", "VLR_COF"
    ]

    def ler_dominio_custom(input_arquivos, colunas_alvo):
        if input_arquivos is None:
            return pd.DataFrame()
        
        lista_arquivos = input_arquivos if isinstance(input_arquivos, list) else [input_arquivos]
        dfs = []
        
        for arq in lista_arquivos:
            try:
                arq.seek(0)
                # Detecta o número de colunas no arquivo físico para ajuste dinâmico
                df_check = pd.read_csv(arq, sep=None, engine='python', encoding='latin1', nrows=0)
                cols_reais = len(df_check.columns)
                
                # Previne o erro de "mismatch" caso o arquivo tenha colunas vazias no final
                if cols_reais > len(colunas_alvo):
                    nomes_final = colunas_alvo + [f"EXTRA_{i}" for i in range(cols_reais - len(colunas_alvo))]
                else:
                    nomes_final = colunas_alvo[:cols_reais]

                arq.seek(0)
                df_temp = pd.read_csv(
                    arq, 
                    sep=None, 
                    engine='python', 
                    encoding='latin1', 
                    on_bad_lines='skip',
                    names=nomes_final,
                    header=0, 
                    dtype=str
                )
                dfs.append(df_temp)
            except Exception as e:
                st.warning(f"Erro no processamento do arquivo {arq.name}: {e}")
        
        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

    try:
        # 1. LEITURA DOS GERENCIAIS
        df_ger_e = ler_dominio_custom(ge, cols_entrada)
        df_ger_s = ler_dominio_custom(gs, cols_saida)

        # 2. CRUZAMENTO DE SAÍDAS (XML x Gerencial via NF)
        if not df_xs.empty and not df_ger_s.empty:
            df_xs['NF_JOIN'] = df_xs['NUM_NF'].astype(str).str.lstrip('0').str.strip()
            if 'NF' in df_ger_s.columns:
                df_ger_s['NF_JOIN'] = df_ger_s['NF'].astype(str).str.lstrip('0').str.strip()
                df_mapa = pd.merge(df_xs, df_ger_s, on='NF_JOIN', how='left')
                df_mapa.drop(columns=['NF_JOIN'], inplace=True)
            else:
                df_mapa = df_xs.copy()
        else:
            df_mapa = df_xs.copy()

        # 3. GRAVAÇÃO DA ABA MAPA_RET
        if not df_mapa.empty:
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
            workbook = writer.book
            worksheet = writer.sheets['MAPA_RET']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df_mapa.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # 4. CRUZAMENTO DE ENTRADAS (XML x Gerencial via NUM_NF)
        if not df_xe.empty:
            if not df_ger_e.empty:
                df_xe['NF_JOIN'] = df_xe['NUM_NF'].astype(str).str.lstrip('0').str.strip()
                if 'NUM_NF' in df_ger_e.columns:
                    df_ger_e['NF_JOIN'] = df_ger_e['NUM_NF'].astype(str).str.lstrip('0').str.strip()
                    df_ent = pd.merge(df_xe, df_ger_e, on='NF_JOIN', how='left', suffixes=('', '_GER'))
                    df_ent.drop(columns=['NF_JOIN'], inplace=True)
                else:
                    df_ent = df_xe
            else:
                df_ent = df_xe
            df_ent.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

        st.success(f"Módulo RET MG finalizado com sucesso!")

    except Exception as e:
        st.error(f"Erro Crítico no Motor RET: {str(e)}")
        pd.DataFrame({"Erro": [str(e)]}).to_excel(writer, sheet_name='ERRO_RET')
