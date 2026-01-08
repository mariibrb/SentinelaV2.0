import pandas as pd

# Lista oficial das 27 UFs do Brasil
UFS_BRASIL = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT',
    'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'
]

def gerar_resumo_uf(df, writer):
    """
    Gera a aba DIFAL_ST_FECP com três tabelas lado a lado:
    SAÍDAS | ENTRADAS | SALDO LÍQUIDO
    Filtra notas canceladas e preenche todos os estados com zero se necessário.
    """
    if df.empty:
        return

    df_temp = df.copy()

    # 1. Filtro de Notas Autorizadas
    df_aut = df_temp[
        df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)
    ].copy()

    # 2. Identificação de Sentido pelo CFOP
    def identificar_sentido(cfop):
        c = str(cfop).strip()[0]
        if c in ['1', '2', '3']: return 'ENTRADA'
        if c in ['5', '6', '7']: return 'SAÍDA'
        return 'OUTROS'

    df_aut['SENTIDO'] = df_aut['CFOP'].apply(identificar_sentido)

    # 3. Função para garantir todas as UFs
    def preparar_tabela_completa(dataframe_origem):
        agrupado = dataframe_origem.groupby(['UF_DEST']).agg({
            'VAL-ICMS-ST': 'sum', 'VAL-DIFAL': 'sum', 'VAL-FCP': 'sum', 'VAL-FCP-ST': 'sum'
        }).reset_index()
        
        base_completa = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        final = pd.merge(base_completa, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # Pega a primeira IE encontrada para a UF
        ie_map = dataframe_origem.groupby('UF_DEST')['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("")
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'VAL-DIFAL', 'VAL-FCP', 'VAL-FCP-ST']]

    # 4. Processamento dos blocos
    df_s = df_aut[df_aut['SENTIDO'] == 'SAÍDA']
    df_e = df_aut[df_aut['SENTIDO'] == 'ENTRADA']

    res_s = preparar_tabela_completa(df_s)
    res_e = preparar_tabela_completa(df_e)

    # 5. Cálculo da Tabela de Saldo (Líquido)
    res_saldo = pd.DataFrame({'ESTADO (UF)': UFS_BRASIL})
    res_saldo['IE SUBSTITUTO'] = res_s['IE_SUBST']
    res_saldo['ST LÍQUIDO'] = res_s['VAL-ICMS-ST'] - res_e['VAL-ICMS-ST']
    res_saldo['DIFAL LÍQUIDO'] = res_s['VAL-DIFAL'] - res_e['VAL-DIFAL']
    res_saldo['FCP LÍQUIDO'] = res_s['VAL-FCP'] - res_e['VAL-FCP']
    res_saldo['FCP-ST LÍQUIDO'] = res_s['VAL-FCP-ST'] - res_e['VAL-FCP-ST']

    # Renomeando colunas dos blocos anteriores para gravação
    res_s.columns = ['ESTADO (UF)', 'IE SUBSTITUTO', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
    res_e.columns = ['ESTADO (UF) ', 'IE SUBSTITUTO ', 'ST TOTAL ', 'DIFAL TOTAL ', 'FCP TOTAL ', 'FCP-ST TOTAL ']

    # 6. Gravação Física Lado a Lado
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet

    # Formatação
    title_fmt = workbook.add_format({'bold': True, 'font_color': '#FF6F00', 'font_size': 12})
    
    # Escrevendo Títulos
    worksheet.write(0, 0, "1. SAÍDAS (DÉBITO)", title_fmt)
    worksheet.write(0, 8, "2. ENTRADAS (CRÉDITO)", title_fmt)
    worksheet.write(0, 16, "3. SALDO LÍQUIDO (A RECOLHER)", title_fmt)

    # Gravando as 3 Tabelas
    res_s.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=0, index=False)
    res_e.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=8, index=False)
    res_saldo.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=16, index=False)
