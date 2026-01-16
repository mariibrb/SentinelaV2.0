import pandas as pd
import os

def processar_pc(df, writer, cod_cliente=None, regime="Lucro Real"):
    df_pc = df.copy()

    # --- 1. CARREGAMENTO DA BASE TRIBUTÁRIA (GABARITO) ---
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    if cod_cliente and os.path.exists(caminho_base):
        try:
            # Lemos como string para garantir match do NCM (texto puro)
            base_gabarito = pd.read_excel(caminho_base, dtype=str)
            base_gabarito.columns = [str(c).strip().upper() for c in base_gabarito.columns]
            if 'NCM' in base_gabarito.columns:
                base_gabarito['NCM'] = base_gabarito['NCM'].str.replace(r'\D', '', regex=True).str.strip().str.zfill(8)
        except:
            pass

    def audit_pc_completa(r):
        # --- Dados do XML ---
        ncm = str(r.get('NCM', '')).strip().zfill(8)
        cst_pis_xml = str(r.get('CST-PIS', '')).strip().zfill(2)
        cst_cof_xml = str(r.get('CST-COFINS', '')).strip().zfill(2)
        vlr_pis_xml = float(r.get('VLR-PIS', 0.0))
        vlr_cof_xml = float(r.get('VLR-COFINS', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        
        # --- DEFINIÇÃO DE ALÍQUOTA POR REGIME ---
        if "Presumido" in str(regime):
            alq_pis_esp = 0.65
            alq_cof_esp = 3.0
            cst_pc_esp = "01"
        else: # Lucro Real
            alq_pis_esp = 1.65
            alq_cof_esp = 7.6
            cst_pc_esp = "01"
        
        # SOBREPOSIÇÃO PELO GABARITO (Monofásicos, Alíquota Zero, etc.)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            
            # Busca dinâmica de colunas no seu Excel
            col_cst = [c for c in base_gabarito.columns if 'CST' in c and ('PC' in c or 'PIS' in c)]
            col_pis = [c for c in base_gabarito.columns if 'ALQ' in c and 'PIS' in c]
            col_cof = [c for c in base_gabarito.columns if 'ALQ' in c and 'COF' in c]

            if col_cst: cst_pc_esp = str(g[col_cst[0]]).strip().split('.')[0].zfill(2)
            if col_pis: alq_pis_esp = float(g[col_pis[0]])
            if col_cof: alq_cof_esp = float(g[col_cof[0]])

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
        motivo = f"PIS/COFINS em conformidade para {regime} e NCM {ncm}."
        
        if comp_pis > 0.01 or comp_cof > 0.01:
            acao = "NF Complementar / Guia de Ajuste"
            motivo = f"Recolhimento insuficiente no {regime}. Dif PIS: {comp_pis} | Dif COFINS: {comp_cof}."
        elif "❌" in diag_cst_pis or "❌" in diag_cst_cof:
            acao = "Registrar CC-e"
            motivo = f"CST informado difere do esperado ({cst_pc_esp}) para este NCM."

        return pd.Series([
            cst_pc_esp, alq_pis_esp, alq_cof_esp,
            diag_cst_pis, diag_vlr_pis, 
            diag_cst_cof, diag_vlr_cof, 
            acao, motivo
        ])

    # --- LISTA DE COLUNAS DE ANÁLISE ---
    analises_nomes = [
        'CST_PC_ESPERADA', 'ALQ_PIS_ESP', 'ALQ_COF_ESP',
        'PIS_DIAG_CST', 'PIS_DIAG_VALOR', 
        'COFINS_DIAG_CST', 'COFINS_DIAG_VALOR', 
        'AÇÃO_CORRETIVA_PC', 'FUNDAMENTAÇÃO_PC'
    ]
    
    # Aplica a auditoria
    df_pc[analises_nomes] = df_pc.apply(audit_pc_completa, axis=1)
    
    # --- REORGANIZAÇÃO RIGOROSA DAS COLUNAS ---
    # 1. Separamos as Tags do XML (dados brutos extraídos pelo Core)
    cols_originais = [c for c in df.columns if c != 'Situação Nota']
    
    # 2. Separamos o Status de Autenticidade
    cols_status = ['Situação Nota'] if 'Situação Nota' in df.columns else []
    
    # 3. Concatenamos na ordem: [XML] -> [STATUS] -> [ANÁLISES]
    df_final = pd.concat([df_pc[cols_originais], df_pc[cols_status], df_pc[analises_nomes]], axis=1)
    
    # Gravação no Excel
    df_final.to_excel(writer, sheet_name='PIS_COFINS_AUDIT', index=False)
