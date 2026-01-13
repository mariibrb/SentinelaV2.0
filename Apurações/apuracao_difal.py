import pandas as pd

UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df_saida, writer, df_entrada=None):
    # Garante que temos DataFrames válidos
    if df_entrada is None: df_entrada = pd.DataFrame()
    
    # --- UNIFICAÇÃO DOS DADOS PARA SOMAR DEVOLUÇÕES ---
    # Unimos os dois blocos para garantir que devoluções em qualquer pasta sejam vistas
    df_total = pd.concat([df_saida, df_entrada], ignore_index=True)
    
    # 1. FILTRO DE CANCELADAS (Só entra nota AUTORIZADA)
    if 'Situação Nota' in df_total.columns:
        df_total = df_total[df_total['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)]

    def preparar_tabela(tipo):
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        
        # 2. SEPARAÇÃO POR CFOP (A regra que você pediu)
        # Saídas: CFOP começa com 5, 6 ou 7
        # Entradas (Compras e Devoluções): CFOP começa com 1, 2 ou 3
        df_temp = df_total.copy()
        df_temp['PREFIXO'] = df_temp['CFOP'].astype(str).str.strip().str[0]
        
        if tipo == 'saida':
            df_filtro = df_temp[df_temp['PREFIXO'].isin(['5', '6', '7'])]
            col_uf = 'UF_DEST'
        else:
            df_filtro = df_temp[df_temp['PREFIXO'].isin(['1', '2', '3'])]
            col_uf = 'UF_EMIT' # Nas entradas, somamos pela UF de origem do fornecedor/devolução

        if df_filtro.empty:
            for c in ['VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']: base[c] = 0.0
            base['IE_SUBST'] = ""
            return base

        # 3. AGRUPAMENTO POR ESTADO
        agrupado = df_filtro.groupby([col_uf]).agg({
            'VAL-ICMS-ST': 'sum', 
            'VAL-DIFAL': 'sum', 
            'VAL-FCP-DEST': 'sum', 
            'VAL-FCP': 'sum', 
            'VAL-FCP-ST': 'sum'
        }).reset_index().rename(columns={col_uf: 'UF_DEST'})
        
        agrupado['DIFAL_CONSOLIDADO'] = agrupado['VAL-DIFAL'] + agrupado['VAL-FCP-DEST']
        
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # Mapeamento de IE Substituta (Para o destaque laranja)
        ie_map = df_filtro[df_filtro['IE_SUBST'] != ""].groupby(col_uf)['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("").astype(str)
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']]

    # Processamento Final
    res_s = preparar_tabela('saida')
    res_e = preparar_tabela('entrada')

    # SALDO (Saídas - Entradas)
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    for c_xml, c_fin in [('VAL-ICMS-ST', 'ST LÍQUIDO'), ('DIFAL_CONSOLIDADO', 'DIFAL LÍQUIDO'), ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')]:
        res_saldo[c_fin] = res_s[c_xml] - res_e[c_xml]

    # --- EXCEL (Mantendo a formatação laranja aprovada) ---
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)
    
    f_title = workbook.add_format({'bold': True, 'align': 'center', 'font_color': '#FF6F00', 'border': 1})
    f_head = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
    f_num = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    f_border = workbook.add_format({'border': 1})
    f_orange_num = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1, 'num_format': '#,##0.00'})
    f_orange_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1})
    f_total = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})

    heads = ['UF', 'IEST (SUBST)', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']

    for df_t, start_c, title in [(res_s, 0, "1. SAÍDAS"), (res_e, 7, "2. ENTRADAS"), (res_saldo, 14, "3. SALDO")]:
        worksheet.merge_range(0, start_c, 0, start_c + 5, title, f_title)
        for i, h in enumerate(heads): worksheet.write(2, start_c + i, h, f_head)
        
        for r_idx, row in enumerate(df_t.values):
            uf = str(row[0]).strip()
            tem_ie = res_s.loc[res_s['UF_DEST'] == uf, 'IE_SUBST'].values[0] != ""
            
            for c_idx, val in enumerate(row):
                fmt = f_orange_num if tem_ie and isinstance(val, (int, float)) else f_orange_fill if tem_ie else f_num if isinstance(val, (int, float)) else f_border
                if c_idx == 1: worksheet.write_string(r_idx + 3, start_c + c_idx, str(val), fmt)
                else: worksheet.write(r_idx + 3, start_c + c_idx, val, fmt)
        
        # Totais
        worksheet.write(30, start_c, "TOTAL GERAL", f_total)
        worksheet.write(30, start_c + 1, "", f_total)
        for i in range(2, 6):
            c_idx = start_c + i
            col_let = chr(65 + c_idx) if c_idx < 26 else f"A{chr(65 + c_idx - 26)}"
            worksheet.write(30, c_idx, f'=SUM({col_let}4:{col_let}30)', f_total)
