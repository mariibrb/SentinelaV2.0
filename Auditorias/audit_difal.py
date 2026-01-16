import pandas as pd

# Tabela de Alíquotas Internas Atualizada (Base 2025/2026)
ALIQUOTAS_INTERNAS = {
    'AC': 19.0, 'AL': 19.0, 'AM': 20.0, 'AP': 18.0, 'BA': 20.5, 'CE': 20.0, 'DF': 20.0, 'ES': 17.0,
    'GO': 19.0, 'MA': 22.0, 'MG': 18.0, 'MS': 17.0, 'MT': 17.0, 'PA': 19.0, 'PB': 20.0, 'PE': 20.5,
    'PI': 21.0, 'PR': 19.5, 'RJ': 22.0, 'RN': 20.0, 'RO': 17.5, 'RR': 20.0, 'RS': 18.0, 'SC': 17.0,
    'SE': 19.0, 'SP': 18.0, 'TO': 20.0
}

def processar_difal(df, writer):
    df_d = df.copy()

    def audit_difal_detalhada(r):
        # --- Dados do XML ---
        uf_orig = str(r.get('UF_EMIT', '')).strip().upper()
        uf_dest = str(r.get('UF_DEST', '')).strip().upper()
        bc_icms = float(r.get('BC-ICMS', 0.0))
        vlr_difal_xml = float(r.get('VAL-DIFAL', 0.0))
        alq_inter_xml = float(r.get('ALQ-ICMS', 0.0))
        
        # O indicador de Inscrição Estadual (9 = Não Contribuinte)
        # O Core precisa extrair essa tag, se não existir, usamos a lógica de UF
        ind_ie_dest = str(r.get('INDIEDEST', '1')).strip() 

        # --- TRAVA DE SEGURANÇA (O CORAÇÃO DA MUDANÇA) ---
        # Só há DIFAL se: For interestadual E Destinatário for Não Contribuinte (9)
        e_interestadual = (uf_orig != uf_dest) and (uf_orig != "") and (uf_dest != "")
        e_nao_contribuinte = (ind_ie_dest == '9')

        if not e_interestadual:
            return pd.Series([0.0, 0.0, "✅ N/A", "✅ OK", 0.0, "Nenhuma", "Operação Interna."])
        
        if not e_nao_contribuinte:
            return pd.Series([0.0, 0.0, "✅ N/A", "✅ OK", 0.0, "Nenhuma", "Destinatário Contribuinte (Isento de DIFAL EC 87/15)."])

        # --- Cálculos de Auditoria (Só chega aqui se for Não Contribuinte) ---
        alq_interna_dest = ALIQUOTAS_INTERNAS.get(uf_dest, 18.0)
        p_difal_esperado = max(0.0, alq_interna_dest - alq_inter_xml)
        vlr_difal_esperado = round(bc_icms * (p_difal_esperado / 100), 2)
        
        # --- DIAGNÓSTICOS ---
        status_destaque = "✅ OK"
        if vlr_difal_xml <= 0 and vlr_difal_esperado > 0.01:
            status_destaque = "❌ Falta Destaque DIFAL"

        dif_centavos = abs(vlr_difal_xml - vlr_difal_esperado)
        if dif_centavos < 0.11: 
            diag_difal = "✅ OK"
            vlr_comp = 0.0
        else:
            diag_difal = "❌ Erro"
            vlr_comp = max(0.0, round(vlr_difal_esperado - vlr_difal_xml, 2))

        # --- AÇÃO CORRETIVA ---
        acao = "Nenhuma"
        motivo = f"DIFAL em conformidade para consumidor final em {uf_dest}."

        if vlr_comp > 0:
            acao = "Gerar Guia GNRE / NF Complementar"
            motivo = f"Diferença de R$ {vlr_comp} para a UF {uf_dest}. Alíquota interna de {alq_interna_dest}%."
        elif status_destaque == "❌ Falta Destaque DIFAL":
            acao = "Emitir NF Complementar"
            motivo = f"Consumidor Final em {uf_dest} exige DIFAL."

        return pd.Series([
            alq_interna_dest, p_difal_esperado, status_destaque, 
            diag_difal, vlr_comp, acao, motivo
        ])

    # --- LISTA DE COLUNAS DE ANÁLISE ---
    analises_nomes = [
        'DIFAL_ALQ_INTERNA_DEST',
        'DIFAL_%_ESPERADO',
        'DIFAL_STATUS_DESTAQUE', 
        'DIFAL_DIAG_VALOR', 
        'DIFAL_VALOR_COMPLEMENTAR', 
        'DIFAL_AÇÃO_CORRETIVA', 
        'DIFAL_FUNDAMENTAÇÃO'
    ]
    
    df_d[analises_nomes] = df_d.apply(audit_difal_detalhada, axis=1)

    # --- REORGANIZAÇÃO ---
    df_final = df_d[df_d['UF_EMIT'] != df_d['UF_DEST']].copy()
    
    if not df_final.empty:
        cols_xml = [c for c in df_final.columns if c != 'Situação Nota' and c not in analises_nomes]
        col_status = ['Situação Nota'] if 'Situação Nota' in df_final.columns else []
        df_export = pd.concat([df_final[cols_xml], df_final[col_status], df_final[analises_nomes]], axis=1)
    else:
        df_export = pd.DataFrame(columns=list(df.columns) + analises_nomes)

    df_export.to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)
