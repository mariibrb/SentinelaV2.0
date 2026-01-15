import pandas as pd
import os
import streamlit as st

def processar_icms(df, writer, cod_cliente):
    df_i = df.copy()

    # 1. Carregamento da Base Tributária (Gabarito) do GitHub/Local
    caminho_base = f"Bases_Tributárias/{cod_cliente}-Bases_Tributarias.xlsx"
    base_gabarito = pd.DataFrame()
    
    # Tenta ler a base para o cruzamento de NCM
    if os.path.exists(caminho_base):
        try:
            base_gabarito = pd.read_excel(caminho_base)
            base_gabarito['NCM'] = base_gabarito['NCM'].astype(str).str.strip().str.zfill(8)
        except Exception as e:
            st.error(f"Erro ao ler gabarito no motor de ICMS: {e}")

    def audit_icms_completa(r):
        # --- Dados vindos do XML ---
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

        # --- Valores Esperados (O Coração da Auditoria) ---
        alq_esp = 18.0  # Padrão Interno
        cst_esp = "00"  # Padrão Tributado Integralmente
        
        # Lógica de Alíquota Interestadual Automática
        if uf_orig != uf_dest:
            if origem_prod in ['1', '2', '3', '8']: 
                alq_esp = 4.0
            else:
                sul_sudeste = ['SP', 'RJ', 'MG', 'PR', 'RS', 'SC']
                # Regra: Origem Sul/Sudeste para Norte/Nordeste/Centro-Oeste = 7%
                if (uf_orig in sul_sudeste and uf_dest not in sul_sudeste + ['ES']):
                    alq_esp = 7.0
                else:
                    alq_esp = 12.0
        
        # Cruzamento com Gabarito por Empresa (Se houver NCM cadastrado)
        if not base_gabarito.empty and ncm in base_gabarito['NCM'].values:
            g = base_gabarito[base_gabarito['NCM'] == ncm].iloc[0]
            if 'CST_ESPERADA' in base_gabarito.columns: 
                cst_esp = str(g['CST_ESPERADA']).zfill(2)
            if 'ALQ_INTER' in base_gabarito.columns and uf_orig != uf_dest: 
                alq_esp = float(g['ALQ_INTER'])

        # --- CÁLCULOS DE AUDITORIA ---
        
        # Cálculo ICMS Próprio Devido
        vlr_icms_devido = round(bc_icms_xml * (alq_esp / 100), 2)
        vlr_complementar = round(vlr_icms_devido - vlr_icms_xml, 2)
        vlr_comp_final = vlr_complementar if vlr_complementar > 0.01 else 0.0

        # Diagnósticos de Conformidade
        diag_alq = "✅ OK" if abs(alq_xml - alq_esp) < 0.01 else f"❌ Erro (XML: {alq_xml}% | Esp: {alq_esp}%)"
        diag_cst = "✅ OK" if cst_xml == cst_esp else f"❌ Divergente (XML: {cst_xml} | Esp: {cst_esp})"

        # Status Destaque
        status_destaque = "✅ OK"
        if cst_xml in ['00', '10', '20', '70'] and vlr_icms_xml <= 0: 
            status_destaque = "❌ Falta Destaque"
        elif cst_xml in ['40', '41', '50'] and vlr_icms_xml > 0: 
            status_destaque = "⚠️ Destaque Indevido"

        # Análise da Base de Cálculo
        status_base = "✅ Integral" if abs(bc_icms_xml - vprod) < 0.10 else "⚠️ Reduzida/Diferente"

        # Diagnóstico de ST
        diag_st = "✅ OK"
        if cst_xml in ['10', '30', '70', '90'] and vlr_st_xml <= 0:
            diag_st = "❌ ST não retido"
        elif cst_xml == '60' and uf_orig != uf_dest:
            diag_st = "⚠️ Requer nova retenção (Interestadual)"

        # Definição de Ação Corretiva
        acao = "Nenhuma"
        motivo = "Imposto em conformidade com as regras tributárias."

        if vlr_comp_final > 0:
            acao = "Emitir NF Complementar"
            motivo = f"Diferença de ICMS Próprio de R$ {vlr_comp_final} detectada."
        elif alq_xml > alq_esp:
            acao = "Solicitar Estorno / Crédito"
            motivo = f"Alíquota de {alq_xml}% maior que a esperada de {alq_esp}%."
        elif "❌" in diag_cst:
            acao = "Registrar CC-e"
            motivo = "A CST informada no XML difere do gabarito tributário da empresa."

        return pd.Series([
            cst_esp, alq_esp, diag_cst, diag_alq, status_destaque, 
            status_base, vlr_comp_final, diag_st, acao, motivo
        ])

    # Lista de colunas de análise para o relatório
    analises = [
        'ICMS_CST_ESPERADA', 
        'ICMS_ALQ_ESPERADA', 
        'DIAGNÓSTICO_CST', 
        'DIAGNÓSTICO_ALÍQUOTA', 
        'STATUS_DESTAQUE_IMPOSTO', 
        'STATUS_BASE_CÁLCULO',
        'VALOR_ICMS_COMPLEMENTAR', 
        'DIAGNÓSTICO_ST', 
        'AÇÃO_CORRETIVA_SUGERIDA', 
        'FUNDAMENTAÇÃO_LEGAL'
    ]
    
    # Aplica a auditoria linha por linha
    df_i[analises] = df_i.apply(audit_icms_completa, axis=1)

    # Reorganiza: Dados do XML primeiro, depois os campos de análise
    cols_originais = [c for c in df_i.columns if c not in analises]
    df_final = df_i[cols_originais + analises]

    # Salva na aba correspondente
    df_final.to_excel(writer, sheet_name='ICMS_AUDIT', index=False)
