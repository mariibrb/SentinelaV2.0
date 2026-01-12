import pandas as pd

# Tabela de Alíquotas Internas (Base 2025/2026)
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
        uf_orig = str(r.get('UF_EMIT', ''))
        uf_dest = str(r.get('UF_DEST', ''))
        ind_ie = str(r.get('indIEDest', '9')) # 9 = Não Contribuinte
        bc_icms = float(r.get('BC-ICMS', 0.0))
        vlr_difal_xml = float(r.get('VAL-DIFAL', 0.0))
        alq_inter_xml = float(r.get('ALQ-ICMS', 0.0))
        
        # --- Regra de Aplicabilidade ---
        # Só há DIFAL Consumidor Final se: Interestadual E Destinatário Não Contribuinte
        obrigatorio = (uf_orig != uf_dest) and (ind_ie == '9')

        if not obrigatorio:
            return pd.Series(["✅ N/A", "✅ OK", 0.0, "Nenhuma", "Operação interna ou com contribuinte."])

        # --- Cálculos de Auditoria ---
        alq_interna_dest = ALIQUOTAS_INTERNAS.get(uf_dest, 18.0)
        p_difal = max(0.0, alq_interna_dest - alq_inter_xml)
        vlr_difal_esperado = round(bc_icms * (p_difal / 100), 2)
        
        # --- Diagnóstico de Destaque ---
        if obrigatorio and vlr_difal_xml <= 0 and vlr_difal_esperado > 0:
            status_destaque = "❌ Falta Destaque DIFAL"
        else:
            status_destaque = "✅ OK"

        # --- Diagnóstico de Valor ---
        dif_centavos = abs(vlr_difal_xml - vlr_difal_esperado)
        if dif_centavos < 0.10:
            diag_difal = "✅ OK"
            vlr_comp = 0.0
        else:
            diag_difal = f"❌ Erro (XML: R$ {vlr_difal_xml} | Esp: R$ {vlr_difal_esperado})"
            vlr_comp = max(0.0, round(vlr_difal_esperado - vlr_difal_xml, 2))

        # --- Ação Corretiva ---
        acao = "Nenhuma"
        if status_destaque == "❌ Falta Destaque DIFAL" or vlr_comp > 0:
            acao = "Emitir NF Complementar / Guia"
            motivo = f"A UF {uf_dest} exige DIFAL de {p_difal}% nesta operação."
        elif vlr_difal_xml > vlr_difal_esperado:
            acao = "Avaliar Restituição"
            motivo = "Valor destacado no XML é superior ao cálculo legal."
        else:
            motivo = "DIFAL em conformidade."

        return pd.Series([status_destaque, diag_difal, vlr_comp, acao, motivo])

    # Colunas de Análise pós AG
    analises = [
        'DIFAL_STATUS_DESTAQUE', 
        'DIFAL_DIAG_VALOR', 
        'DIFAL_VALOR_COMPLEMENTAR', 
        'DIFAL_AÇÃO_CORRETIVA', 
        'DIFAL_FUNDAMENTAÇÃO'
    ]
    
    df_d[analises] = df_d.apply(audit_difal_detalhada, axis=1)

    # Reorganização Final
    cols_xml = [c for c in df_d.columns if c not in analises and c != 'Situação Nota']
    df_final = df_d[cols_xml + ['Situação Nota'] + analises]

    df_final.to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)
