import pandas as pd
import streamlit as st

def executar_motor_ret(writer, df_xs, df_xe, ge, gs, cod_cliente):
    """
    Motor de processamento exclusivo para empresas detentoras de RET em MG.
    Realiza o cruzamento entre XMLs e arquivos Gerenciais do cliente.
    """
    st.info("Iniciando processamento do Módulo RET (Minas Gerais)...")

    try:
        # 1. LEITURA DOS ARQUIVOS GERENCIAIS
        # Tentamos ler como CSV (padrão sistema), se falhar, tentamos Excel.
        def ler_gerencial(arquivo):
            if arquivo is None:
                return pd.DataFrame()
            try:
                arquivo.seek(0)
                # Geralmente gerenciais são CSV com delimitador ; ou ,
                return pd.read_csv(arquivo, sep=None, engine='python', encoding='latin1')
            except:
                arquivo.seek(0)
                return pd.read_excel(arquivo)

        df_ger_e = ler_gerencial(ge)
        df_ger_s = ler_gerencial(gs)

        # 2. PADRONIZAÇÃO E LIMPEZA (Conforme os títulos de coluna que você definiu)
        # Exemplo de tratamento nas chaves para garantir o cruzamento
        if not df_ger_s.empty:
            # Supondo que a coluna de chave no seu gerencial se chame 'Chave de Acesso' ou similar
            col_chave = [c for c in df_ger_s.columns if 'CHAVE' in str(c).upper()]
            if col_chave:
                df_ger_s[col_chave[0]] = df_ger_s[col_chave[0]].astype(str).str.replace(r'\D', '', regex=True)

        # 3. LÓGICA DE CRUZAMENTO (XML vs GERENCIAL)
        # Aqui entra a inteligência fiscal de MG
        # Exemplo: Identificar notas que estão no XML mas não no Gerencial
        if not df_xs.empty and not df_ger_s.empty:
            df_xs['CHAVE_ACESSO'] = df_xs['CHAVE_ACESSO'].astype(str).str.replace(r'\D', '', regex=True)
            
            # Merge para encontrar discrepâncias
            df_mapa = pd.merge(
                df_xs, 
                df_ger_s, 
                left_on='CHAVE_ACESSO', 
                right_on=col_chave[0] if col_chave else None, 
                how='left',
                suffixes=('_XML', '_GER')
            )
        else:
            df_mapa = df_xs.copy()

        # 4. CRIAÇÃO DAS ABAS ESPECÍFICAS NO EXCEL
        # Aba MAPA_RET
        if not df_mapa.empty:
            df_mapa.to_excel(writer, sheet_name='MAPA_RET', index=False)
            
            # Formatação básica da aba
            worksheet = writer.sheets['MAPA_RET']
            header_format = writer.book.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            for col_num, value in enumerate(df_mapa.columns.values):
                worksheet.write(0, col_num, value, header_format)

        # Aba ENTRADAS_AC (Entradas de Alíquota Cheia ou conforme regra de MG)
        if not df_xe.empty:
            # Filtrar apenas o que for relevante para o crédito de MG (ex: CFOPs iniciados em 1 ou 2)
            df_entradas_ac = df_xe[df_xe['CFOP'].astype(str).str.startswith(('1', '2'))].copy()
            df_entradas_ac.to_excel(writer, sheet_name='ENTRADAS_AC', index=False)

        st.success("Módulo RET finalizado com sucesso!")

    except Exception as e:
        st.error(f"Erro crítico no Motor RET: {str(e)}")
        # Em caso de erro, criamos uma aba de log para não quebrar o Excel final
        pd.DataFrame({"Erro": [str(e)]}).to_excel(writer, sheet_name='ERRO_MOTOR_RET')
