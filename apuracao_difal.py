import pandas as pd

UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df, writer):
    if df.empty: return
    
    df_temp = df.copy()
    
    # 1. Filtro rigoroso: Somente notas autorizadas e não canceladas
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

    # 3. Preparação das Tabelas
    def preparar_tabela(df_origem):
        agrupado = df_origem.groupby(['UF_DEST']).agg({
            'VAL-ICMS-ST': 'sum', 
            'VAL-DIFAL': 'sum', 
            'VAL-FCP-DEST': 'sum',
            'VAL-FCP': 'sum', 
            'VAL-FCP-ST': 'sum'
        }).reset_index()
        
        agrupado['DIFAL_CONSOLIDADO'] = agrupado['VAL-DIFAL'] + agrupado['VAL-FCP-DEST']
        
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # Captura Dinâmica da IE de Substituto na UF
        ie_map = df_origem[df_origem['IE_SUBST'] != ""].groupby('UF_DEST')['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("")
        
        return final

    res_s = preparar_tabela(df_validas[df_validas['SENTIDO'] == 'SAÍDA'])
    res_e = preparar_tabela(df_validas[df_validas['SENTIDO'] == 'ENTRADA'])

    # 4. Cálculo do Saldo (Só abate se tiver IE na Saída)
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    
    cols_calc = [
        ('VAL-ICMS-ST', 'ST LÍQUIDO'), ('DIFAL_CONSOLIDADO', 'DIFAL LÍQUIDO'), 
        ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')
    ]
    
    for c_xml, c_fin in cols_calc:
        res_saldo[c_fin] = res_saldo['UF'].apply(
            lambda x: (res_s.loc[res_s['UF_DEST']==x, c_xml].values[0] - res_e.loc[res_e['UF_DEST']==x, c_xml].values[0])
            if res_s.loc[res_s['UF_DEST']==x, 'IE_SUBST'].values[0] != "" else res_s.loc[res_s['UF_DEST']==x, c_xml].values[0]
        )

    # 5. Gravação e Formatação Excel (XlsxWriter)
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)

    # Formatos
    title_fmt = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_color': '#FF6F00', 'font_size': 12, 'border': 1})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
    num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    border_fmt = workbook.add_format({'border': 1})
    
    # Formatos Dinâmicos de Laranja (Para quem tem IE)
    orange_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1})
    orange_num = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1, 'num_format': '#,##0.00'})
    
    total_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})

    # Cabeçalhos
    h_v = ['UF', 'IE SUBST', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']
    h_l = ['UF', 'IE SUBST', 'ST LÍQUIDO', 'DIFAL LÍQUIDO', 'FCP LÍQUIDO', 'FCP-ST LÍQUIDO']

    for df_t, start_c, title, heads in [(res_s, 0, "1. SAÍDAS", h_v), (res_e, 7, "2. ENTRADAS", h_v), (res_saldo, 14, "3. SALDO", h_l)]:
        # MESCLAR TÍTULOS (Passo solicitado)
        worksheet.merge_range(0, start_c, 0, start_c + 5, title, title_fmt)
        
        # Cabeçalhos das Colunas
        for i, h in enumerate(heads):
            worksheet.write(2, start_c + i, h, header_fmt)
        
        # Preenchimento de Dados com Cor Dinâmica (Passo solicitado)
        for r_idx, row in enumerate(df_t.values):
            uf = str(row[0]).strip()
            # Pinta se houver IE na aba de Saídas para aquela UF
            tem_ie = res_s.loc[res_s['UF_DEST'] == uf, 'IE_SUBST'].values[0] != ""
            
            for c_idx, val in enumerate(row):
                if tem_ie:
                    fmt = orange_num if isinstance(val, (int, float)) else orange_fill
                else:
                    fmt = num_fmt if isinstance(val, (int, float)) else border_fmt
                worksheet.write(r_idx + 3, start_c + c_idx, val, fmt)

        # Totais Gerais
        worksheet.write(30, start_c, "TOTAL GERAL", total_fmt)
        worksheet.write(30, start_c + 1, "", total_fmt)
        for i in range(2, 6):
            let = chr(65 + start_c + i) if (start_c + i) < 26 else f"A{chr(65 + start_c + i - 26)}"
            worksheet.write(30, start_c + i, f'=SUM({let}4:{let}30)', total_fmt)
