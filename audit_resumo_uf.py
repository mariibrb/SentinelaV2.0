import pandas as pd

# Lista oficial das 27 UFs do Brasil
UFS_BRASIL = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT',
    'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'
]

# Estados que possuem IE Substituto (Laranja) conforme sua imagem
UFS_COM_IE = ['AP', 'BA', 'CE', 'ES', 'MG', 'MT', 'PA', 'PB', 'PE', 'PR', 'RJ', 'RN', 'RS', 'SC']

def gerar_resumo_uf(df, writer):
    if df.empty:
        return

    df_temp = df.copy()

    # 1. Filtro Rigoroso: Apenas Notas Autorizadas e Válidas (Ignora Cancelamento de NF-e homologado)
    df_validas = df_temp[
        (df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)) &
        (~df_temp['Situação Nota'].astype(str).str.upper().str.contains('CANCEL', na=False))
    ].copy()

    # 2. Identificação de Sentido (CFOP)
    def identificar_sentido(cfop):
        c = str(cfop).strip()[0]
        if c in ['1', '2', '3']: return 'ENTRADA'
        if c in ['5', '6', '7']: return 'SAÍDA'
        return 'OUTROS'

    df_validas['SENTIDO'] = df_validas['CFOP'].apply(identificar_sentido)

    # 3. Função para preparar tabela completa (27 UFs)
    def preparar_tabela_completa(dataframe_origem):
        agrupado = dataframe_origem.groupby(['UF_DEST']).agg({
            'VAL-ICMS-ST': 'sum', 'VAL-DIFAL': 'sum', 'VAL-FCP': 'sum', 'VAL-FCP-ST': 'sum'
        }).reset_index()
        
        base_completa = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        final = pd.merge(base_completa, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # IE de Substituto
        ie_map = dataframe_origem.groupby('UF_DEST')['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("")
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'VAL-DIFAL', 'VAL-FCP', 'VAL-FCP-ST']]

    res_s = preparar_tabela_completa(df_validas[df_validas['SENTIDO'] == 'SAÍDA'])
    res_e = preparar_tabela_completa(df_validas[df_validas['SENTIDO'] == 'ENTRADA'])

    # 4. Cálculo do Saldo Líquido com Lógica de Abatimento Condicional
    res_saldo = pd.DataFrame({'ESTADO (UF)': UFS_BRASIL})
    res_saldo['IE SUBSTITUTO'] = res_s['IE_SUBST']

    # Lógica solicitada: Abate devolução apenas se for estado com IE (Laranja)
    for col_xml, col_final in [('VAL-ICMS-ST', 'ST LÍQUIDO'), ('VAL-DIFAL', 'DIFAL LÍQUIDO'), 
                               ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')]:
        
        # Se UF está na lista laranja, faz Saída - Entrada. Senão, mantém apenas Saída.
        res_saldo[col_final] = res_saldo['ESTADO (UF)'].apply(
            lambda x: (res_s.loc[res_s['UF_DEST'] == x, col_xml].values[0] - res_e.loc[res_e['UF_DEST'] == x, col_xml].values[0])
            if x in UFS_COM_IE else res_s.loc[res_s['UF_DEST'] == x, col_xml].values[0]
        )

    # 5. Gravação e Formatação
    res_s.columns = ['ESTADO (UF)', 'IE SUBSTITUTO', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
    res_e.columns = ['ESTADO (UF) ', 'IE SUBSTITUTO ', 'ST TOTAL ', 'DIFAL TOTAL ', 'FCP TOTAL ', 'FCP-ST TOTAL ']

    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet

    # Formatos
    title_fmt = workbook.add_format({'bold': True, 'font_color': '#FF6F00', 'font_size': 12})
    orange_row = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1}) # Laranja claro
    total_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'num_format': '#,##0.00'})

    # Títulos
    worksheet.write(0, 0, "1. SAÍDAS (DÉBITO)", title_fmt)
    worksheet.write(0, 8, "2. ENTRADAS (CRÉDITO)", title_fmt)
    worksheet.write(0, 16, "3. SALDO LÍQUIDO (RECOLHER)", title_fmt)

    # Escrever tabelas
    res_s.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=0, index=False)
    res_e.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=8, index=False)
    res_saldo.to_excel(writer, sheet_name='DIFAL_ST_FECP', startrow=2, startcol=16, index=False)

    # Aplicar Destaque Laranja nas linhas de estados com IE
    for row_num, uf in enumerate(UFS_BRASIL):
        if uf in UFS_COM_IE:
            # Aplica o formato laranja nas 3 tabelas
            worksheet.set_row(row_num + 3, None, orange_row)

    # Totais Gerais no Rodapé
    for col_set in [0, 8, 16]:
        worksheet.write(30, col_set, "TOTAL GERAL", total_fmt)
        for i in range(2, 6):
            col_idx = col_set + i
            col_letter = chr(65 + col_idx) if col_idx < 26 else f"A{chr(65 + col_idx - 26)}"
            worksheet.write(30, col_idx, f'=SUM({col_letter}4:{col_letter}30)', total_fmt)
