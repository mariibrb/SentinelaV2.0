import pandas as pd

# Lista padrão de UFs
UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df, writer):
    if df.empty: return
    df_temp = df.copy()
    
    # 1. Filtro: Notas autorizadas
    df_validas = df_temp[
        (df_temp['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)) &
        (~df_temp['Situação Nota'].astype(str).str.upper().str.contains('CANCEL', na=False))
    ].copy()

    # 2. Sentido da Operação
    df_validas['SENTIDO'] = df_validas['CFOP'].apply(lambda x: 'ENTRADA' if str(x)[0] in ['1','2','3'] else 'SAÍDA')

    # 3. Preparação das Tabelas (IEST)
    def preparar_tabela(df_origem):
        agrupado = df_origem.groupby(['UF_DEST']).agg({
            'VAL-ICMS-ST': 'sum', 'VAL-DIFAL': 'sum', 'VAL-FCP-DEST': 'sum', 'VAL-FCP': 'sum', 'VAL-FCP-ST': 'sum'
        }).reset_index()
        
        agrupado['DIFAL_CONSOLIDADO'] = agrupado['VAL-DIFAL'] + agrupado['VAL-FCP-DEST']
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # MAPEAMENTO DA IE (Coluna B)
        ie_map = df_origem[df_origem['IE_SUBST'] != ""].groupby('UF_DEST')['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("").astype(str)
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']]

    res_s = preparar_tabela(df_validas[df_validas['SENTIDO'] == 'SAÍDA'])
    res_e = preparar_tabela(df_validas[df_validas['SENTIDO'] == 'ENTRADA'])

    # 4. Cálculo do Saldo Líquido (Regra da IE)
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    
    campos = [('VAL-ICMS-ST', 'ST LÍQUIDO'), ('DIFAL_CONSOLIDADO', 'DIFAL LÍQUIDO'), ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')]
    
    for c_xml, c_fin in campos:
        res_saldo[c_fin] = res_saldo['UF'].apply(
            lambda x: (res_s.loc[res_s['UF_DEST']==x, c_xml].values[0] - res_e.loc[res_e['UF_DEST']==x, c_xml].values[0])
            if res_s.loc[res_s['UF_DEST']==x, 'IE_SUBST'].values[0] != "" else res_s.loc[res_s['UF_DEST']==x, c_xml].values[0]
        )

    # 5. Escrita no Excel
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)

    # Formatos
    title_fmt = workbook.add_format({'bold': True, 'align': 'center', 'font_color': '#FF6F00', 'font_size': 12, 'border': 1})
    header_fmt = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
    num_fmt = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    border_fmt = workbook.add_format({'border': 1})
    orange_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1})
    orange_num = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1, 'num_format': '#,##0.00'})
    total_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})

    heads = ['UF', 'IEST (SUBST)', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']

    for df_t, start_c, title in [(res_s, 0, "1. SAÍDAS"), (res_e, 7, "2. ENTRADAS"), (res_saldo, 14, "3. SALDO")]:
        worksheet.merge_range(0, start_c, 0, start_c + 5, title, title_fmt)
        for i, h in enumerate(heads): worksheet.write(2, start_c + i, h, header_fmt)
        
        for r_idx, row in enumerate(df_t.values):
            tem_ie = res_s.loc[res_s['UF_DEST'] == str(row[0]), 'IE_SUBST'].values[0] != ""
            for c_idx, val in enumerate(row):
                fmt = orange_num if tem_ie and isinstance(val, (int, float)) else \
                      orange_fill if tem_ie else \
                      num_fmt if isinstance(val, (int, float)) else border_fmt
                
                if c_idx == 1:
                    worksheet.write_string(r_idx + 3, start_c + c_idx, str(val), fmt)
                else:
                    worksheet.write(r_idx + 3, start_c + c_idx, val, fmt)
