import pandas as pd
import os
import streamlit as st

def processar_icms(df, writer, cod_cliente):
    df_i = df.copy()

    # --- 1. CARREGAMENTO DO GABARITO (INTELIGÊNCIA POR CLIENTE) ---
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    
    if os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except: pass

    def audit_icms_linha(r):
        # --- Captura de Dados do XML ---
        uf_orig = str(r.get('UF_EMIT', '')).strip()
        uf_dest = str(r.get('UF_DEST', '')).strip()
        ncm = str(r.get('NCM', '')).zfill(8)
        origem_prod = str(r.get('ORIGEM', '0'))
        cst_xml = str(r.get('CST-ICMS', '00')).zfill(2)
        alq_xml = float(r.get('ALQ-ICMS', 0.0))
        vlr_icms_xml = float(r.get('VLR-ICMS', 0.0))
        bc_icms_xml = float(r.get('BC-ICMS', 0.0))
        vprod = float(r.get('VPROD', 0.0))
        vlr_st_xml = float(r.get('VAL-ICMS-ST', 0.0))
        vlr_ibs = float(r.get('VAL-IBS', 0.0))
        vlr_cbs = float(r.get('VAL-CBS', 0.0))

        # --- REGRAS DE OURO (VALORES ESPERADOS) ---
        alq_esp = 18.0  # Alíquota interna padrão
        cst_esp = "00"  # Tributação integral padrão
        
        # Lógica Interestadual Automática
        if uf_orig != uf_dest:
            if origem_prod in ['1', '2', '3', '8']: 
                alq_esp = 4.0
            else:
                sul_sudeste = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC']
                if (uf_orig in sul_sudeste and uf_dest not in sul_sudeste + ['ES']):
                    alq_esp = 7.0
                else:
                    alq_esp = 12.0
        
        # Sobreposição pelo Gabarito do Cliente
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_ESPERADA' in base_gabarito.columns: 
                cst_esp = str(g['CST_ESPERADA']).zfill(2)
            if 'ALQ_INTER' in base_gabarito.columns and uf_orig != uf_dest: 
                alq_esp = float(g['ALQ_INTER'])

        # --- CÁLCULOS E VALIDAÇÕES ---
        vlr_icms_devido = round(bc_icms_xml * (alq_esp / 100), 2)
        vlr_comp = round(vlr_icms_devido - vlr_icms_xml, 2)
        vlr_comp_final = vlr_comp if vlr_comp > 0.01 else 0.0

        # Diagnósticos
        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML:{alq_xml}%|Esp:{alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML:{cst_xml}|Esp:{cst_esp})"
        status_base = "✅ Integral" if abs(bc_icms_xml - vprod) < 0.10 else "⚠️ Base Reduzida"
        
        status_destaque = "✅ OK"
        if cst_xml in ['00', '10', '20', '70'] and vlr_icms_xml <= 0: 
            status_destaque = "❌ Falta Destaque"
        elif cst_xml in ['40', '41', '50'] and vlr_icms_xml > 0: 
            status_destaque = "⚠️ Destaque Indevido"

        diag_st = "✅ OK"
        if cst_xml in ['10', '30', '70', '90'] and vlr_st_xml <= 0:
            diag_st = "❌ ST não retido"

        # Ação Corretiva
        acao = "Nenhuma"
        motivo = "Em conformidade."
        if vlr_comp_final > 0:
            acao = "Emitir NF Complementar"
            motivo = f"Faltou destacar R$ {vlr_comp_final} de ICMS Próprio."
        elif alq_xml > alq_esp:
            acao = "Estorno de Débito"
            motivo = f"Alíquota XML ({alq_xml}%) maior que a devida ({alq_esp}%)."

        return pd.Series([
            cst_esp, alq_esp, diag_cst, diag_alq, status_destaque, 
            status_base, vlr_comp_final, diag_st, acao, motivo
        ])

    # --- MONTAGEM DAS COLUNAS ---
    analises = [
        'CST_ESPERADA', 'ALQ_ESPERADA', 'DIAG_CST', 'DIAG_ALQUOTA', 
        'STATUS_DESTAQUE', 'STATUS_BASE', 'ICMS_COMPLEMENTAR', 
        'DIAG_ST', 'AÇÃO_CORRETIVA', 'FUNDAMENTAÇÃO'
    ]
    
    df_i[analises] = df_i.apply(audit_icms_linha, axis=1)

    # Organização das colunas (Dados XML + Novas Tags + Análise)
    cols_originais = [
        'NUM_NF', 'CFOP', 'NCM', 'VPROD', 'CST-ICMS', 'ALQ-ICMS', 'VLR-ICMS', 
        'VAL-ICMS-ST', 'VAL-FCP', 'VAL-IBS', 'VAL-CBS', 'Situação Nota'
    ]
    
    df_final = df_i[cols_originais + analises]
    df_final.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
