import pandas as pd
import streamlit as st
import io

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Motor de processamento exclusivo para empresas detentoras de RET em MG.
    Realiza o cruzamento entre XMLs e arquivos Gerenciais do cliente.
    """
    st.info("Iniciando processamento do Módulo RET (Minas Gerais)...")

    try:
        # --- FUNÇÃO INTERNA PARA TRATAR LISTA DE ARQUIVOS ---
        def ler_gerencial(input_arquivos):
            if input_arquivos is None:
                return pd.DataFrame()
            
            # Se for um arquivo único, transforma em lista para padronizar o loop
            lista_arquivos = input_arquivos if isinstance(input_arquivos, list) else [input_arquivos]
            
            dfs = []
            for arq in lista_arquivos:
                try:
                    arq.seek(0)
                    if arq.name.lower().endswith(('.xlsx', '.xls')):
                        temp_df = pd.read_excel(arq)
                    else:
                        # Tenta ler CSV com detecção automática de separador
                        temp_df = pd.read_csv(arq, sep=None, engine='python', encoding='latin1')
                    dfs.append(temp_df)
                except Exception as e:
                    st.warning(f"Não foi possível ler o arquivo {arq.name}: {e}")
            
            return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

        # 1. LEITURA DOS ARQUIVOS GERENCIAIS (Tratando a lista vinda do Core)
        df_ger_e = ler_gerencial(ge)
        df_ger_s = ler_gerencial(gs)

        # 2. IDENTIFICAÇÃO DA COLUNA DE CHAVE NO GERENCIAL
        col_chave_ger = None
        if not df_ger_s.empty:
            # Busca por colunas que contenham 'CHAVE' ou 'NF' no nome
            candidatos = [c for c in df_ger_s.columns if any(x in str(c).upper() for x in ['CHAVE', 'NFE', 'NF-E'])]
            if candidatos:
                col_chave_ger = candidatos[0]
                # Limpeza da chave: remove caracteres não numéricos
                df_ger_s[col_chave_ger] = df_ger_s[col_chave_ger].astype(str).str.replace(r'\D', '', regex=True)

        # 3. LÓGICA DE CRUZAMENTO (XML vs GERENCIAL)
        if not df_xs.empty:
            # Garante que a chave do XML também esteja limpa
            df_xs['CHAVE_ACESSO'] = df_xs['CHAVE_ACESSO'].astype(str).str.replace(r'\D', '', regex=True)
            
            if not df_ger_s.empty and col_chave_ger:
                # Cruzamento (Merge)
                df_mapa = pd.merge(
                    df_xs, 
                    df_ger_s, 
                    left_on='CHAVE_ACESSO', 
                    right_on=col_chave_ger, 
                    how='left',
                    suffixes=('_XML', '_GER')
                )
            else:
                df_mapa = df_xs.copy()
                if not col_chave_ger:
                    st.warning("Coluna de 'Chave de Acesso' não identificada no arquivo Gerencial de Saída.")
        else:
            df_mapa = pd.DataFrame()

        # 4. GRAVAÇÃO DAS ABAS NO EXCEL
        # Aba MAPA_RET
        if not df_mapa.empty:
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
            
            # Formatação do cabeçalho
            workbook = writer.book
            worksheet = writer.sheets['MAPA_RET']
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df_mapa.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Aba ENTRADAS_AC (Exemplo: CFOPs de entrada para crédito em MG)
        if not df_xe.empty:
            df_entradas_ac = df_xe[df_xe['CFOP'].astype(str).str.startswith(('1', '2'))].copy()
            df_entradas_ac.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

        st.success("Módulo RET finalizado com sucesso!")

    except Exception as e:
        st.error(f"Erro crítico no Motor RET: {str(e)}")
        # Cria aba de erro para não interromper o download do Excel completo
        pd.DataFrame({"Erro": [str(e)], "Causa": ["Provável formato de arquivo ou coluna ausente"]}).to_excel(writer, sheet_name='ERRO_MOTOR_RET')
