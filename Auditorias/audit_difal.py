import pandas as pd

# Tabela de Alíquotas Internas Atualizada (Base 2025/2026)
# Importante: Muitos estados subiram para 19% e 20% recentemente
ALIQUOTAS_INTERNAS = {
    'AC': 19.0, 'AL': 19.0, 'AM': 20.0, 'AP': 18.0, 'BA': 20.5, 'CE': 20.0, 'DF': 20.0, 'ES': 17.0,
    'GO': 19.0, 'MA': 22.0, 'MG': 18.0, 'MS': 17.0, 'MT': 17.0, 'PA': 19.0, 'PB': 20.0, 'PE': 20.5,
    'PI': 21.0, 'PR': 19.5, 'RJ': 22.0, 'RN': 20.0, 'RO': 17.5, 'RR': 20.0, 'RS': 18.0, 'SC': 17.0,
    'SE': 19.0, 'SP': 18.0, 'TO': 20.0
}

def processar_difal(df, writer):
    df_d = df.copy()

    def audit_difal_detalhada(r):
        # --- Dados do XML (Conectando com as chaves do Core) ---
        uf_orig = str(r.get('UF_EMIT', '')).strip()
        uf_dest = str(r.get('UF_DEST', '')).strip()
        bc_icms = float(r.get('BC-ICMS', 0.0))
        vlr_difal_xml = float(r.get('VAL-DIFAL', 0.0))    # Já inclui FCP Destino no Core
        vlr_fcp_dest = float(r.get('VAL-FCP-DEST', 0.0))
        alq_inter_xml = float(r.get('ALQ-ICMS', 0.0))
        
        # Identifica se é consumidor final (indIEDest != 1)
        # O Core extrai isso se mapeado, senão assumimos pela UF_ORIG != UF_DEST
        obrigatorio = (uf_orig != uf_dest)

        if not obrigatorio:
            return pd.Series([0.0, 0.0, "✅ N/A", "✅ OK", 0.0, "Nenhuma", "Operação Interna."])

        # --- Cálculos de Auditoria (O Cérebro do DIFAL) ---
        alq_interna_dest = ALIQUOTAS_INTERNAS.get(uf_dest, 18.0)
        
        # O DIFAL é a diferença entre a interna do destino e a interestadual da origem
        p_difal_esperado = max(0.0, alq_interna_dest - alq_inter_xml)
        
        # Valor Esperado = BC * %DIFAL
        vlr_difal_esperado = round(bc_icms * (p_difal_esperado / 100), 2)
        
        # --- DIAGNÓSTICOS ---
        
        # 1. Status de Destaque
        status_destaque = "✅ OK"
        if vlr_difal_xml <= 0 and vlr_difal_esperado > 0.01:
            status_destaque = "❌ Falta Destaque DIFAL"

        # 2. Diagnóstico de Valor
        dif_centavos = abs(vlr_difal_xml - vlr_difal_esperado)
        if dif_centavos < 0.11: # Tolerância para arredondamento de centavos
            diag_difal = "✅ OK"
            vlr_comp = 0.0
        else:
            diag_difal = f"❌ Erro"
            vlr_comp = max(0.0, round(vlr_difal_esperado - vlr_difal_xml, 2))

        # --- AÇÃO CORRETIVA ---
        acao = "Nenhuma"
        motivo = f"DIFAL em conformidade para {uf_dest}."

        if vlr_comp > 0:
            acao = "Gerar Guia GNRE / NF Complementar"
            motivo = f"Diferença de R$ {vlr_comp} para a UF {uf_dest}. Alíquota interna de {alq_interna_dest}%."
        elif status_destaque == "❌ Falta Destaque DIFAL":
            acao = "Emitir NF Complementar"
            motivo = f"Operação interestadual para {uf_dest} exige destaque de DIFAL."

        return pd.Series([
            alq_interna_dest, p_difal_esperado, status_destaque, 
            diag_difal, vlr_comp, acao, motivo
        ])

    # --- LISTA DE COLUNAS DE ANÁLISE ---
    analises = [
        'DIFAL_ALQ_INTERNA_DEST',
        'DIFAL_%_ESPERADO',
        'DIFAL_STATUS_DESTAQUE', 
        'DIFAL_DIAG_VALOR', 
        'DIFAL_VALOR_COMPLEMENTAR', 
        'DIFAL_AÇÃO_CORRETIVA', 
        'DIFAL_FUNDAMENTAÇÃO'
    ]
    
    # Aplica a auditoria linha a linha
    df_d[analises] = df_d.apply(audit_difal_detalhada, axis=1)

    # --- REORGANIZAÇÃO E FILTRAGEM ---
    # No DIFAL, geralmente só queremos ver o que é Interestadual
    df_final = df_d[df_d['UF_EMIT'] != df_d['UF_DEST']].copy()

    # Prioridade de colunas
    prioridade = ['NUM_NF', 'UF_EMIT', 'UF_DEST', 'BC-ICMS', 'ALQ-ICMS', 'VAL-DIFAL', 'VAL-FCP-DEST', 'Situação Nota']
    outras_cols = [c for c in df_final.columns if c not in analises and c not in prioridade]
    
    df_export = df_final[prioridade + outras_cols + analises]

    # Gravação no Excel
    df_export.to_excel(writer, sheet_name='DIFAL_AUDIT', index=False)
