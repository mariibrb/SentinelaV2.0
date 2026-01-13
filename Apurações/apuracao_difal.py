import pandas as pd

UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df_saida, writer, df_entrada=None):
    if df_entrada is None or df_entrada.empty:
        df_entrada = pd.DataFrame(columns=df_saida.columns)

    def preparar_tabela(df_origem, tipo):
        col_uf = 'UF_DEST' if tipo == 'saida' else 'UF_EMIT'
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        
        if df_origem.empty:
            for c in ['VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']: base[c] = 0.0
            base['IE_SUBST'] = ""
            return base

        # --- VALIDAÇÃO POR CFOP (O CORAÇÃO DO FILTRO) ---
        df_validado = df_origem.copy()
        # Garantimos que o CFOP seja string para pegar o primeiro dígito
        df_validado['CFOP_PREFIXO'] = df_validado['CFOP'].astype(str).str.strip().str[0]
        
        if tipo == 'saida':
            # Considera apenas operações de Saída (5, 6 e 7)
            df_validado = df_validado[df_validado['CFOP_PREFIXO'].isin(['5', '6', '7'])]
        else:
            # Considera apenas operações de Entrada (1, 2 e 3)
            df_validado = df_validado[df_validado['CFOP_PREFIXO'].isin(['1', '2', '3'])]

        # Agrupamento por UF (Isso reduz as 90 linhas para 27 UFs)
        agrupado = df_validado.groupby([col_uf]).agg({
            'VAL-ICMS-ST': 'sum', 
            'VAL-DIFAL': 'sum', 
            'VAL-FCP-DEST': 'sum', 
            'VAL-FCP': 'sum', 
            'VAL-FCP-ST': 'sum'
        }).reset_index().rename(columns={col_uf: 'UF_DEST'})
        
        agrupado['DIFAL_CONSOLIDADO'] = agrupado['VAL-DIFAL'] + agrupado['VAL-FCP-DEST']
        
        # Cruzamos com a lista de todos os estados (Base)
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # Busca a IE Substituta se existir
        ie_map = df_validado[df_validado['IE_SUBST'] != ""].groupby(col_uf)['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("").astype(str)
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']]

    # Processamento
    res_s = preparar_tabela(df_saida, 'saida')
    res_e = preparar_tabela(df_entrada, 'entrada')

    # Cálculo do Saldo Líquido
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    for c_xml, c_fin in [('VAL-ICMS-ST', 'ST LÍQUIDO'), ('DIFAL_CONSOLIDADO', 'DIFAL LÍQUIDO'), ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')]:
        res_saldo[c_fin] = res_s[c_xml] - res_e[c_xml]

    # --- ESCRITA NO EXCEL ---
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)
    
    # Formatações
    f_title = workbook.add_format({'bold': True, 'align': 'center', 'font_color': '#FF6F00', 'border': 1})
    f_head = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
    f_num = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    f_border = workbook.add_format({'border': 1})
    f_total = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})

    heads = ['UF', 'IEST (SUBST)', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']

    for df_t, start_c, title in [(res_s, 0, "1. SAÍDAS"), (res_e, 7, "2. ENTRADAS"), (res_saldo, 14, "3. SALDO")]:
        worksheet.merge_range(0, start_c, 0, start_c + 5, title, f_title)
        for i, h in enumerate(heads): worksheet.write(2, start_c + i, h, f_head)
        
        for r_idx, row in enumerate(df_t.values):
            for c_idx, val in enumerate(row):
                fmt = f_num if isinstance(val, (int, float)) else f_border
                worksheet.write(r_idx + 3, start_c + c_idx, val, fmt)
        
        # Totais no rodapé (Linha 31)
        for i in range(2, 6):
            c_idx = start_c + i
            col_let = chr(65 + c_idx) if c_idx < 26 else f"A{chr(65 + c_idx - 26)}"
            worksheet.write(30, c_idx, f'=SUM({col_let}4:{col_let}30)', f_total)
