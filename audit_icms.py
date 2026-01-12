import pandas as pd
import os

def processar_icms(df, writer, cod_cliente):
    df_i = df.copy()

    # 1. Carregamento da Base Tributária da Empresa (Gabarito)
    caminho_base = f"bases/base_tributaria_{cod_cliente}.xlsx"
    base_gabarito = pd.DataFrame()
    if os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except: pass

    def audit_icms_completa(r):
        # --- Dados do XML ---
        uf_orig = str(r.get('UF_EMIT', ''))
        uf_dest = str(r.get('UF_DEST', ''))
        ncm = str(r.get('NCM', '')).zfill(8)
        origem_prod = str(r.get('ORIGEM', '0'))
        cst_xml = str(r.get('CST-ICMS', '00')).zfill(2)
        alq_xml = float(r.get('ALQ-ICMS', 0.0))
        vlr_icms_xml = float(r.get('VLR-ICMS', 0.0))
        bc_icms_xml = float(r.get('BC-ICMS', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        
        # Dados de ST
        vlr_st_xml = float(r.get('VAL-ICMS-ST', 0.0))
        bc_st_xml = float(r.get('BC-ICMS-ST', 0.0))

        # --- Gabarito e Regras ---
        alq_esp = 18.0
        cst_esp = "00"
        mva_esp = 0.0
        
        # Regra Interestadual (4%, 7%, 12%)
        if uf_orig != uf_dest:
            if origem_prod in ['1', '2', '3', '8']: alq_esp = 4.0
            else:
                sul_sudeste = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC']
                alq_esp = 7.0 if (uf_orig in sul_sudeste and uf_dest not in sul_sudeste + ['ES']) else 12.0
        
        # Cruzamento com Gabarito por Empresa
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_ESPERADA' in base_gabarito.columns: cst_esp = str(g['CST_ESPERADA']).zfill(2)
            if 'ALQ_INTER' in base_gabarito.columns and uf_orig != uf_dest: alq_esp = float(g['ALQ_INTER'])
            if 'MVA' in base_gabarito.columns: mva_esp = float(g['MVA'])

        # --- ANALISE ICMS PRÓPRIO ---
        status_destaque = "✅ OK"
        if cst_xml in ['00', '10', '20', '70'] and vlr_icms_xml <= 0: status_destaque = "❌ Falta Destaque"
        elif cst_xml in ['40', '41', '50'] and vlr_icms_xml > 0: status_destaque = "⚠️ Destaque Indevido"

        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (Esp: {alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (Esp: {cst_esp})"
        
        # Auditoria de Base (Redução ou Integral)
        status_base = "✅ Integral" if abs(bc_icms_xml - vprod) < 0.10 else "⚠️ Reduzida/Diferente"

        # --- ANALISE ICMS ST ---
        diag_st = "✅ OK"
        if cst_xml in ['10', '30', '70', '90'] and vlr_st_xml <= 0:
            diag_st = "❌ ST não retido"
        elif cst_xml == '60' and uf_orig != uf_dest:
            diag_st = "⚠️ Requer nova retenção"

        # --- AÇÃO CORRETIVA E FUNDAMENTAÇÃO ---
        acao = "Nenhuma"
        motivo = "Imposto em conformidade."

        if status_destaque == "❌ Falta Destaque" or alq_xml < alq_esp:
            acao = "Emitir NF Complementar"
            motivo = "Diferença de imposto a menor identificada."
        elif alq_xml > alq_esp:
            acao = "Procedimento de Estorno"
            motivo = "Alíquota aplicada maior que o previsto na legislação."
        elif diag_cst != "✅ OK":
            acao = "Registrar CC-e"
            motivo = "Correção de CST sem alteração de valores."

        return pd.Series([
            status_destaque, diag_alq, alq_esp, 
            diag_cst, cst_esp, status_base,
            diag_st, acao, motivo
        ])

    # Colunas de Análise pós AG
    analises = [
        'ICMS_STATUS_DESTAQUE', 'ICMS_DIAG_ALQUOTA', 'ICMS_ALQ_ESPERADA',
        'ICMS_DIAG_CST', 'ICMS_CST_ESPERADA', 'ICMS_STATUS_BASE',
        'ICMS_DIAG_ST', 'AÇÃO_CORRETIVA', 'FUNDAMENTAÇÃO'
    ]
    
    df_i[analises] = df_i.apply(audit_icms_completa, axis=1)

    # Organização das Colunas: Originais até AG (Situação Nota) + Analises
    cols_xml = [c for c in df_i.columns if c not in analises and c != 'Situação Nota']
    df_final = df_i[cols_xml + ['Situação Nota'] + analises]

    df_final.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
