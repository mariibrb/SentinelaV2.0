import pandas as pd

def gerar_resumo_uf(df, writer):
    """
    Gera a aba DIFAL_ST_FECP com tabelas de Saída e Entrada lado a lado,
    alinhadas pela UF.
    """
    if df.empty:
        return

    df_temp = df.copy()

    # 1. Filtro de Notas Autorizadas
    df_aut = df_temp[
        df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)
    ].copy()

    if df_aut.empty:
        pd.DataFrame([["Aviso:", "Nenhuma nota AUTORIZADA encontrada."]]).to_excel(writer, sheet_name='DIFAL_ST_FECP', index=False, header=False)
        return

    # 2. Identificação de Sentido pelo CFOP
    def identificar_sentido(cfop):
        c = str(cfop).strip()[0]
        if c in ['1', '2', '3']: return 'ENTRADA'
        if c in ['5', '6', '7']: return 'SAÍDA'
        return 'OUTROS'

    df_aut['SENTIDO'] = df_aut['CFOP'].apply(identificar_sentido)

    # 3. Função de Agrupamento
    def agrupar_dados(dataframe):
        return dataframe.groupby(['UF_DEST', 'IE_SUBST']).agg({
            'VAL-ICMS-ST': 'sum',
            'VAL-DIFAL': 'sum',
            'VAL-FCP': 'sum',
            'VAL-FCP-ST': 'sum'
        }).reset_index()

    # 4. Preparação das Tabelas Lado a Lado
    df_s = df_aut[df_aut['SENTIDO'] == 'SAÍDA']
    df_e = df_aut[df_aut['SENTIDO'] == 'ENTRADA']

    res_s = agrupar_dados(df_s) if not df_s.empty else pd.DataFrame(columns=['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'VAL-DIFAL', 'VAL-FCP', 'VAL-FCP-ST'])
    res_e = agrupar_dados(df_e) if not df_e.empty else pd.DataFrame(columns=['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'VAL-DIFAL', 'VAL-FCP', 'VAL-FCP-ST'])

    # Renomeando colunas para evitar colisão e alinhar no Excel
    res_s.columns = ['ESTADO (UF)', 'IE SUBSTITUTO', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
    res_e.columns = ['ESTADO (UF) ', 'IE SUBSTITUTO ', 'ST TOTAL ', 'DIFAL TOTAL ', 'FCP TOTAL ', 'FCP-ST TOTAL ']

    # 5. Gravação manual para garantir o posicionamento exato (Lado a Lado)
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet

    # Formatação de Títulos (Laranja conforme imagem)
    title_fmt = workbook.add_format({'bold': True, 'font_color': '#FF6F00', 'font_size': 12})

    # Escrevendo Títulos das Seções
    worksheet.write(0, 0, "RESUMO DE SAÍDAS (VENDAS)", title_fmt)
    worksheet.write(0, 8, "RESUMO DE ENTRADAS (DEVOLUÇÕES/COMPRAS)", title_fmt)

    # Gravando tabela de Saídas (Inicia na Coluna A)
    res_s.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=0, index=False)

    # Gravando tabela de Entradas (Inicia na Coluna I - deixando G e H vazias para respiro)
    res_e.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=8, index=False)
