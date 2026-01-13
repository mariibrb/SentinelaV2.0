import pandas as pd
import numpy as np

UFS_BRASIL = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']

def gerar_resumo_uf(df_saida, writer, df_entrada=None):
    # Alterar somente o necessário: Subtrair FCP do DIFAL Consolidado para separar os valores
    if df_entrada is None: df_entrada = pd.DataFrame()
    
    df_total = pd.concat([df_saida, df_entrada], ignore_index=True)
    
    if 'Situação Nota' in df_total.columns:
        df_total = df_total[df_total['Situação Nota'].astype(str).str.upper().str.contains('AUTORIZAD', na=False)]

    def preparar_tabela(tipo):
        base = pd.DataFrame({'UF_DEST': UFS_BRASIL})
        df_temp = df_total.copy()
        df_temp['PREFIXO'] = df_temp['CFOP'].astype(str).str.strip().str[0]
        
        if tipo == 'saida':
            df_filtro = df_temp[df_temp['PREFIXO'].isin(['5', '6', '7'])]
            col_uf_final = 'UF_DEST'
        else:
            df_filtro = df_temp[df_temp['PREFIXO'].isin(['1', '2', '3'])]
            # Devolução Própria: Se Emitente SP, olha Destinatário
            df_filtro['UF_AGRUPAR'] = np.where(df_filtro['UF_EMIT'] == 'SP', df_filtro['UF_DEST'], df_filtro['UF_EMIT'])
            col_uf_final = 'UF_AGRUPAR'

        if df_filtro.empty:
            for c in ['VAL-ICMS-ST', 'DIFAL_PURO', 'VAL-FCP-DEST', 'VAL-FCP-ST']: base[c] = 0.0
            base['IE_SUBST'] = ""
            return base

        # Agrupamento somando os valores brutos vindo do Core
        agrupado = df_filtro.groupby([col_uf_final]).agg({
            'VAL-ICMS-ST': 'sum', 
            'VAL-DIFAL': 'sum',      # Valor Consolidado (DIFAL + FCP)
            'VAL-FCP-DEST': 'sum',   # Valor do FCP isolado
            'VAL-FCP-ST': 'sum'
        }).reset_index().rename(columns={col_uf_final: 'UF_DEST'})
        
        # --- LÓGICA DE SUBTRAÇÃO SOLICITADA ---
        # Criamos o DIFAL_PURO subtraindo o FCP do valor consolidado
        agrupado['DIFAL_PURO'] = agrupado['VAL-DIFAL'] - agrupado['VAL-FCP-DEST']
        
        final = pd.merge(base, agrupado, on='UF_DEST', how='left').fillna(0)
        
        # IE para destaque laranja e regra de saldo
        ie_map = df_filtro[df_filtro['IE_SUBST'] != ""].groupby(col_uf_final)['IE_SUBST'].first().to_dict()
        final['IE_SUBST'] = final['UF_DEST'].map(ie_map).fillna("").astype(str)
        
        return final[['UF_DEST', 'IE_SUBST', 'VAL-ICMS-ST', 'DIFAL_PURO', 'VAL-FCP-DEST', 'VAL-FCP-ST']]

    res_s = preparar_tabela('saida')
    res_e = preparar_tabela('entrada')

    # SALDO (Aplica a regra de IEST: só abate entrada se tiver inscrição no estado)
    res_saldo = pd.DataFrame({'UF': UFS_BRASIL})
    res_saldo['IE_SUBST'] = res_s['IE_SUBST']
    
    tem_ie_mask = res_s['IE_SUBST'] != ""
    
    colunas_finais = [
        ('VAL-ICMS-ST', 'ST LÍQUIDO'), 
        ('DIFAL_PURO', 'DIFAL LÍQUIDO'), 
        ('VAL-FCP-DEST', 'FCP LÍQUIDO'), 
        ('VAL-FCP-ST', 'FCP-ST LÍQUIDO')
    ]

    for c_xml, c_fin in colunas_finais:
        # Se tem IE: Saída - Entrada | Se não tem IE: Apenas Saída
        res_saldo[c_fin] = np.where(tem_ie_mask, res_s[c_xml] - res_e
