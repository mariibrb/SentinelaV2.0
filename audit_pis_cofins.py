import pandas as pd
import os

def processar_pc(df, writer, cod_cliente=None, regime="Lucro Real"):
    df_pc = df.copy()

    # 1. Carregamento da Base Tributária (Gabarito)
    caminho_base = f"bases/base_tributaria_{cod_cliente}.xlsx"
    base_gabarito = pd.DataFrame()
    if cod_cliente and os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except: pass

    def audit_pc_completa(r):
        ncm = str(r.get('NCM', '')).zfill(8)
        cst_pis = str(r.get('CST-PIS', '')).zfill(2)
        cst_cof = str(r.get('CST-COF', '')).zfill(2)
        vlr_pis_xml = float(r.get('VAL-PIS', 0.0))
        vlr_cof_xml = float(r.get('VAL-COF', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        
        # --- DEFINIÇÃO DE ALÍQUOTA POR REGIME ---
        if regime == "Lucro Presumido":
            alq_pis_esp = 0.65
            alq_cof_esp = 3.0
            cst_pc_esp = "01" # No presumido também se usa 01 para saídas tributadas
        else: # Lucro Real
            alq_pis_esp = 1.65
            alq_cof_esp = 7.6
            cst_pc_esp = "01"
        
        # Sobrescreve com o Gabarito (se houver exceção por NCM, como Monofásicos)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_PC_ESPERADA' in base_gabarito.columns: cst_pc_esp = str(g['CST_PC_ESPERADA']).zfill(2)
            if 'ALQ_PIS_ESPERADA' in base_gabarito.columns: alq_pis_esp = float(g['ALQ_PIS_ESPERADA'])
            if 'ALQ_COF_ESPERADA' in base_gabarito.columns: alq_cof_esp = float(g['ALQ_COF_ESPERADA'])

        # --- CÁLCULO DE COMPLEMENTO ---
        vlr_pis_dev = round(vprod * (alq_pis_esp / 100), 2)
        vlr_cof_dev = round(vprod * (alq_cof_esp / 100), 2)
        comp_pis = max(0.0, round(vlr_pis_dev - vlr_pis_xml, 2))
        comp_cof = max(0.0, round(vlr_cof_dev - vlr_cof_xml, 2))

        # --- DIAGNÓSTICOS CONDICIONAIS ---
        diag_cst_pis = "✅ OK" if cst_pis == cst_pc_esp else f"❌ Erro (XML: {cst_pis} | Esp: {cst_pc_esp})"
        diag_vlr_pis = "✅ OK" if comp_pis <= 0.01 else f"❌ Faltou R$ {comp_pis}"
        diag_cst_cof = "✅ OK" if cst_cof == cst_pc_esp else f"❌ Erro (XML: {cst_cof} | Esp: {cst_pc_esp})"
        diag_vlr_cof = "✅ OK" if comp_cof <= 0.01 else f"❌ Faltou R$ {comp_cof}"

        # Ações
        acao = "Nenhuma"
        motivo = f"PIS/COFINS em conformidade ({regime})."
        if comp_pis > 0 or comp_cof > 0:
            acao = "Emitir NF Complementar"
            motivo = f"Diferença no regime {regime}: PIS R$ {comp_pis}, COFINS R$ {comp_cof}."
        elif "❌" in diag_cst_pis or "❌" in diag_cst_cof:
            acao = "Registrar CC-e"
            motivo = "Divergência de CST sem impacto financeiro."

        return pd.Series([diag_cst_pis, diag_vlr_pis, diag_cst_cof, diag_vlr_cof, acao, motivo])

    analises = ['PIS_DIAG_CST', 'PIS_DIAG_VALOR', 'COFINS_DIAG_CST', 'COFINS_DIAG_VALOR', 'AÇÃO_CORRETIVA_PC', 'FUNDAMENTAÇÃO_PC']
    df_pc[analises] = df_pc.apply(audit_pc_completa, axis=1)
    
    cols_xml = [c for c in df_pc.columns if c not in analises and c != 'Situação Nota']
    df_final = df_pc[cols_xml + ['Situação Nota'] + analises]
    df_final.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)
