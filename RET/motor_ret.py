import pandas as pd
import streamlit as st
import io

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Motor de processamento RET (MG) para extratos da Domínio Sistemas sem cabeçalho.
    Aplica manualmente a estrutura de colunas fornecida pelo usuário.
    """
    st.info("Iniciando processamento RET: Aplicando estrutura de colunas da Domínio Sistemas...")

    # Lista exata de 32 colunas fornecida por você
    colunas_dominio = [
        "NF", "DATA_EMISSAO", "CNPJ", "Ufp", "VC", "AC", "CFOP", "COD_ITEM", 
        "DESC_ITEM", "NCM", "UND", "VUNIT", "QTDE", "VITEM", "DESC", "FRETE", 
        "SEG", "OUTRAS", "VC_ITEM", "CST", "BC_ICMS", "ALIQ_ICMS", "ICMS", 
        "BC_ICMSST", "ICMSST", "IPI", "CST_PIS", "BC_PIS", "PIS", "CST_COF", 
        "BC_COF", "COF"
    ]

    def ler_gerencial_sem_cabecalho(input_arquivos):
        if input_arquivos is None:
            return pd.DataFrame()
        
        lista_arquivos = input_arquivos if isinstance(input_arquivos, list) else [input_arquivos]
        dfs = []
        
        for arq in lista_arquivos:
            try:
                arq.seek(0)
                # Lemos o CSV ignorando a primeira linha (se houver lixo) ou tratando como dados
                # names=colunas_dominio força o nome das colunas
                # header=0 diz que a primeira linha do arquivo deve ser substituída pelos nomes abaixo
                df_temp = pd.read_csv(
                    arq, 
                    sep=None, 
                    engine='python', 
                    encoding='latin1', 
                    on_bad_lines='skip',
                    names=colunas_dominio,
                    header=0, 
                    dtype=str
                )
                dfs.append(df_temp)
            except Exception as e:
                st.warning(f"Erro ao processar arquivo {arq.name}: {e}")
        
        if not dfs:
            return pd.DataFrame()
            
        return pd.concat(dfs, ignore_index=True)

    try:
        # 1. LEITURA FORÇADA DOS GERENCIAIS
        df_ger_e = ler_gerencial_sem_cabecalho(ge)
        df_ger_s = ler_gerencial_sem_cabecalho(gs)

        # 2. CRUZAMENTO (MERGE) PELA COLUNA 'NF'
        # Padronização para garantir que '00123' cruze com '123'
        if not df_xs.empty and not df_ger_s.empty:
            df_xs['NF_JOIN'] = df_xs['NUM_NF'].astype(str).str.lstrip('0').str.strip()
            df_ger_s['NF_JOIN'] = df_ger_s['NF'].astype(str).str.lstrip('0').str.strip()
            
            df_mapa = pd.merge(
                df_xs, 
                df_ger_s, 
                left_on='NF_JOIN', 
                right_on='NF_JOIN', 
                how='left'
            )
            df_mapa.drop(columns=['NF_JOIN'], inplace=True)
        else:
            df_mapa = df_xs.copy()

        # 3. GRAVAÇÃO DAS ABAS ESPECÍFICAS
        if not df_mapa.empty:
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
            
            # Formatação estética do cabeçalho
            workbook = writer.book
            worksheet = writer.sheets['MAPA_RET']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df_mapa.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Aba de Entradas AC
        if not df_xe.empty:
            if not df_ger_e.empty:
                df_xe['NF_JOIN'] = df_xe['NUM_NF'].astype(str).str.lstrip('0').str.strip()
                df_ger_e['NF_JOIN'] = df_ger_e['NF'].astype(str).str.lstrip('0').str.strip()
                df_ent = pd.merge(df_xe, df_ger_e, on='NF_JOIN', how='left')
                df_ent.drop(columns=['NF_JOIN'], inplace=True)
            else:
                df_ent = df_xe
            df_ent.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

        st.success("Módulo RET finalizado com dados da Domínio Sistemas!")

    except Exception as e:
        st.error(f"Erro no processamento do Motor RET: {str(e)}")
        # Cria aba de log para não impedir a geração do arquivo
        pd.DataFrame({"Erro": [str(e)], "Status": ["Verifique se o CSV tem 32 colunas"]}).to_excel(writer, sheet_name='ERRO_RET')
