import pandas as pd

UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df_saida, writer, df_entrada=None):
    # Alterar somente o que foi solicitado, mantendo o restante igual.
    if df_entrada is None or df_entrada.empty:
        df_entrada = pd.DataFrame(columns=df_saida.columns)

    def preparar_tabela(df_origem, tipo):
        col_uf = 'UF_DEST' if tipo == 'saida' else 'UF_EMIT'
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        
        if df_origem.empty:
            for c in ['VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']: base[c] = 0.0
            base['IE_SUBST'] = ""
            return base

        # Validação de CFOP para garantir que são entradas/saídas comerciais
        df_validado = df_origem.copy()
        df_validado['CFOP_PREFIXO'] = df_validado['CFOP'].astype(str).str.strip().str[0]
        
        if tipo == 'saida':
            df_validado = df_validado[df_validado['CFOP_PREFIXO'].isin(['5', '6', '7'])]
        else:
            df_validado = df_validado[df_validado['CFOP_PREFIXO'].isin(['1', '2', '3'])]

        # Agrupamento somando os valores
        agrupado = df_validado.groupby([col_uf]).agg({
            'VAL-ICMS-ST': 'sum', 
            'VAL-DIFAL': 'sum', 
            'VAL-FCP-DEST': 'sum', 
            'VAL-FCP': 'sum', 
            'VAL-FCP-ST': 'sum'
        }).reset_index().rename(columns={col_uf: 'UF_DEST'})
        
        # Consolidação do DIFAL + FCP conforme solicitado anteriormente
        agrupado['DIFAL_CONSOLIDADO'] = agrupado['VAL-DIFAL'] + agrupado['VAL-FCP-DEST']
        
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # Mapeamento da IE Substituta
        ie_map = df_validado[df_validado['IE_SUBST'] != ""].groupby(col_uf)['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("").astype(str)
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'DIFAL_CONSOLIDADO', 'VAL-FCP', 'VAL-FCP-ST']]

    # Processamento das tabelas
    res_s = preparar_tabela(df_saida, 'saida')
    res_e = preparar_tabela(df_entrada, 'entrada')

    # Cálculo do Saldo Líquido (Abatendo Entradas das Saídas)
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    for c_xml, c_fin in [('VAL-ICMS-ST', 'ST LÍQUIDO'), ('DIFAL_CONSOLIDADO', 'DIFAL LÍQUIDO'), ('VAL-FCP', 'FCP LÍQUIDO'), ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')]:
        res_saldo[c_fin] = res_s[c_xml] - res_e[c_xml]

    # --- GRAVAÇÃO EXCEL COM FORMATAÇÃO ---
    workbook = writer.book
    worksheet = workbook.add_worksheet('DIFAL_ST_FECP')
    writer.sheets['DIFAL_ST_FECP'] = worksheet
    worksheet.hide_gridlines(2)
    
    # Definição dos Formatos (Mantendo o padrão laranja para IEs)
    f_title = workbook.add_format({'bold': True, 'align': 'center', 'font_color': '#FF6F00', 'border': 1})
    f_head = workbook.add_format({'bold': True, 'border': 1, 'bg_color': '#E0E0E0', 'align': 'center'})
    f_num = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
    f_border = workbook.add_format({'border': 1})
    f_orange_num = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1, 'num_format': '#,##0.00'})
    f_orange_fill = workbook.add_format({'bg_color': '#FFDAB9', 'border': 1})
    f_total = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'num_format': '#,##0.00'})

    heads = ['UF', 'IEST (SUBST)', 'ST TOTAL', 'DIFAL TOTAL', 'FCP TOTAL', 'FCP-ST TOTAL']

    # Gerar as 3 tabelas Lado a Lado
    for df_t, start_c, title in [(res_s, 0, "1. SAÍDAS"), (res_e, 7, "2. ENTRADAS"), (res_saldo, 14, "3. SALDO")]:
        worksheet.merge_range(0, start_c, 0, start_c + 5, title, f_title)
        for i, h in enumerate(heads): worksheet.write(2, start_c + i, h, f_head)
        
        for r_idx, row in enumerate(df_t.values):
            uf = str(row[0]).strip()
            # Valida se o estado possui IE para aplicar a cor laranja
            tem_ie = res_s.loc[res_s['UF_DEST'] == uf, 'IE_SUBST'].values[0] != ""
            
            for c_idx, val in enumerate(row):
                # Escolha do formato baseado na IE
                if tem_ie:
                    fmt = f_orange_num if isinstance(val, (int, float)) else f_orange_fill
                else:
                    fmt = f_num if isinstance(val, (int, float)) else f_border
                
                if c_idx == 1: # Coluna da IE
                    worksheet.write_string(r_idx + 3, start_c + c_idx, str(val), fmt)
                else:
                    worksheet.write(r_idx + 3, start_c + c_idx, val, fmt)
        
        # Totais Gerais
        worksheet.write(30, start_c, "TOTAL GERAL", f_total)
        worksheet.write(30, start_c + 1, "", f_total)
        for i in range(2, 6):
            c_idx = start_c + i
            col_let = chr(65 + c_idx) if c_idx < 26 else f"A{chr(65 + c_idx - 26)}"
            worksheet.write(30, c_idx, f'=SUM({col_let}4:{col_let}30)', f_total)
