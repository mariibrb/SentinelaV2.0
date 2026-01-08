import pandas as pd

# Lista oficial das 27 UFs do Brasil
UFS_BRASIL = [
    'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT',
    'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'
]

# ESTADOS HOMOLOGADOS PARA ABATIMENTO E COR LARANJA (Conforme image_b9b701.png)
UFS_COM_IE = ['BA', 'DF', 'ES', 'GO', 'MT', 'MS', 'MG', 'PR', 'PE', 'RJ', 'RS', 'SC', 'SP']

def gerar_resumo_uf(df, writer):
    if df.empty:
        return

    df_temp = df.copy()

    # 1. Filtro Rigoroso: Apenas Notas Autorizadas e Válidas (Ignora Cancelamentos)
    df_validas = df_temp[
        (df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)) &
        (~df_temp['Situação Nota'].astype(str).str.upper().str.contains('CANCEL', na=False))
    ].copy()

    # 2. Identificação de Sentido pelo CFOP
    def identificar_sentido(cfop):
        c = str(cfop).strip()[0]
        if c in ['1', '2', '3']: return 'ENTRADA'
        if c in ['5', '6', '7']: return 'SAÍDA'
        return 'OUTROS'

    df_validas['SENTIDO'] = df_validas['CFOP'].apply(identificar_sentido)

    # 3. Preparação das Tabelas (Garante 27 UFs alinhadas)
    def preparar_tabela_completa(dataframe_origem):
        agrupado = dataframe_origem.groupby(['UF_DEST']).agg({
            'VAL-ICMS-ST': 'sum', 'VAL-DIFAL': 'sum', 'VAL-FCP': 'sum', 'VAL-FCP-ST': 'sum'
        }).reset_index()
        base_completa = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        final = pd.merge(base_completa, agrupado, on='UF_DEST', how='left').fillna(0)
        ie_map = dataframe_origem.groupby('UF_DEST')['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("")
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'VAL-DIFAL', 'VAL-FCP', 'VAL-FCP-ST']]

    res_s = preparar_tabela_completa(df_validas[df_validas['SENTIDO'] == 'SAÍDA'])
    res_e = preparar_tabela_completa(df_validas[df_validas['SENTIDO'] == 'ENTRADA'])

    # 4. Cálculo do Saldo Líquido (Lógica de Abatimento restrita aos estados da lista)
    res_saldo = pd.DataFrame({'ESTADO (UF)': UFS_BRASIL})
    res_saldo['IE SUBSTITUTO'] = res_s['IE_SUBST']
    
    colunas_map = [
        ('VAL-ICMS-ST', 'ST LÍQUIDO'), ('VAL-DIFAL', 'DIFAL LÍQUIDO'), 
        ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')
    ]

    for col_xml, col_final in colunas_map:
        res_saldo[col_final] = res_saldo['ESTADO (UF)'].apply(
            lambda x: (res_s.loc[res_s['UF_DEST'] == x, col_xml].values[0] - res_e.loc[res_e['UF_DEST'] == x, col_xml].values[0])
            if x in UFS_COM_IE else res_s.loc[res_s['UF_DEST'] == x, col_xml].values[0]
        )

    # 5. Configuração do Excel (Lado a Lado, Sem Grades)
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)

    # Estilos de Célula
    title_fmt = workbook.add_format({'bold': True, 'font_color': '#FF6F00', 'font_size': 11})
    orange_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1}) 
    orange_num_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1, 'num_format': '#,##0.00'}) 
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0'})
    total_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})
    num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    border_fmt = workbook.add_format({'border': 1})

    # Definição das Tabelas
    headers_s = ['ESTADO (UF)', 'IE SUBSTITUTO', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
    headers_e = ['ESTADO (UF) ', 'IE SUBSTITUTO ', 'ST TOTAL ', 'DIFAL TOTAL ', 'FCP TOTAL ', 'FCP-ST TOTAL ']
    headers_sl = ['ESTADO (UF)  ', 'IE SUBSTITUTO  ', 'ST LÍQUIDO', 'DIFAL LÍQUIDO', 'FCP LÍQUIDO', 'FCP-ST LÍQUIDO']

    tables = [(res_s, 0, "1. SAÍDAS (DÉBITO)", headers_s), 
              (res_e, 7, "2. ENTRADAS (CRÉDITO)", headers_e), 
              (res_saldo, 14, "3. SALDO LÍQUIDO (RECOLHER)", headers_sl)]
    
    for df_t, start_col, title, h_list in tables:
        worksheet.write(0, start_col, title, title_fmt)
        for c_idx, h_name in enumerate(h_list):
            worksheet.write(2, start_col + c_idx, h_name, header_fmt)
        
        for r_idx, row_data in enumerate(df_t.values):
            uf_atual = str(row_data[0]).strip()
            for c_idx, value in enumerate(row_data):
                # Pinta a linha inteira se a UF estiver na lista homologada
                if uf_atual in UFS_COM_IE:
                    current_fmt = orange_num_fill if isinstance(value, (int, float)) else orange_fill
                else:
                    current_fmt = num_fmt if isinstance(value, (int, float)) else border_fmt
                
                worksheet.write(r_idx + 3, start_col + c_idx, value, current_fmt)

        # Totais Gerais
        worksheet.write(30, start_col, "TOTAL GERAL", total_fmt)
        worksheet.write(30, start_col + 1, "", total_fmt)
        for i in range(2, 6):
            c_pos = start_col + i
            c_let = chr(65 + c_pos) if c_pos < 26 else f"A{chr(65 + c_pos - 26)}"
            worksheet.write(30, c_pos, f'=SUM({c_let}4:{c_let}30)', total_fmt)
