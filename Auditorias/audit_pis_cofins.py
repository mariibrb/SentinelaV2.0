import pandas as pd
import os

def processar_pc(df, writer, cod_cliente=None, regime="Lucro Real"):
    df_pc = df.copy()

    # --- 1. CARREGAMENTO DA BASE TRIBUTÁRIA (GABARITO) ---
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    if cod_cliente and os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except:
            pass

    def audit_pc_completa(r):
        # --- Dados do XML (Conectando com as tags restauradas do Core) ---
        ncm = str(r.get('NCM', '')).zfill(8)
        cst_pis_xml = str(r.get('CST-PIS', '')).zfill(2)
        cst_cof_xml = str(r.get('CST-COFINS', '')).zfill(2)
        vlr_pis_xml = float(r.get('VLR-PIS', 0.0))    # Tag ajustada
        vlr_cof_xml = float(r.get('VLR-COFINS', 0.0)) # Tag ajustada
        vprod = float(r.get('VPROD', 0.0))
        
        # --- DEFINIÇÃO DE ALÍQUOTA POR REGIME (O CÉREBRO) ---
        if "Presumido" in str(regime):
            alq_pis_esp = 0.65
            alq_cof_esp = 3.0
            cst_pc_esp = "01"
        else: # Lucro Real (Padrão)
            alq_pis_esp = 1.65
            alq_cof_esp = 7.6
            cst_pc_esp = "01"
        
        # Sobrescreve com o Gabarito (Para Monofásicos, Alíquota Zero, etc.)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_PC_ESPERADA' in base_gabarito.columns: 
                cst_pc_esp = str(g['CST_PC_ESPERADA']).zfill(2)
            if 'ALQ_PIS_ESPERADA' in base_gabarito.columns: 
                alq_pis_esp = float(g['ALQ_PIS_ESPERADA'])
            if 'ALQ_COF_ESPERADA' in base_gabarito.columns: 
                alq_cof_esp = float(g['ALQ_COF_ESPERADA'])

        # --- CÁLCULOS DE CONFERÊNCIA ---
        vlr_pis_dev = round(vprod * (alq_pis_esp / 100), 2)
        vlr_cof_dev = round(vprod * (alq_cof_esp / 100), 2)
        
        comp_pis = max(0.0, round(vlr_pis_dev - vlr_pis_xml, 2))
        comp_cof = max(0.0, round(vlr_cof_dev - vlr_cof_xml, 2))

        # --- DIAGNÓSTICOS ---
        diag_cst_pis = "✅ OK" if cst_pis_xml == cst_pc_esp else f"❌ Erro (XML: {cst_pis_xml} | Esp: {cst_pc_esp})"
        diag_vlr_pis = "✅ OK" if comp_pis <= 0.01 else f"❌ Faltou R$ {comp_pis}"
        
        diag_cst_cof = "✅ OK" if cst_cof_xml == cst_pc_esp else f"❌ Erro (XML: {cst_cof_xml} | Esp: {cst_pc_esp})"
        diag_vlr_cof = "✅ OK" if comp_cof <= 0.01 else f"❌ Faltou R$ {comp_cof}"

        # --- AÇÃO CORRETIVA ---
        acao = "Nenhuma"
        motivo = f"PIS/COFINS em conformidade para o regime {regime}."
        
        if comp_pis > 0 or comp_cof > 0:
            acao = "Emitir NF Complementar / Guia de Ajuste"
            motivo = f"Recolhimento a menor identificado no {regime}. PIS: R$ {comp_pis}, COFINS: R$ {comp_cof}."
        elif "❌" in diag_cst_pis or "❌" in diag_cst_cof:
            acao = "Registrar CC-e"
            motivo = "Ajustar CST de PIS/COFINS para evitar rejeição em obrigações acessórias (EFD Contribuições)."

        return pd.Series([
            cst_pc_esp, alq_pis_esp, alq_cof_esp,
            diag_cst_pis, diag_vlr_pis, 
            diag_cst_cof, diag_vlr_cof, 
            acao, motivo
        ])

    # --- MONTAGEM DAS COLUNAS DE ANÁLISE ---
    analises = [
        'CST_PC_ESPERADA', 'ALQ_PIS_ESP', 'ALQ_COF_ESP',
        'PIS_DIAG_CST', 'PIS_DIAG_VALOR', 
        'COFINS_DIAG_CST', 'COFINS_DIAG_VALOR', 
        'AÇÃO_CORRETIVA_PC', 'FUNDAMENTAÇÃO_PC'
    ]
    
    df_pc[analises] = df_pc.apply(audit_pc_completa, axis=1)
    
    # --- ORGANIZAÇÃO FINAL ---
    # Priorizamos a visualização das tags do XML (incluindo as novas CBS e IBS)
    prioridade = [
        'NUM_NF', 'NCM', 'VPROD', 
        'CST-PIS', 'VLR-PIS', 'CST-COFINS', 'VLR-COFINS', 
        'VAL-CBS', 'VAL-IBS', 'Situação Nota'
    ]
    
    outras_cols = [c for c in df_pc.columns if c not in analises and c not in prioridade]
    df_final = df_pc[prioridade + outras_cols + analises]
    
    # Gravação no Excel
    df_final.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)
